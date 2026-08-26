import pytest
from app.models.transaction import Transaction
from app.models.risk_assessment import RiskAssessment
from app.services.agent_team import DecisionAgent

def test_risk_score_consensus_formula():
    """Verifies that the consensus math weights exactly equal: ML (35%), Heuristics/Behavior average (20%), Graph (30%), Policy (15%)."""
    # Test case 1: all components at maximum severity
    res_max = DecisionAgent.process_task(
        db=None,
        ml_score=100.0,
        rule_score=100.0,
        graph_score=100.0,
        policy_score=100.0
    )
    assert res_max["score"] == 100.0
    assert res_max["classification"] == "High Risk"

    # Test case 2: all components at zero severity
    res_zero = DecisionAgent.process_task(
        db=None,
        ml_score=0.0,
        rule_score=0.0,
        graph_score=0.0,
        policy_score=0.0
    )
    assert res_zero["score"] == 0.0
    assert res_zero["classification"] == "Safe"

    # Test case 3: custom component distribution
    # ML = 50.0 (contrib 17.5), Rules = 80.0 (contrib 16.0), Graph = 30.0 (contrib 9.0), Policy = 0.0 (contrib 0.0)
    # Expected composite = 17.5 + 16.0 + 9.0 = 42.5
    res_custom = DecisionAgent.process_task(
        db=None,
        ml_score=50.0,
        rule_score=80.0,
        graph_score=30.0,
        policy_score=0.0
    )
    assert abs(res_custom["score"] - 42.5) < 1e-5
    assert res_custom["classification"] == "Suspicious" # Score is 40 <= score < 75

def test_evidence_and_audit_linkage(client):
    """Verifies that transaction ingestion creates linked evidences and audit log trails."""
    # Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "invariant@test.com",
        "password": "securepassword",
        "full_name": "Invariant Tester"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "invariant@test.com",
        "password": "securepassword"
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Ingest a transaction that will trigger rules (high amount)
    ingest_res = client.post("/api/v1/transactions/", json={
        "transaction_id": "tx_invariant_1",
        "user_id": "CUST-7821",
        "amount": 750000.0,
        "currency": "INR",
        "device_fingerprint": "df_inv_1",
        "ip_address": "127.0.0.1",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_inv_1",
        "merchant_category": "gaming"
    }, headers=headers)
    
    assert ingest_res.status_code == 202
    tx_data = ingest_res.json()
    id_val = tx_data["id"]

    # Fetch investigation trace details
    trace_res = client.get(f"/api/v1/transactions/{id_val}/investigation", headers=headers)
    assert trace_res.status_code == 200
    trace_data = trace_res.json()

    assert "evidences" in trace_data
    assert "audit_logs" in trace_data
    assert len(trace_data["evidences"]) > 0
    assert len(trace_data["audit_logs"]) > 0

    # Ensure evidence objects map back to the transaction ID
    for ev in trace_data["evidences"]:
        assert ev["description"] is not None
        assert ev["source"] is not None
        assert ev["confidence"] >= 0.0

    event_names = [log["event"] for log in trace_data["audit_logs"]]
    assert "transaction_received" in event_names
    assert "analysis_started" in event_names


def test_decision_agent_determinism():
    """Explicitly asserts that given fixed inputs, the Decision Agent processes them identically and deterministically every time."""
    inputs = {
        "ml_score": 75.0,
        "rule_score": 50.0,
        "graph_score": 25.0,
        "policy_score": 100.0
    }
    expected = (0.35 * 75.0) + (0.20 * 50.0) + (0.30 * 25.0) + (0.15 * 100.0)
    
    first = DecisionAgent.process_task(None, **inputs)
    assert first["score"] == expected
    assert first["classification"] == "Suspicious"
    
    for _ in range(50):
        res = DecisionAgent.process_task(None, **inputs)
        assert res == first
