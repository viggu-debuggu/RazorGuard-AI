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


def test_merchant_resolution_flow(client, db_session):
    """Tests the full merchant submit resolution loop: Flagged -> merchant submits notes/docs -> re-score -> Approved status and submissions retrieval."""
    from datetime import datetime, timedelta
    from app.models.policy import PolicyDocument, PolicyChunk
    from app.models.graph import GraphEdge
    from app.models.transaction import Transaction

    # Seed single policy manual chunk
    doc = db_session.query(PolicyDocument).filter(PolicyDocument.filename == "test_policy.txt").first()
    if not doc:
        doc = PolicyDocument(title="Verification Directive", filename="test_policy.txt", checksum="ch_hash")
        db_session.add(doc)
        db_session.flush()
        c1 = PolicyChunk(
            document_id=doc.id, 
            chunk_index=0, 
            content="gaming merchant categories card-not-present limitations and compliance verification block requires verification limit", 
            embedding=[0.1]*384
        )
        db_session.add(c1)
        db_session.commit()

    # Seed Graph walking paths for device fingerprint overlaps
    db_session.add(GraphEdge(source_type="User", source_id="usr_suspect_1", relation="INITIATED", target_type="Transaction", target_id="tx_suspect_1", weight=1.0))
    db_session.add(GraphEdge(source_type="Transaction", source_id="tx_suspect_1", relation="FROM_DEVICE", target_type="Device", target_id="df_res_001", weight=1.0))

    db_session.add(GraphEdge(source_type="User", source_id="usr_suspect_2", relation="INITIATED", target_type="Transaction", target_id="tx_suspect_2", weight=1.0))
    db_session.add(GraphEdge(source_type="Transaction", source_id="tx_suspect_2", relation="FROM_DEVICE", target_type="Device", target_id="df_res_001", weight=1.0))

    # Seed shared device connections in GraphEdge table for ML features (target_id matches device_fingerprint exactly)
    db_session.add(GraphEdge(source_type="User", source_id="usr_merch_res_001", relation="USED_DEVICE", target_type="Device", target_id="df_res_001", weight=1.0))
    db_session.add(GraphEdge(source_type="User", source_id="usr_suspect_1", relation="USED_DEVICE", target_type="Device", target_id="df_res_001", weight=1.0))
    db_session.add(GraphEdge(source_type="User", source_id="usr_suspect_2", relation="USED_DEVICE", target_type="Device", target_id="df_res_001", weight=1.0))

    # Seed 5 transactions in the last hour to trigger VELOCITY_SPIKE_1H in BehavioralRiskAgent
    # and increase velocity_1h_including_current count to 6 in the ML features (which moves the feature vector closer to High Risk centroid)
    for i in range(5):
        db_session.add(Transaction(
            transaction_id=f"tx_recent_velocity_{i}",
            user_id="usr_merch_res_001",
            amount=100.0,
            currency="INR",
            device_fingerprint="df_res_001",
            ip_address="49.207.12.99",
            billing_country="IN",
            card_country="IN",
            card_present=True,
            merchant_id="mer_res_001",
            merchant_category="gaming",
            status="Pending",
            risk_score=0.0
        ))
    db_session.commit()

    # 1. Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "merchant_test@test.com",
        "password": "securepassword",
        "full_name": "Merchant Tester"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "merchant_test@test.com",
        "password": "securepassword"
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest highly suspicious transaction (amount 600,000 + card country mismatch + CNP + device overlaps -> High Risk status)
    ingest_res = client.post("/api/v1/transactions/", json={
        "transaction_id": "tx_merchant_res_001",
        "user_id": "usr_merch_res_001",
        "amount": 600000.0,
        "currency": "INR",
        "device_fingerprint": "df_res_001",
        "ip_address": "49.207.12.99",
        "billing_country": "IN",
        "card_country": "US", # mismatch -> High Risk
        "card_present": False,
        "merchant_id": "mer_res_001",
        "merchant_category": "gaming"
    }, headers=headers)
    
    assert ingest_res.status_code == status.HTTP_202_ACCEPTED
    tx_data = ingest_res.json()
    id_val = tx_data["id"]

    # Retrieve initial investigation details (verify Escalated and risk score >= 75%)
    trace_res = client.get(f"/api/v1/transactions/{id_val}/investigation", headers=headers)
    trace_data = trace_res.json()
    assert trace_data["transaction"]["status"] == "Escalated"
    assert trace_data["transaction"]["risk_score"] >= 75.0

    # 3. Submit generic/insufficient merchant evidence (no velocity, graph or policy keywords, no target_category)
    submit_res = client.post(f"/api/v1/transactions/{id_val}/merchant-submit", json={
        "notes": "Verified buyer billing address matches, signed delivery receipt attached.",
        "document_url": "signed_delivery_receipt.pdf"
    }, headers=headers)

    assert submit_res.status_code == status.HTTP_200_OK
    
    # Query investigation endpoint to fetch updated transaction details from background task
    chk_res = client.get(f"/api/v1/transactions/{id_val}/investigation", headers=headers)
    sub_tx_data = chk_res.json()["transaction"]
    
    # Assert status transitioned to Approved but risk score is only reduced (still > 0.0)
    assert sub_tx_data["status"] == "Approved"
    assert 0.0 < sub_tx_data["risk_score"] < 75.0

    # 4. Now submit category-specific resolving evidence for the remaining flags (velocity, graph, policy)
    # velocity submission
    client.post(f"/api/v1/transactions/{id_val}/merchant-submit", json={
        "notes": "Verifying transaction spending frequency limits.",
        "target_category": "velocity"
    }, headers=headers)

    # graph submission
    client.post(f"/api/v1/transactions/{id_val}/merchant-submit", json={
        "notes": "Verifying shared device fingerprint overlaps.",
        "target_category": "graph"
    }, headers=headers)

    # policy submission
    submit_final = client.post(f"/api/v1/transactions/{id_val}/merchant-submit", json={
        "notes": "Verifying policy compliance rules.",
        "target_category": "policy"
    }, headers=headers)

    assert submit_final.status_code == status.HTTP_200_OK
    
    # Query investigation endpoint to fetch updated transaction details from final background task
    chk_res_final = client.get(f"/api/v1/transactions/{id_val}/investigation", headers=headers)
    final_tx_data = chk_res_final.json()["transaction"]

    # Assert status is Approved and score is now fully resolved (only baseline ML score contributes)
    assert final_tx_data["status"] == "Approved"
    assert abs(final_tx_data["risk_score"] - (0.35 * 74.934)) < 1.0

    # 5. Check that submissions are included in investigation query
    chk_res = client.get(f"/api/v1/transactions/{id_val}/investigation", headers=headers)
    chk_data = chk_res.json()
    assert "submissions" in chk_data
    assert len(chk_data["submissions"]) == 4
    assert chk_data["submissions"][0]["notes"] == "Verified buyer billing address matches, signed delivery receipt attached."
    assert chk_data["submissions"][0]["document_url"] == "signed_delivery_receipt.pdf"
    assert chk_data["submissions"][0]["status"] == "Submitted"


