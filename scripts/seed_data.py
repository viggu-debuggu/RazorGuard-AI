import sys
import os
import hashlib
from datetime import datetime, timedelta

# Append backend directory to sys.path to enable imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database.session import SessionLocal, Base, engine
from app.models.user import User
from app.models.transaction import Transaction
from app.models.graph import GraphEdge
from app.models.policy import PolicyDocument, PolicyChunk
from app.models.decision import AnalystDecision
from app.models.risk_assessment import RiskAssessment
from app.models.agent import AgentExecution
from app.api.dependencies.auth import get_password_hash
from app.ai.embeddings import generate_embedding
from app.ai.vector_store import save_policy_chunk
from app.services.agent_orchestrator import AgentOrchestrator

# Regulatory compliance manuals to seed
POLICY_DOCUMENTS = [
    {
        "title": "Strong Customer Authentication Guidelines (SCA)",
        "filename": "sca_directive.txt",
        "content": (
            "Clause PSD2-Art-97: Strong Customer Authentication (SCA) must be triggered for electronic "
            "payment transactions exceeding a value limit of 50 EUR (approximately INR 4,500) if the "
            "card-present status evaluates to false (Card-Not-Present remote transactions). "
            "Failure to apply SCA constitutes a severe regulatory compliance breach and results in transaction holding."
        )
    },
    {
        "title": "High Ticket Transaction Processing Policy",
        "filename": "high_ticket_policy.txt",
        "content": (
            "Clause CNP-LIMIT-08: remote digital card payments for high-risk merchant categories (like electronics, crypto, gaming) "
            "exceeding INR 50,000 are subject to immediate velocity profiling and location drift evaluation. If the card issuing country "
            "does not match the billing country of origin, the transaction must be blocked or escalated "
            "for manual analyst intervention."
        )
    }
]

