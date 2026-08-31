import os
import sys

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.session import Base
from app.models.policy import PolicyDocument, PolicyChunk
from app.ai.embeddings import generate_embedding
from app.ai.rag_service import hybrid_retrieve_policy_chunks


def setup_eval_db():
    """Sets up an in-memory SQLite database and seeds test compliance policies."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSession()
    
    # 1. Seed policy document
    doc = PolicyDocument(
        title="RazorGuard Compliance Rules Manual",
        filename="compliance_rules.pdf",
        checksum="comp_rules_hash_123"
    )
    db.add(doc)
    db.flush()
    
    # 2. Seed chunks
    chunks_data = [
        (0, "Transactions in the gaming category require cardholder presence validation if the transaction amount is over INR 10,000."),
        (1, "Geographic origin checks: Card origin mismatch relative to customer billing address must trigger SCA authentication guidelines."),
        (2, "Card-not-present transactions for the electronics category exceeding INR 50,000 must be blocked for compliance review and verification."),
        (3, "Any large ticket size transactions exceeding INR 500,000 require manual review and compliance audit by the risk investigations team.")
    ]
    
    for idx, content in chunks_data:
        embedding = generate_embedding(content)
        chunk = PolicyChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=content,
            embedding=embedding
        )
        db.add(chunk)
        
    db.commit()
    return db


def run_rag_evaluation():
    print("-----------------------------------------------------------------")
    print("Starting RAG Retrieval Quality Evaluation...")
    print("-----------------------------------------------------------------")
    
    # Setup test database
    db = setup_eval_db()
    
    # Define test queries and expected matching chunk index (8-10 cases, including tricky ones)
    test_cases = [
        {
            "query": "gaming CNP limits over 10000",
            "expected_idx": 0,
            "description": "Direct gaming threshold check"
        },
        {
            "query": "billing mismatch origin SCA",
            "expected_idx": 1,
            "description": "Direct geographic origin mismatch"
        },
        {
            "query": "electronics CNP block threshold 50000",
            "expected_idx": 2,
            "description": "Direct electronics threshold check"
        },
        {
            "query": "large ticket transaction review",
            "expected_idx": 3,
            "description": "Direct large ticket threshold check"
        },
        {
            "query": "gaming category cardholder presence required check",
            "expected_idx": 0,
            "description": "Slightly rephrased gaming presence check"
        },
        {
            "query": "geographic card billing address mismatch guidelines",
            "expected_idx": 1,
            "description": "Rephrased geographic origin mismatch"
        },
        {
            "query": "unauthorized card-not-present electronics payments block limit",
            "expected_idx": 2,
            "description": "Rephrased electronics limit check"
        },
        {
            "query": "audit rules for transactions exceeding five hundred thousand INR",
            "expected_idx": 3,
            "description": "Rephrased large ticket size check"
        },
        {
            "query": "do I need strong customer authentication for card present local food purchase?",
            "expected_idx": 1,
            "description": "[TRICKY] Asks about SCA but mentions food and local (should pull SCA mismatch rules as closest match)"
        },
        {
            "query": "compliance verification limits for crypto transaction of 30000 INR CNP",
            "expected_idx": 2,
            "description": "[TRICKY] Mentions crypto (grouped under electronics/crypto limits chunk) but amount is under 50k"
        }
    ]
    
    hits_at_1 = 0
    hits_at_3 = 0
    total = len(test_cases)
    mrr_sum = 0.0
    
    for idx, case in enumerate(test_cases, start=1):
        query = case["query"]
        expected_idx = case["expected_idx"]
        
        # Retrieve chunks (limit = 3)
        retrieved = hybrid_retrieve_policy_chunks(db, str(query), limit=3)
        
        # Evaluate
        found_rank = 0
        for rank, (chunk, _) in enumerate(retrieved, start=1):
            if chunk.chunk_index == expected_idx:
                found_rank = rank
                break
                
        if found_rank == 1:
            hits_at_1 += 1
        if 1 <= found_rank <= 3:
            hits_at_3 += 1
            
        reciprocal_rank = 1.0 / found_rank if found_rank > 0 else 0.0
        mrr_sum += reciprocal_rank
        
        status_symbol = "SUCCESS" if found_rank == 1 else "FAILED"
        print(f"Test Case {idx}: {case['description']}")
        print(f"  Query: '{query}'")
        print(f"  Expected Chunk Index: {expected_idx}")
        print(f"  Matched Rank: {found_rank if found_rank > 0 else 'Not Found'} ({status_symbol})")
        if retrieved:
            print(f"  Top Retrieved Chunk: \"{retrieved[0][0].content[:70]}...\" (Score: {retrieved[0][1]:.1f}%)")
        else:
            print("  Top Retrieved Chunk: None")
        print("-" * 65)
        
    p_at_1 = hits_at_1 / total
    p_at_3 = hits_at_3 / total
    mrr = mrr_sum / total
    
    print("\n=================================================================")
    print("EVALUATION METRICS:")
    print(f"  Total Test Queries Evaluated: {total}")
    print(f"  Precision @ 1: {p_at_1 * 100:.1f}%")
    print(f"  Precision @ 3: {p_at_3 * 100:.1f}%")
    print(f"  Mean Reciprocal Rank (MRR):   {mrr:.3f}")
    print("=================================================================")
    
    # Assert acceptable precision thresholds (tricky cases allow realistic failure bounds)
    assert p_at_1 >= 0.70, f"RAG Quality under expectations: Precision @ 1 = {p_at_1 * 100}%"
    assert p_at_3 >= 0.80, f"RAG Quality under expectations: Precision @ 3 = {p_at_3 * 100}%"
    print("SUCCESS: RAG retrieval quality matches baseline compliance requirements.")


if __name__ == "__main__":
    run_rag_evaluation()
