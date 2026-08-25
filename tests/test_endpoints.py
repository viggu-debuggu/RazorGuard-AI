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


def test_analyst_efficiency_metrics(client):
    """Tests registration, transaction ingestion, resolution, and verification of efficiency metrics."""
    # 1. Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "metrics_analyst@test.com",
        "password": "securepassword",
        "full_name": "Metrics Analyst"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "metrics_analyst@test.com",
        "password": "securepassword"
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest transaction
    ingest_res = client.post("/api/v1/transactions/", json={
        "transaction_id": "tx_efficiency_test_99",
        "user_id": "usr_metrics_99",
        "amount": 250000.0,
        "currency": "INR",
        "device_fingerprint": "df_efficiency_99",
        "ip_address": "49.207.12.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_metrics_99",
        "merchant_category": "gaming"
    }, headers=headers)
    assert ingest_res.status_code == status.HTTP_202_ACCEPTED
    tx_data = ingest_res.json()
    id_val = tx_data["id"]

    # 3. Submit analyst override decision
    resolve_res = client.post(f"/api/v1/transactions/{id_val}/resolve", json={
        "action": "Block",
        "notes": "Verify suspect behavior under evaluation guidelines."
    }, headers=headers)
    assert resolve_res.status_code == status.HTTP_200_OK

    # 4. Get efficiency metrics
    metrics_res = client.get("/api/v1/transactions/metrics/efficiency", headers=headers)
    assert metrics_res.status_code == status.HTTP_200_OK
    metrics_data = metrics_res.json()
    
    # Assert fields are present
    assert "avg_investigation_time_seconds" in metrics_data
    assert "avg_analyst_review_minutes" in metrics_data
    assert "total_cases_processed" in metrics_data
    assert "total_overrides_submitted" in metrics_data
    assert "pct_decisions_with_justification" in metrics_data
    assert "cases_by_classification" in metrics_data

    # Assert values
    assert metrics_data["total_cases_processed"] >= 1
    assert metrics_data["total_overrides_submitted"] >= 1
    assert metrics_data["pct_decisions_with_justification"] == 100.0


def test_refresh_token_rotation(client):
    """Tests refresh token redemption, rotation, and validation workflows."""
    # 1. Register & Login to get initial refresh token
    client.post("/api/v1/auth/register", json={
        "email": "refresh_test@test.com",
        "password": "securepassword",
        "full_name": "Refresh Tester"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "refresh_test@test.com",
        "password": "securepassword"
    })
    assert log_res.status_code == 200
    res_data = log_res.json()
    refresh_token = res_data["refresh_token"]

    # 2. Redeem refresh token
    ref_res = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    assert "access_token" in ref_data
    assert "refresh_token" in ref_data
    new_refresh = ref_data["refresh_token"]
    assert new_refresh != refresh_token

    # 3. Test old refresh token is now invalid (rotated out)
    fail_res = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert fail_res.status_code == 401