# Synthetic transactions to seed
MOCK_TRANSACTIONS = [
    {
        "transaction_id": "TXN-10021",
        "user_id": "usr_safe_01",
        "amount": 1200.0,
        "currency": "INR",
        "device_fingerprint": "df_safe_chrome_1",
        "ip_address": "49.207.12.50",
        "billing_country": "IN",
        "card_country": "IN",
        "card_present": True,
        "merchant_id": "mer_razor_food_1",
        "merchant_category": "food",
        "status": "Pending",
        "risk_score": 0.0
    },
    {
        "transaction_id": "TXN-40293",
        "user_id": "usr_suspicious_02",
        "amount": 65000.0,
        "currency": "INR",
        "device_fingerprint": "df_shared_android_99",
        "ip_address": "103.45.18.2",
        "billing_country": "IN",
        "card_country": "US",  # Mismatch!
        "card_present": False, # Card-Not-Present!
        "merchant_id": "mer_razor_electronics_4",
        "merchant_category": "electronics",
        "status": "Pending",
        "risk_score": 0.0
    },
    {
        "transaction_id": "pay_fraud_9901",
        "user_id": "usr_fraud_03",
        "amount": 280000.0,  # High Amount!
        "currency": "INR",
        "device_fingerprint": "df_shared_android_99", # Shared device fingerprint!
        "ip_address": "185.120.40.15",
        "billing_country": "IN",
        "card_country": "GB",
        "card_present": False,
        "merchant_id": "mer_razor_crypto_9",
        "merchant_category": "crypto",
        "status": "Escalated",
        "risk_score": 88.0
    },
    
    # ----------------------------------------------------
    # DEMO SCENARIO SPECIFIC DATA FOR CUST-7821
    # ----------------------------------------------------
    # Primary demo transaction
    {
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
        "merchant_category": "electronics",
        "status": "Pending",
        "risk_score": 0.0
    },
    # Normal historical transactions (establish 1800 average)
    {
        "transaction_id": "tx_demo_hist_1",
        "user_id": "CUST-7821",
        "amount": 1800.0,
        "currency": "INR",
        "device_fingerprint": "df_cust_normal_1",
        "ip_address": "49.207.12.51",
        "billing_country": "IN",
        "card_country": "IN",
        "card_present": True,
        "merchant_id": "mer_razor_food_1",
        "merchant_category": "food",
        "status": "Approved",
        "risk_score": 10.0
    },
    {
        "transaction_id": "tx_demo_hist_2",
        "user_id": "CUST-7821",
        "amount": 1750.0,
        "currency": "INR",
        "device_fingerprint": "df_cust_normal_1",
        "ip_address": "49.207.12.51",
        "billing_country": "IN",
        "card_country": "IN",
        "card_present": True,
        "merchant_id": "mer_razor_food_1",
        "merchant_category": "food",
        "status": "Approved",
        "risk_score": 8.0
    },
    {
        "transaction_id": "tx_demo_hist_3",
        "user_id": "CUST-7821",
        "amount": 1850.0,
        "currency": "INR",
        "device_fingerprint": "df_cust_normal_1",
        "ip_address": "49.207.12.51",
        "billing_country": "IN",
        "card_country": "IN",
        "card_present": True,
        "merchant_id": "mer_razor_food_1",
        "merchant_category": "food",
        "status": "Approved",
        "risk_score": 11.0
    },
    {
        "transaction_id": "tx_demo_hist_4",
        "user_id": "CUST-7821",
        "amount": 1900.0,
        "currency": "INR",
        "device_fingerprint": "df_cust_normal_1",
        "ip_address": "49.207.12.51",
        "billing_country": "IN",
        "card_country": "IN",
        "card_present": True,
        "merchant_id": "mer_razor_food_1",
        "merchant_category": "food",
        "status": "Approved",
        "risk_score": 12.0
    },
    {
        "transaction_id": "tx_demo_hist_5",
        "user_id": "CUST-7821",
        "amount": 1700.0,
        "currency": "INR",
        "device_fingerprint": "df_cust_normal_1",
        "ip_address": "49.207.12.51",
        "billing_country": "IN",
        "card_country": "IN",
        "card_present": True,
        "merchant_id": "mer_razor_food_1",
        "merchant_category": "food",
        "status": "Approved",
        "risk_score": 9.0
    },
    
    # 4 Failed/declined attempts in the last 6 minutes for CUST-7821
    {
        "transaction_id": "tx_demo_fail_1",
        "user_id": "CUST-7821",
        "amount": 85000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics",
        "status": "Blocked",
        "risk_score": 85.0,
        "timestamp": datetime.utcnow() - timedelta(minutes=5)
    },
    {
        "transaction_id": "tx_demo_fail_2",
        "user_id": "CUST-7821",
        "amount": 85000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics",
        "status": "Blocked",
        "risk_score": 85.0,
        "timestamp": datetime.utcnow() - timedelta(minutes=4)
    },
    {
        "transaction_id": "tx_demo_fail_3",
        "user_id": "CUST-7821",
        "amount": 85000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics",
        "status": "Blocked",
        "risk_score": 85.0,
        "timestamp": datetime.utcnow() - timedelta(minutes=3)
    },
    {
        "transaction_id": "tx_demo_fail_4",
        "user_id": "CUST-7821",
        "amount": 85000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics",
        "status": "Blocked",
        "risk_score": 85.0,
        "timestamp": datetime.utcnow() - timedelta(minutes=2)
    },

    # Suspect transactions that shared the device fingerprint df_demo_unseen_99
    {
        "transaction_id": "tx_suspect_1",
        "user_id": "usr_suspect_1",
        "amount": 15000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics",
        "status": "Blocked",
        "risk_score": 90.0
    },
    {
        "transaction_id": "tx_suspect_2",
        "user_id": "usr_suspect_2",
        "amount": 25000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics",
        "status": "Blocked",
        "risk_score": 92.0
    },
    {
        "transaction_id": "tx_suspect_3",
        "user_id": "usr_suspect_3",
        "amount": 35000.0,
        "currency": "INR",
        "device_fingerprint": "df_demo_unseen_99",
        "ip_address": "103.45.18.99",
        "billing_country": "IN",
        "card_country": "US",
        "card_present": False,
        "merchant_id": "mer_demo_electronics",
        "merchant_category": "electronics",
        "status": "Blocked",
        "risk_score": 95.0
    }
]

