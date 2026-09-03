import os
import sys
import json

# Ensure backend root is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

os.environ["DATABASE_URL"] = "sqlite:///./razorguard.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["LLM_PROVIDER"] = "mock"

from fastapi.testclient import TestClient
from app.main import app
from app.database.session import SessionLocal
from app.models.transaction import Transaction

client = TestClient(app)

# 1. Register & Login
demo_password = os.getenv("DEMO_ANALYST_PASSWORD", "demo_placeholder_analyst_2026")
client.post("/api/v1/auth/register", json={
    "email": "analyst@razorguard.ai",
    "password": demo_password,
    "full_name": "Risk Analyst"
})
log_res = client.post("/api/v1/auth/login", json={
    "email": "analyst@razorguard.ai",
    "password": demo_password
})
token = log_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Get Transaction ID mapping from Database
db = SessionLocal()
txn_ids = ["TXN-10021", "TXN-40293", "TXN-92817"]
db_txs = db.query(Transaction).filter(Transaction.transaction_id.in_(txn_ids)).all()

for tx_id_target in txn_ids:
    tx = next((t for t in db_txs if t.transaction_id == tx_id_target), None)
    if not tx:
        print(f"ERROR: Transaction {tx_id_target} not found in DB.")
        continue
        
    print(f"\n=================================================================")
    print(f"JSON Response for {tx_id_target} Details (GET /api/v1/transactions/{tx.id})")
    print(f"=================================================================")
    res_details = client.get(f"/api/v1/transactions/{tx.id}", headers=headers)
    print(json.dumps(res_details.json(), indent=2))

db.close()