def test_submit_analyst_decision_with_evidence(client, db_session):
    """Submits an analyst override decision for a transaction with real evidence attached and asserts it does not crash."""
    from app.models.evidence import Evidence
    from app.models.transaction import Transaction

    # 1. Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "analyst_decision@test.com",
        "password": "securepassword",
        "full_name": "Analyst Override Tester"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "analyst_decision@test.com",
        "password": "securepassword"
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Ingest transaction
    ingest_res = client.post("/api/v1/transactions/", json={
        "transaction_id": "tx_decision_override_99",
        "user_id": "usr_override_99",
        "amount": 12000.0,
        "currency": "INR",
        "device_fingerprint": "df_override_99",
        "ip_address": "49.207.12.99",
        "billing_country": "IN",
        "card_country": "IN",
        "card_present": True,
        "merchant_id": "mer_override_99",
        "merchant_category": "gaming"
    }, headers=headers)
    assert ingest_res.status_code == status.HTTP_202_ACCEPTED
    tx_data = ingest_res.json()
    id_val = tx_data["id"]

    # 3. Explicitly seed a real evidence record in the database
    db_session.add(Evidence(
        transaction_id=id_val,
        evidence_id="EV-OVERRIDE-TEST-1",
        category="rules",
        severity="medium",
        value="Test Value",
        description="Test Evidence Description",
        source="Test Source",
        confidence=1.0
    ))
    db_session.commit()

    # 4. Post the analyst decision
    resolve_res = client.post(f"/api/v1/transactions/{id_val}/resolve", json={
        "action": "Approve",
        "notes": "Verified manual whitelist override."
    }, headers=headers)
    assert resolve_res.status_code == status.HTTP_200_OK
    data = resolve_res.json()
    assert data["status"] == "Approved"


def test_first_user_role_assignment_without_admin_env(client):
    """Tests that by default (ALLOW_FIRST_USER_ADMIN=False), the first registered user gets the Analyst role."""
    from app.core.config import settings
    # Ensure settings has ALLOW_FIRST_USER_ADMIN set to False
    settings.ALLOW_FIRST_USER_ADMIN = False

    reg_res = client.post("/api/v1/auth/register", json={
        "email": "first_user_no_admin@test.com",
        "password": "securepassword",
        "full_name": "First User Analyst"
    })
    assert reg_res.status_code == status.HTTP_201_CREATED
    user_data = reg_res.json()
    assert user_data["role"] == "Analyst"


def test_first_user_role_assignment_with_admin_env(client):
    """Tests that when ALLOW_FIRST_USER_ADMIN=True, the first registered user gets the Super Admin role."""
    from app.core.config import settings
    settings.ALLOW_FIRST_USER_ADMIN = True

    reg_res = client.post("/api/v1/auth/register", json={
        "email": "first_user_admin@test.com",
        "password": "securepassword",
        "full_name": "First User Super Admin"
    })
    assert reg_res.status_code == status.HTTP_201_CREATED
    user_data = reg_res.json()
    assert user_data["role"] == "Super Admin"


def test_jwt_claims_token_type_mismatch(client):
    """Tests that access tokens cannot be used as refresh tokens and vice versa."""
    # 1. Register & Login
    client.post("/api/v1/auth/register", json={
        "email": "claims_mismatch@test.com",
        "password": "securepassword",
        "full_name": "Claims Tester"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "claims_mismatch@test.com",
        "password": "securepassword"
    })
    token_data = log_res.json()
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]

    # 2. Try validating access token as a refresh token (should fail 401)
    refresh_res = client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token
    })
    assert refresh_res.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Try validating refresh token as an access token on a protected endpoint (should fail 401)
    headers = {"Authorization": f"Bearer {refresh_token}"}
    protected_res = client.get("/api/v1/transactions/metrics/efficiency", headers=headers)
    assert protected_res.status_code == status.HTTP_401_UNAUTHORIZED