# Shared network connections to populate the graph
MOCK_GRAPH_EDGES = [
    # Shared device fingerprint between Suspicious account and Fraud account
    ("User:usr_suspicious_02", "df_shared_android_99", "USED_DEVICE", "Device"),
    ("User:usr_fraud_03", "df_shared_android_99", "USED_DEVICE", "Device"),
    
    # Shared IP address
    ("User:usr_safe_01", "49.207.12.50", "USED_IP", "IP"),
    ("User:usr_suspicious_02", "103.45.18.2", "USED_IP", "IP"),

    # ----------------------------------------------------
    # DEMO SCENARIO SPECIFIC GRAPH CONNECTIONS
    # ----------------------------------------------------
    # Suspect 1 device overlaps
    ("User:usr_suspect_1", "tx_suspect_1", "INITIATED", "Transaction"),
    ("Transaction:tx_suspect_1", "df_demo_unseen_99", "FROM_DEVICE", "Device"),
    ("User:usr_suspect_1", "df_demo_unseen_99", "USED_DEVICE", "Device"),

    # Suspect 2 device overlaps
    ("User:usr_suspect_2", "tx_suspect_2", "INITIATED", "Transaction"),
    ("Transaction:tx_suspect_2", "df_demo_unseen_99", "FROM_DEVICE", "Device"),
    ("User:usr_suspect_2", "df_demo_unseen_99", "USED_DEVICE", "Device"),

    # Suspect 3 device overlaps
    ("User:usr_suspect_3", "tx_suspect_3", "INITIATED", "Transaction"),
    ("Transaction:tx_suspect_3", "df_demo_unseen_99", "FROM_DEVICE", "Device"),
    ("User:usr_suspect_3", "df_demo_unseen_99", "USED_DEVICE", "Device"),
]


