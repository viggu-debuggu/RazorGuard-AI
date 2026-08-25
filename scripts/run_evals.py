import os
import sys
from datetime import datetime, timedelta

# Add backend directory and root directory to PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database.session import SessionLocal, engine, Base
from app.models.transaction import Transaction
from app.models.user import User
from app.services.agent_orchestrator import AgentOrchestrator
from app.models.graph import GraphEdge

def main():
    print("==============================================================")
    print("RAZORGUARD AI BUILDATHON - SCENARIO EVALUATION RUNNER")
    print("==============================================================")
    
    # 1. Reset DB and recreate tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create a mock analyst / user
        test_user = User(
            email="eval_analyst@razorguard.ai",
            password_hash="mock",
            full_name="Evaluation Inspector",
            is_active=True
        )
        db.add(test_user)
        db.flush()
        
        # Scenario definitions
        scenarios = [
            # 1. Baseline Clean Transaction
            {
                "name": "Scenario 1: Clean Transaction",
                "tx_id": "TXN-EVAL-001",
                "user_id": "CUST-CLEAN",
                "amount": 1200.0,
                "currency": "INR",
                "device_fingerprint": "df_clean",
                "ip_address": "49.207.1.1",
                "billing_country": "IN",
                "card_country": "IN",
                "card_present": True,
                "merchant_id": "mer_clean",
                "merchant_category": "food",
                "setup": None
            },
            # 2. Large Ticket Limit Breach (> 500,000)
            {
                "name": "Scenario 2: Large Ticket Breach",
                "tx_id": "TXN-EVAL-002",
                "user_id": "CUST-LARGE",
                "amount": 600000.0,
                "currency": "INR",
                "device_fingerprint": "df_large",
                "ip_address": "49.207.1.2",
                "billing_country": "IN",
                "card_country": "IN",
                "card_present": True,
                "merchant_id": "mer_large",
                "merchant_category": "retail",
                "setup": None
            },
            # 3. Geographic Country Mismatch
            {
                "name": "Scenario 3: Geographic Mismatch",
                "tx_id": "TXN-EVAL-003",
                "user_id": "CUST-GEO",
                "amount": 4500.0,
                "currency": "INR",
                "device_fingerprint": "df_geo",
                "ip_address": "49.207.1.3",
                "billing_country": "IN",
                "card_country": "US",
                "card_present": False,
                "merchant_id": "mer_geo",
                "merchant_category": "retail",
                "setup": None
            },
            # 4. High Value Card-Not-Present (> 50,000)
            {
                "name": "Scenario 4: High Value CNP",
                "tx_id": "TXN-EVAL-004",
                "user_id": "CUST-CNP",
                "amount": 75000.0,
                "currency": "INR",
                "device_fingerprint": "df_cnp",
                "ip_address": "49.207.1.4",
                "billing_country": "IN",
                "card_country": "IN",
                "card_present": False,
                "merchant_id": "mer_cnp",
                "merchant_category": "retail",
                "setup": None
            },
            # 5. High Velocity Spike (> 5 payments in 1 hour)
            {
                "name": "Scenario 5: High Velocity Spike",
                "tx_id": "TXN-EVAL-005",
                "user_id": "CUST-VELOCITY",
                "amount": 1500.0,
                "currency": "INR",
                "device_fingerprint": "df_velocity",
                "ip_address": "49.207.1.5",
                "billing_country": "IN",
                "card_country": "IN",
                "card_present": True,
                "merchant_id": "mer_velocity",
                "merchant_category": "food",
                "setup": lambda db, u_id: seed_velocity_data(db, u_id)
            },
            # 6. Spend Amount Deviation from Avg (3x avg spend > 10,000)
            {
                "name": "Scenario 6: Spend Amount Deviation",
                "tx_id": "TXN-EVAL-006",
                "user_id": "CUST-DEV",
                "amount": 25000.0,
                "currency": "INR",
                "device_fingerprint": "df_dev",
                "ip_address": "49.207.1.6",
                "billing_country": "IN",
                "card_country": "IN",
                "card_present": True,
                "merchant_id": "mer_dev",
                "merchant_category": "food",
                "setup": lambda db, u_id: seed_historical_spend(db, u_id)
            },
            # 7. Knowledge Graph Relations Loop (Shared device overlaps)
            {
                "name": "Scenario 7: Network Overlap Loop",
                "tx_id": "TXN-EVAL-007",
                "user_id": "CUST-GRAPH-MAIN",
                "amount": 2000.0,
                "currency": "INR",
                "device_fingerprint": "df_shared_device_999",
                "ip_address": "49.207.1.7",
                "billing_country": "IN",
                "card_country": "IN",
                "card_present": True,
                "merchant_id": "mer_graph",
                "merchant_category": "food",
                "setup": lambda db, u_id: seed_graph_overlaps(db, u_id)
            },
            # 8. Compliance Policy Check Match (RAG block criteria)
            {
                "name": "Scenario 8: Policy RAG Trigger",
                "tx_id": "TXN-EVAL-008",
                "user_id": "CUST-POLICY",
                "amount": 120000.0,
                "currency": "INR",
                "device_fingerprint": "df_policy",
                "ip_address": "49.207.1.8",
                "billing_country": "IN",
                "card_country": "IN",
                "card_present": False,
                "merchant_id": "mer_policy",
                "merchant_category": "gaming",
                "setup": lambda db, u_id: seed_compliance_policy(db)
            }
        ]
        
        results = []
        
        for scen in scenarios:
            print(f"Evaluating {scen['name']}...")
            # Trigger setup hook if defined
            if scen["setup"]:
                scen["setup"](db, scen["user_id"])
                
            # Create transaction
            tx = Transaction(
                transaction_id=scen["tx_id"],
                user_id=scen["user_id"],
                amount=scen["amount"],
                currency=scen["currency"],
                device_fingerprint=scen["device_fingerprint"],
                ip_address=scen["ip_address"],
                billing_country=scen["billing_country"],
                card_country=scen["card_country"],
                card_present=scen["card_present"],
                merchant_id=scen["merchant_id"],
                merchant_category=scen["merchant_category"],
                timestamp=datetime.utcnow(),
                status="Pending",
                risk_score=0.0
            )
            db.add(tx)
            db.commit()
            
            # Execute agent multi-agent sequence via orchestrator
            assessment, trace = AgentOrchestrator.run_investigation(db, tx.transaction_id)
            
            # Refresh from DB
            db.refresh(tx)
            
            results.append({
                "scenario": scen["name"],
                "tx_id": tx.transaction_id,
                "amount": f"{tx.currency} {tx.amount}",
                "score": f"{tx.risk_score:.1f}%",
                "status": tx.status,
                "classification": assessment.classification
            })
            
        print("\n=========================================================================")
        print("EVALUATION MATRIX REPORT")
        print("=========================================================================")
        print(f"{'Scenario Name':<30} | {'Tx ID':<12} | {'Amount':<12} | {'Score':<6} | {'Status':<10}")
        print("-" * 80)
        for r in results:
            print(f"{r['scenario']:<30} | {r['tx_id']:<12} | {r['amount']:<12} | {r['score']:<6} | {r['status']:<10}")
        print("=========================================================================")
        
    finally:
        db.close()

