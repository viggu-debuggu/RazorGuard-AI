from fastapi import status

def test_analyst_auth_flow(client):
    """Tests registration, login, and authorization validation workflows."""
    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json={
        "email": "analyst@test.com",
        "password": "securepassword",
        "full_name": "Test Analyst"
    })
    assert reg_res.status_code == status.HTTP_201_CREATED
    assert reg_res.json()["email"] == "analyst@test.com"

    # 2. Login
    log_res = client.post("/api/v1/auth/login", json={
        "email": "analyst@test.com",
        "password": "securepassword"
    })
    assert log_res.status_code == status.HTTP_200_OK
    assert "access_token" in log_res.json()
    token = log_res.json()["access_token"]

    # 3. Access Protected Route (Diagnostic status check)
    headers = {"Authorization": f"Bearer {token}"}
    queue_res = client.get("/api/v1/transactions/", headers=headers)
    assert queue_res.status_code == status.HTTP_200_OK
    assert isinstance(queue_res.json(), list)


def test_transaction_ingest_risk_assessment_flow(client):
    """Tests transaction ingestion, auto-agents execution, and override updates."""
    # 1. Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "analyst2@test.com",
        "password": "securepassword",
        "full_name": "Test Analyst 2"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "analyst2@test.com",
        "password": "securepassword"
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest suspicious transaction
    ingest_res = client.post("/api/v1/transactions/", json={
        "transaction_id": "tx_test_909",
        "user_id": "usr_test_99",
        "amount": 250000.0,
        "currency": "INR",
        "device_fingerprint": "df_chrome_909",
        "ip_address": "49.207.12.99",
        "billing_country": "IN",
        "card_country": "US", # country mismatch
        "card_present": False,
        "merchant_id": "mer_test_909",
        "merchant_category": "gaming"
    }, headers=headers)
    
    assert ingest_res.status_code == status.HTTP_202_ACCEPTED
    tx_data = ingest_res.json()
    assert tx_data["transaction_id"] == "tx_test_909"
    assert tx_data["status"] in ["Pending", "Approved", "Escalated"]

    # 3. Retrieve detailed investigation trace
    id_val = tx_data["id"]
    trace_res = client.get(f"/api/v1/transactions/{id_val}/investigation", headers=headers)
    assert trace_res.status_code == status.HTTP_200_OK
    trace_data = trace_res.json()
    assert "transaction" in trace_data
    assert "memories" in trace_data
    assert len(trace_data["memories"]) > 0

    # 4. Submit analyst override decision
    # Update status to Blocked
    resolve_res = client.post(f"/api/v1/transactions/{id_val}/resolve", json={
        "action": "Block",
        "notes": "Confirm credit card stolen on phone verification call."
    }, headers=headers)
    
    assert resolve_res.status_code == status.HTTP_200_OK
    assert resolve_res.json()["status"] == "Blocked"
