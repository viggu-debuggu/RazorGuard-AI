from app.services.agent_team import DecisionAgent

def test_composite_risk_score_calculation():
    """Verifies that the Decision Agent computes composite scores correctly using the weighted consensus formula."""
    # S_overall = (0.35 * ml) + (0.20 * rule) + (0.30 * graph) + (0.15 * policy)
    
    # Case 1: Low Risk (Safe)
    res_low = DecisionAgent.process_task(None, ml_score=10.0, rule_score=20.0, graph_score=0.0, policy_score=0.0)
    expected_low = (0.35 * 10.0) + (0.20 * 20.0) + (0.30 * 0.0) + (0.15 * 0.0)
    assert res_low["score"] == expected_low
    assert res_low["classification"] == "Safe"

    # Case 2: Medium Risk (Suspicious)
    res_med = DecisionAgent.process_task(None, ml_score=60.0, rule_score=50.0, graph_score=50.0, policy_score=0.0)
    expected_med = (0.35 * 60.0) + (0.20 * 50.0) + (0.30 * 50.0) + (0.15 * 0.0)
    assert abs(res_med["score"] - expected_med) < 0.01
    assert res_med["classification"] == "Suspicious"

    # Case 3: High Risk
    res_high = DecisionAgent.process_task(None, ml_score=90.0, rule_score=80.0, graph_score=66.6, policy_score=100.0)
    expected_high = (0.35 * 90.0) + (0.20 * 80.0) + (0.30 * 66.6) + (0.15 * 100.0)
    assert abs(res_high["score"] - expected_high) < 0.01
    assert res_high["classification"] == "High Risk"
