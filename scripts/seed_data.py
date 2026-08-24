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
        "transaction_id": "pay_safe_8801",
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
        "status": "Approved",
        "risk_score": 12.0
    },
    {
        "transaction_id": "pay_suspicious_2004",
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
        "risk_score": 62.0
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
        
        # 6. Run agent pipeline on the primary demo transaction to generate assessment, reasoning steps, and memories
        print("Running agent pipeline on primary demo transaction TXN-92817...")
        AgentOrchestrator.run_investigation(db, "TXN-92817")
        db.commit()
        
        print("SUCCESS: Database seeding finished.")
        
    except Exception as e:
        print(f"ERROR: Database seeding failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
