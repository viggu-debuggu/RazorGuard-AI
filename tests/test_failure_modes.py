import pytest
from unittest.mock import patch
from app.models.transaction import Transaction
from app.services.agent_team import PolicyRAGAgent, FraudInvestigationAgent

def test_rag_database_empty_fallback(db_session):
    """Verifies that the PolicyRAGAgent falls back gracefully when RAG search yields zero matching documents."""
    tx = Transaction(
        transaction_id="tx_fail_1",
        user_id="usr_fail_1",
        amount=250.0,
        currency="INR",
        billing_country="IN",
        card_country="IN",
        card_present=True,
        merchant_category="retail"
    )
    
    # Force hybrid retrieval to return empty array
    with patch("app.services.agent_team.hybrid_retrieve_policy_chunks", return_value=[]):
        res = PolicyRAGAgent.process_task(db_session, tx)
        assert res["score"] == 0.0
        assert "No applicable compliance guidelines" in res["outcome"]
        assert "evidences" in res
        assert len(res["evidences"]) == 0

def test_graph_walk_isolated_node(db_session):
    """Verifies that the FraudInvestigationAgent handles isolated nodes without matches correctly."""
    tx = Transaction(
        transaction_id="tx_fail_2",
        user_id="usr_isolated_1",
        amount=1000.0,
        currency="INR",
        device_fingerprint="df_brand_new_unique_123",
        ip_address="192.168.0.1",
        billing_country="IN",
        card_country="IN",
        card_present=True,
        merchant_category="retail"
    )
    
    res = FraudInvestigationAgent.process_task(db_session, tx)
    assert res["score"] == 0.0
    assert "Graph walking completed" in res["outcome"]
    assert "evidences" in res
    assert len(res["evidences"]) == 0
