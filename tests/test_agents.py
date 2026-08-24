from app.models.transaction import Transaction
from app.services.agent_team import TransactionRiskAgent, BehavioralRiskAgent

def test_transaction_risk_heuristics():
    """Verifies that TransactionRiskAgent correctly flags transaction amount and location drift rules."""
    # Case 1: Transaction with no violations
    tx_clean = Transaction(
        amount=1200.0,
        billing_country="IN",
        card_country="IN",
        card_present=True,
        merchant_category="food"
    )
    res_clean = TransactionRiskAgent.process_task(None, tx_clean)
    assert res_clean["score"] == 0.0
    assert "No heuristic rule violations" in res_clean["evidence"]

    # Case 2: Transaction with amount and location mismatches
    tx_fraud = Transaction(
        amount=600000.0, # exceeds limit
        billing_country="IN",
        card_country="US", # mismatch
        card_present=False
    )
    res_fraud = TransactionRiskAgent.process_task(None, tx_fraud)
    assert res_fraud["score"] > 0.0
    assert "LARGE_TICKET_AMOUNT" in res_fraud["evidence"]
    assert "GEOGRAPHIC_MISMATCH" in res_fraud["evidence"]