def seed_velocity_data(db, user_id):
    # Seed 6 recent transactions in the last 30 minutes to trigger velocity
    for i in range(6):
        tx = Transaction(
            transaction_id=f"TXN-VEL-{i}",
            user_id=user_id,
            amount=500.0,
            currency="INR",
            device_fingerprint=f"df_vel_{i}",
            ip_address=f"49.207.1.{10+i}",
            billing_country="IN",
            card_country="IN",
            card_present=True,
            merchant_id="mer_vel",
            merchant_category="food",
            timestamp=datetime.utcnow() - timedelta(minutes=5*i),
            status="Approved",
            risk_score=5.0
        )
        db.add(tx)
    db.commit()

def seed_historical_spend(db, user_id):
    # Seed approved transactions to establish average spend average of INR 1,800
    for i in range(3):
        tx = Transaction(
            transaction_id=f"TXN-DEV-{i}",
            user_id=user_id,
            amount=1800.0,
            currency="INR",
            device_fingerprint=f"df_dev_{i}",
            ip_address=f"49.207.1.{20+i}",
            billing_country="IN",
            card_country="IN",
            card_present=True,
            merchant_id="mer_dev",
            merchant_category="food",
            timestamp=datetime.utcnow() - timedelta(days=i+1),
            status="Approved",
            risk_score=10.0
        )
        db.add(tx)
    db.commit()

def seed_graph_overlaps(db, user_id):
    # Seed shared device matches
    edges = [
        # Link main user to device
        GraphEdge(source_type="User", source_id=f"User:{user_id}", relation="USED_DEVICE", target_type="Device", target_id="Device:df_shared_device_999", weight=1.0),
        # Link suspect account 1 to same device
        GraphEdge(source_type="User", source_id="User:usr_suspect_1", relation="USED_DEVICE", target_type="Device", target_id="Device:df_shared_device_999", weight=1.0),
        # Link suspect account 2 to same device
        GraphEdge(source_type="User", source_id="User:usr_suspect_2", relation="USED_DEVICE", target_type="Device", target_id="Device:df_shared_device_999", weight=1.0)
    ]
    for e in edges:
        db.add(e)
    db.commit()

def seed_compliance_policy(db):
    from app.models.policy import PolicyDocument
    from app.ai.embeddings import generate_embedding
    from app.ai.vector_store import save_policy_chunk
    
    # Register document
    doc = PolicyDocument(
        title="Gaming Merchant Verification Policy Rules",
        filename="gaming_policy.txt",
        checksum="checksum_gaming_policy"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    content = "Gaming merchant card-not-present transactions exceeding INR 50,000 requires strict compliance verification and must block processing pending review."
    embedding = generate_embedding(content)
    
    save_policy_chunk(
        db=db,
        document_id=doc.id,
        chunk_index=0,
        content=content,
        embedding=embedding
    )
    db.commit()

if __name__ == "__main__":
    main()