def seed_database():
    db = SessionLocal()
    try:
        print("Starting Database Seeder...")
        
        # 1. Ensure tables are created
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Clear existing tables to ensure clean seed
        db.query(User).delete()
        db.query(Transaction).delete()
        db.query(GraphEdge).delete()
        db.query(PolicyDocument).delete()
        db.query(PolicyChunk).delete()
        db.commit()
        
        # 2. Seed default Analyst user
        analyst_email = "analyst@razorguard.ai"
        hashed_pw = get_password_hash("password")
        user = User(
            email=analyst_email,
            full_name="Alex Mercer",
            password_hash=hashed_pw,
            role="Super Admin",
            is_active=True
        )
        db.add(user)
        print(f"Seeded default user: {analyst_email} / password")
            
        # 3. Seed transactions
        for tx_data in MOCK_TRANSACTIONS:
            tx = Transaction(**tx_data)
            db.add(tx)
            print(f"Seeded transaction: {tx_data['transaction_id']}")
                
        # 4. Seed compliance policy documents
        for doc_data in POLICY_DOCUMENTS:
            content = doc_data["content"]
            checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
            
            doc = PolicyDocument(
                title=doc_data["title"],
                filename=doc_data["filename"],
                checksum=checksum
            )
            db.add(doc)
            db.flush()
            
            # Chunk and Embed
            embedding = generate_embedding(content)
            save_policy_chunk(
                db=db,
                document_id=doc.id,
                chunk_index=0,
                content=content,
                embedding=embedding
            )
            print(f"Seeded and indexed policy: {doc_data['title']}")
                
        # 5. Seed graph relationships
        for src_node, tgt_id, relation, tgt_type in MOCK_GRAPH_EDGES:
            src_type, src_id = src_node.split(":", 1)
            
            edge = GraphEdge(
                source_type=src_type,
                source_id=src_id,
                relation=relation,
                target_type=tgt_type,
                target_id=tgt_id,
                weight=1.0
            )
            db.add(edge)
            print(f"Seeded Graph edge: ({src_node}) -[{relation}]-> ({tgt_type}:{tgt_id})")

        db.commit()
        
        # 6. Run agent pipeline on the three reproducible scenarios to generate assessments, reasoning steps, and memories
        print("Running agent pipeline on Scenario A: LOW RISK (TXN-10021)...")
        AgentOrchestrator.run_investigation(db, "TXN-10021")
        
        print("Running agent pipeline on Scenario B: MEDIUM RISK (TXN-40293)...")
        AgentOrchestrator.run_investigation(db, "TXN-40293")
        
        print("Running agent pipeline on Scenario C: HIGH RISK (TXN-92817)...")
        AgentOrchestrator.run_investigation(db, "TXN-92817")
        db.commit()
        
        # 7. Seed analyst decision overrides for Scenarios B and C to provide realistic metrics out of the box
        print("Seeding analyst overrides for Scenario B & Scenario C...")
        analyst_user = db.query(User).filter(User.email == "analyst@razorguard.ai").first()
        if analyst_user:
            from app.models.evidence import Evidence
            from app.models.audit_log import AuditLog

            # Scenario B: TXN-40293
            tx_b = db.query(Transaction).filter(Transaction.transaction_id == "TXN-40293").first()
            if tx_b:
                assessment_b = db.query(RiskAssessment).filter(RiskAssessment.transaction_id == tx_b.id).first()
                if assessment_b:
                    dec_b = db.query(AnalystDecision).filter(AnalystDecision.transaction_id == tx_b.id).first()
                    if not dec_b:
                        submitted_time_b = assessment_b.analyzed_at + timedelta(minutes=3, seconds=45)
                        original_rec_b = tx_b.status
                        
                        # Capture evidence snapshot
                        evs_b = db.query(Evidence).filter(Evidence.transaction_id == tx_b.id).all()
                        snapshot_b = []
                        for e in evs_b:
                            snapshot_b.append({
                                "evidence_id": e.evidence_id,
                                "category": e.category,
                                "severity": e.severity,
                                "value": e.value,
                                "description": e.description,
                                "source": e.source,
                                "confidence": e.confidence,
                                "timestamp": e.timestamp.isoformat()
                            })

                        dec_b = AnalystDecision(
                            transaction_id=tx_b.id,
                            analyst_id=analyst_user.id,
                            action="Approve",
                            notes="Verified billing country IN matches card issuing country US due to customer remote work status verified via OTP.",
                            original_ai_recommendation=original_rec_b,
                            submitted_at=submitted_time_b,
                            risk_score_at_decision_time=tx_b.risk_score,
                            evidence_snapshot=snapshot_b
                        )
                        db.add(dec_b)
                        tx_b.status = "Approved"
                        db.add(tx_b)
                        
                        # Add AuditLog
                        log_b = AuditLog(
                            transaction_id=tx_b.id,
                            event="decision_overridden",
                            description=f"Analyst override committed. Final status transitioned from '{original_rec_b}' to 'Approved' with notes: \"{dec_b.notes}\".",
                            actor=f"Analyst: {analyst_user.email}",
                            timestamp=submitted_time_b
                        )
                        db.add(log_b)
                        print("Seeded AnalystDecision override for TXN-40293.")
            
            # Scenario C: TXN-92817
            tx_c = db.query(Transaction).filter(Transaction.transaction_id == "TXN-92817").first()
            if tx_c:
                assessment_c = db.query(RiskAssessment).filter(RiskAssessment.transaction_id == tx_c.id).first()
                if assessment_c:
                    dec_c = db.query(AnalystDecision).filter(AnalystDecision.transaction_id == tx_c.id).first()
                    if not dec_c:
                        submitted_time_c = assessment_c.analyzed_at + timedelta(minutes=5, seconds=12)
                        original_rec_c = tx_c.status

                        # Capture evidence snapshot
                        evs_c = db.query(Evidence).filter(Evidence.transaction_id == tx_c.id).all()
                        snapshot_c = []
                        for e in evs_c:
                            snapshot_c.append({
                                "evidence_id": e.evidence_id,
                                "category": e.category,
                                "severity": e.severity,
                                "value": e.value,
                                "description": e.description,
                                "source": e.source,
                                "confidence": e.confidence,
                                "timestamp": e.timestamp.isoformat()
                            })

                        dec_c = AnalystDecision(
                            transaction_id=tx_c.id,
                            analyst_id=analyst_user.id,
                            action="Block",
                            notes="Confirmed hardware device fingerprint df_demo_unseen_99 overlaps with 3 blocked suspect accounts.",
                            original_ai_recommendation=original_rec_c,
                            submitted_at=submitted_time_c,
                            risk_score_at_decision_time=tx_c.risk_score,
                            evidence_snapshot=snapshot_c
                        )
                        db.add(dec_c)
                        tx_c.status = "Blocked"
                        db.add(tx_c)

                        # Add AuditLog
                        log_c = AuditLog(
                            transaction_id=tx_c.id,
                            event="decision_overridden",
                            description=f"Analyst override committed. Final status transitioned from '{original_rec_c}' to 'Blocked' with notes: \"{dec_c.notes}\".",
                            actor=f"Analyst: {analyst_user.email}",
                            timestamp=submitted_time_c
                        )
                        db.add(log_c)
                        print("Seeded AnalystDecision override for TXN-92817.")
            
            # Ensure AgentExecution duration is non-zero
            executions = db.query(AgentExecution).all()
            for exe in executions:
                if exe.duration == 0.0 or not exe.duration:
                    exe.duration = 0.85
                    db.add(exe)

            db.commit()

        print("SUCCESS: Database seeding finished.")
        
    except Exception as e:
        print(f"ERROR: Database seeding failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
