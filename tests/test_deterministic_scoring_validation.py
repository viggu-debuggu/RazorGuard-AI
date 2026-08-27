import pytest
from fastapi import status
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.policy import PolicyDocument, PolicyChunk
from app.models.evidence import Evidence


def test_deterministic_scoring_multiple_ingestions(client, db_session):
    """
    Ingests the exact same transaction payload 10 times under unique transaction IDs,
    asserting that all runs produce identical composite risk scores and classifications.
    To avoid stateful DB accumulation (which would naturally increase velocity count),
    we use a unique user_id for each run to isolate the velocity metric.
    """
    # 1. Register & Login Analyst
    client.post("/api/v1/auth/register", json={
        "email": "det_analyst@test.com",
        "password": "securepassword",
        "full_name": "Det Analyst"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "det_analyst@test.com",
        "password": "securepassword"
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    scores = []
    classifications = []

    # 2. Ingest 10 identical payloads with unique transaction IDs and isolated user_ids
    for i in range(10):
        tx_id = f"tx_deterministic_{i}"
        user_id = f"usr_det_test_{i}"  # Unique user_id ensures velocity count remains exactly 1 across runs
        ingest_res = client.post("/api/v1/transactions/", json={
            "transaction_id": tx_id,
            "user_id": user_id,
            "amount": 250000.0,
            "currency": "INR",
            "device_fingerprint": "df_det_chrome",
            "ip_address": "49.207.12.99",
            "billing_country": "IN",
            "card_country": "US",
            "card_present": False,
            "merchant_id": "mer_det_store",
            "merchant_category": "gaming"
        }, headers=headers)
        
        assert ingest_res.status_code == status.HTTP_202_ACCEPTED
        tx_data = ingest_res.json()
        db_tx_id = tx_data["id"]

        # Fetch investigation trace (background task runs synchronously in TestClient)
        trace_res = client.get(f"/api/v1/transactions/{db_tx_id}/investigation", headers=headers)
        assert trace_res.status_code == status.HTTP_200_OK
        trace_data = trace_res.json()
        
        assessment = trace_data["assessment"]
        assert assessment is not None
        
        scores.append(assessment["overall_score"])
        classifications.append(assessment["classification"])

    # 3. Assert all scores and classifications are identical
    first_score = scores[0]
    first_classification = classifications[0]
    
    for score in scores:
        assert score == first_score, f"Scoring is non-deterministic: {score} != {first_score}"
        
    for cls in classifications:
        assert cls == first_classification, f"Classification is non-deterministic: {cls} != {first_classification}"


def test_independent_analyst_reviews(client, db_session):
    """
    Simulates two analysts independently reviewing the same transaction,
    asserting that both retrieve the identical overall risk score.
    """
    # 1. Register & Login Analyst A
    client.post("/api/v1/auth/register", json={
        "email": "analyst_a@test.com",
        "password": "securepassword",
        "full_name": "Analyst A"
    })
    log_a = client.post("/api/v1/auth/login", json={
        "email": "analyst_a@test.com",
        "password": "securepassword"
    })
    token_a = log_a.json()["access_token"]

    # 2. Register & Login Analyst B
    client.post("/api/v1/auth/register", json={
        "email": "analyst_b@test.com",
        "password": "securepassword",
        "full_name": "Analyst B"
    })
    log_b = client.post("/api/v1/auth/login", json={
        "email": "analyst_b@test.com",
        "password": "securepassword"
    })
    token_b = log_b.json()["access_token"]

    # 3. Ingest a transaction using Analyst A
    ingest_res = client.post("/api/v1/transactions/", json={
        "transaction_id": "tx_analyst_review_999",
        "user_id": "usr_review_test",
        "amount": 120000.0,
        "currency": "INR",
        "device_fingerprint": "df_review_chrome",
        "ip_address": "49.207.12.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_review_store",
        "merchant_category": "gaming"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert ingest_res.status_code == status.HTTP_202_ACCEPTED
    tx_data = ingest_res.json()
    db_tx_id = tx_data["id"]

    # 4. Analyst A fetches the investigation details
    res_a = client.get(f"/api/v1/transactions/{db_tx_id}/investigation", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == status.HTTP_200_OK
    score_a = res_a.json()["assessment"]["overall_score"]

    # 5. Analyst B fetches the identical investigation details
    res_b = client.get(f"/api/v1/transactions/{db_tx_id}/investigation", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == status.HTTP_200_OK
    score_b = res_b.json()["assessment"]["overall_score"]

    # 6. Assert both analysts retrieve identical scores
    assert score_a == score_b, f"Independent reviews yielded different scores: {score_a} != {score_b}"


def test_hero_scenario_policy_reference_format(client, db_session):
    """
    Ingests the TXN-92817 hero scenario profile (amount > 50000 and CNP electronics category)
    and asserts that the Policy Compliance Score component triggers (100.0)
    and at least one Evidence entry has a non-null, correctly formatted policy_reference field.
    """
    # 1. Register & Login Analyst
    client.post("/api/v1/auth/register", json={
        "email": "hero_analyst@test.com",
        "password": "securepassword",
        "full_name": "Hero Analyst"
    })
    log_res = client.post("/api/v1/auth/login", json={
        "email": "hero_analyst@test.com",
        "password": "securepassword"
    })
    token = log_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Seed a PolicyDocument and matching PolicyChunk in the DB
    doc = PolicyDocument(title="Electronics Compliance Manual", filename="electronics_policy.pdf", checksum="elec_hash_123")
    db_session.add(doc)
    db_session.flush()
    
    chunk = PolicyChunk(
        document_id=doc.id,
        chunk_index=5,
        content="Merchant categories electronics card-not-present limitations require verification and block if unauthorized.",
        embedding=[0.1] * 384
    )
    db_session.add(chunk)
    db_session.commit()

    # 3. Ingest TXN-92817 hero scenario payload
    ingest_res = client.post("/api/v1/transactions/", json={
        "transaction_id": "TXN-92817",
        "user_id": "CUST-7821",
        "amount": 85000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics"
    }, headers=headers)
    
    assert ingest_res.status_code == status.HTTP_202_ACCEPTED
    tx_data = ingest_res.json()
    db_tx_id = tx_data["id"]

    # 4. Fetch the investigation details
    trace_res = client.get(f"/api/v1/transactions/{db_tx_id}/investigation", headers=headers)
    assert trace_res.status_code == status.HTTP_200_OK
    trace_data = trace_res.json()
    
    assessment = trace_data["assessment"]
    assert assessment is not None
    
    # Assert Policy component is triggered to 100%
    assert assessment["policy_score"] == 100.0
    
    # Assert structured evidence contains correctly formatted policy_reference
    evidences = trace_data["evidences"]
    assert len(evidences) > 0
    
    policy_evidences = [ev for ev in evidences if ev["category"] == "policy_match"]
    assert len(policy_evidences) > 0, "No policy_match evidence entries found."
    
    # Assert at least one has non-null, correctly formatted policy_reference
    has_valid_ref = False
    for ev in policy_evidences:
        ref = ev["policy_reference"]
        if ref == "policies/electronics_policy.pdf#chunk_5":
            has_valid_ref = True
            break
            
    assert has_valid_ref, f"None of the policy evidence entries matched 'policies/electronics_policy.pdf#chunk_5'. Found: {[ev.get('policy_reference') for ev in policy_evidences]}"
