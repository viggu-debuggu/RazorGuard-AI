import pytest
import os
from app.services.agent_orchestrator import verify_explanation_citations


def test_verify_citations_matching():
    """Verifies that citation checker passes when LLM cites only retrieved policy chunks."""
    explanation = (
        "We checked the merchant category electronic limitations and found it violates "
        "compliance rules. Refer to policies/electronics_policy.pdf#chunk_5 for more details. "
        "Also check the billing country mismatch guidelines in [Source: billing_policy.txt, Index: 2]."
    )
    
    # Retrieved policy chunks references
    policy_evidences = [
        {"policy_reference": "policies/electronics_policy.pdf#chunk_5"},
        {"policy_reference": "policies/billing_policy.txt#chunk_2"}
    ]
    
    hallucinations = verify_explanation_citations(explanation, policy_evidences)
    assert len(hallucinations) == 0, f"Expected no hallucinations, found: {hallucinations}"


def test_verify_citations_hallucinated():
    """Verifies that citation checker flags citations that do not exist in the retrieved list."""
    explanation = (
        "This transaction is suspicious. Refer to policies/electronics_policy.pdf#chunk_5. "
        "Also, we are block-listing the customer under policies/fake_rules_policy.pdf#chunk_99. "
        "Check [Source: wrong_doc.txt, Index: 12] for further details."
    )
    
    policy_evidences = [
        {"policy_reference": "policies/electronics_policy.pdf#chunk_5"}
    ]
    
    hallucinations = verify_explanation_citations(explanation, policy_evidences)
    assert len(hallucinations) == 2
    assert "policies/fake_rules_policy.pdf#chunk_99" in hallucinations
    assert "policies/wrong_doc.txt#chunk_12" in hallucinations


def test_demo_scenarios_explanation_actions(client, db_session):
    """Asserts explanation recommended action aligns with actual transaction status in all demo scenarios."""
    from scripts.seed_data import seed_database
    
    # Clean database first to avoid uniqueness conflicts
    from app.database.session import Base, engine
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Run DB seeder to populate scenarios
    seed_database()

    # Login analyst
    demo_password = os.getenv("DEMO_ANALYST_PASSWORD", "demo_placeholder_analyst_2026")
    log_res = client.post("/api/v1/auth/login", json={
        "email": "analyst@razorguard.ai",
        "password": demo_password
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    txs = [
        ("TXN-10021", "Approved", "APPROVE"),
        ("TXN-40293", "Approved", "APPROVE"),
        ("TXN-92817", "Blocked", "ESCALATE") # Initial action is ESCALATE, final status is Blocked by analyst override
    ]
    
    for tx_id, expected_status, expected_action in txs:
        from app.models.transaction import Transaction
        tx_rec = db_session.query(Transaction).filter(Transaction.transaction_id == tx_id).first()
        assert tx_rec is not None
        
        res = client.get(f"/api/v1/transactions/{tx_rec.id}/investigation", headers=headers)
        assert res.status_code == 200
        data = res.json()
        
        assert data["transaction"]["status"] == expected_status
        explanation = data["assessment"]["explanation"]
        
        # Parse Recommended Action section using regex
        import re
        action_match = re.search(r"### Recommended Action\n([^\n]+)", explanation)
        assert action_match is not None, f"Recommended Action section not found in explanation for {tx_id}."
        parsed_action = action_match.group(1).strip()
        assert parsed_action.startswith(expected_action), f"Expected action for {tx_id} to start with '{expected_action}', but parsed '{parsed_action}'."


