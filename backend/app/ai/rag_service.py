import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.policy import PolicyChunk, PolicyDocument
from app.ai.embeddings import generate_embedding
from app.ai.vector_store import search_vector_store
from app.core.logging import logger

def perform_sparse_keyword_search(
    db: Session, 
    query: str, 
    limit: int = 5
) -> List[PolicyChunk]:
    """Finds chunks matching terms using standard case-insensitive SQL ILIKE queries."""
    # Clean query into keywords
    words = re.sub(r"[^\w\s]", "", query.lower()).split()
    keywords = [w for w in words if len(w) > 3] # Keep words longer than 3 characters
    
    if not keywords:
        # Fallback to general split
        keywords = words[:3]
        
    if not keywords:
        return []

    # Build ILIKE query clauses
    query_obj = db.query(PolicyChunk)
    clauses = []
    for keyword in keywords:
        clauses.append(PolicyChunk.content.ilike(f"%{keyword}%"))
        
    if clauses:
        from sqlalchemy import or_
        results = query_obj.filter(or_(*clauses)).limit(limit).all()
        return results
    return []


def hybrid_retrieve_policy_chunks(
    db: Session, 
    query: str, 
    limit: int = 3
) -> List[Tuple[PolicyChunk, float]]:
    """
    Executes a hybrid search combining dense pgvector and sparse keyword queries,
    blending results using Reciprocal Rank Fusion (RRF).
    """
    # 1. Dense retrieval (pgvector)
    try:
        query_vector = generate_embedding(query)
        dense_results = search_vector_store(db, query_vector, limit=limit * 2)
    except Exception as e:
        logger.warning("RAG_DENSE_RETRIEVAL_FAILED: falling back to sparse keyword search only", error=str(e))
        dense_results = []
    
    # 2. Sparse retrieval (Keyword SQL query)
    sparse_results = perform_sparse_keyword_search(db, query, limit=limit * 2)
    
    # 3. Reciprocal Rank Fusion (RRF) Blending
    # Formula: RRF_Score = Sum( 1 / (60 + Rank) )
    rrf_scores: Dict[int, float] = {}
    chunk_map: Dict[int, PolicyChunk] = {}
    
    # Process dense rank
    for rank, (chunk, _) in enumerate(dense_results, start=1):
        chunk_map[chunk.id] = chunk
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (60.0 + rank))
        
    # Process sparse rank
    for rank, chunk in enumerate(sparse_results, start=1):
        chunk_map[chunk.id] = chunk
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + (1.0 / (60.0 + rank))
        
    # Sort by RRF score descending
    sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    
    # Format top-k chunks
    final_results = []
    for chunk_id in sorted_chunk_ids[:limit]:
        chunk = chunk_map[chunk_id]
        # Retrieve document title
        doc = db.query(PolicyDocument).filter(PolicyDocument.id == chunk.document_id).first()
        doc_title = doc.title if doc else "Compliance manual"
        
        # Attach doc title context to chunk object dynamically for easy prompt building
        chunk.document_title = doc_title
        chunk.filename = doc.filename if doc else "manual.pdf"
        
        # Calculate a mock final score based on RRF rank relative to max possible score
        max_rrf = (1.0 / 61.0) * 2.0 # top rank in both dense and sparse
        raw_score = rrf_scores[chunk_id]
        scaled_score = min(100.0, (raw_score / max_rrf) * 100.0)
        
        final_results.append((chunk, float(scaled_score)))
        
    return final_results
