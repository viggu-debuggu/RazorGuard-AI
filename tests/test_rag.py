from app.ai.chunking import split_text_into_sliding_chunks
from app.models.policy import PolicyDocument, PolicyChunk
from app.ai.rag_service import hybrid_retrieve_policy_chunks

def test_sliding_window_chunking():
    """Verifies that split_text_into_sliding_chunks slices long text blocks correctly with overlap."""
    text = "one two three four five six seven eight nine ten"
    # Chunk size: 5 words, overlap: 2 words
    chunks = split_text_into_sliding_chunks(text, chunk_size=5, overlap=2)
    
    # First chunk: "one two three four five"
    # Second chunk start index: index 3 -> "four five six seven eight"
    # Third chunk start index: index 6 -> "seven eight nine ten"
    assert len(chunks) == 3
    assert chunks[0]["content"] == "one two three four five"
    assert chunks[1]["content"] == "four five six seven eight"
    assert chunks[2]["content"] == "seven eight nine ten"


def test_rrf_blending_hybrid_retrieval(db_session):
    """Verifies that RAG search yields matched policy chunk nodes and populates references."""
    # Seed single policy manual
    doc = PolicyDocument(title="Test Directive", filename="test.txt", checksum="ch_hash")
    db_session.add(doc)
    db_session.flush()
    
    # Create chunks
    c1 = PolicyChunk(document_id=doc.id, chunk_index=0, content="CNP payment amount blacklists clause limit", embedding=[0.1]*384)
    db_session.add(c1)
    db_session.commit()
    
    # Run hybrid query
    res = hybrid_retrieve_policy_chunks(db_session, "CNP payment limits", limit=1)
    assert len(res) == 1
    chunk, score = res[0]
    assert chunk.content == "CNP payment amount blacklists clause limit"
    assert chunk.document_title == "Test Directive"
    assert score > 0.0
