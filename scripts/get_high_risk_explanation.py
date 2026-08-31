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

client = TestClient(app)

# Login
log_res = client.post("/api/v1/auth/login", json={
    "email": "analyst@razorguard.ai",
    "password": "password"
})
token = log_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Fetch Investigation for TXN-92817 (id: 4)
res_inv = client.get("/api/v1/transactions/4/investigation", headers=headers)
data = res_inv.json()

print("=================================================================")
print("RAG Explanation for HIGH Risk Scenario (TXN-92817)")
print("=================================================================")
print(data["assessment"]["explanation"])

print("\n=================================================================")
print("Exact Policy Chunk(s) Retrieved from DB:")
print("=================================================================")
for idx, ev in enumerate(data["evidences"]):
    if ev["category"] == "policy_match":
        print(f"Policy Reference {idx+1}: {ev['policy_reference']}")
        print(f"  Similarity Score: {ev['value']}")
        print(f"  Description: \"{ev['description']}\"")
        print("-" * 50)
