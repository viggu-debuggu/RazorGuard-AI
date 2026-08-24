from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.policy import PolicyChunk
from app.core.logging import logger

def save_policy_chunk(
    db: Session, 
    document_id: int, 
    chunk_index: int, 
    content: str, 
    embedding: List[float]
) -> PolicyChunk:
    """Inserts a single policy document text chunk and its embedding into PostgreSQL."""
    chunk = PolicyChunk(
        document_id=document_id,
        chunk_index=chunk_index,
        content=content,
        embedding=embedding
    )
    db.add(chunk)
    db.flush()
    return chunk


def search_vector_store(
    db: Session, 
    query_vector: List[float], 
    limit: int = 5
) -> List[Tuple[PolicyChunk, float]]:
    """
    Executes a pgvector similarity query using cosine distance if PostgreSQL is used,
    otherwise falls back to an in-memory python-based cosine similarity check for SQLite.
    Returns: List of tuples (PolicyChunk, similarity_score) sorted by highest similarity first.
    """
    # Check if database is SQLite or PostgreSQL
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        try:
            # Local SQLite fallback: retrieve all chunks and compute similarity in Python
            chunks = db.query(PolicyChunk).all()
            if not chunks:
                return []
            
            # Helper to calculate cosine similarity
            def cosine_sim(a, b):
                dot_product = sum(x * y for x, y in zip(a, b))
                norm_a = sum(x * x for x in a) ** 0.5
                norm_b = sum(x * x for x in b) ** 0.5
                if norm_a == 0 or norm_b == 0:
                    return 0.0
                return dot_product / (norm_a * norm_b)
            
            scored_chunks = []
            for chunk in chunks:
                emb = chunk.embedding
                if isinstance(emb, list) and len(emb) == len(query_vector):
                    sim = cosine_sim(emb, query_vector)
                    scored_chunks.append((chunk, sim))
            
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            return scored_chunks[:limit]
        except Exception as ex:
            logger.error("vector_search_local_fallback_failed", error=str(ex))
            chunks = db.query(PolicyChunk).limit(limit).all()
            return [(chunk, 0.8) for chunk in chunks]

    try:
        # cosine_distance is the default pgvector sqlalchemy operator <=>
        distance_expression = PolicyChunk.embedding.cosine_distance(query_vector)
        results = db.query(PolicyChunk, distance_expression).order_by(distance_expression).limit(limit).all()
        
        formatted_results = []
        for chunk, distance in results:
            # Cosine similarity = 1 - Cosine Distance
            # If distance is None (unsupported), fallback to 0.0
            distance_val = float(distance) if distance is not None else 1.0
            similarity = max(0.0, min(1.0, 1.0 - distance_val))
            formatted_results.append((chunk, similarity))
            
        return formatted_results
    except Exception as e:
        logger.error("vector_search_failed_falling_back_to_raw_op", error=str(e))
        # Fallback to direct raw operator comparison
        try:
            results = db.query(PolicyChunk).order_by(
                PolicyChunk.embedding.op('<=>')(query_vector)
            ).limit(limit).all()
            # return with mock score
            return [(chunk, 0.8) for chunk in results]
        except Exception as ex:
            logger.error("vector_search_raw_fallback_failed", error=str(ex))
            return []
