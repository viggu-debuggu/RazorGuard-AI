"""
RazorGuard AI — Demo Database Seeding Entrypoint
Creates default database tables, demo transactions, compliance RAG chunks, and mock graph relationships.
"""
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Demo-only placeholder analyst credentials (not for production use)
DEMO_ANALYST_EMAIL = "analyst@razorguard.ai"
DEMO_ANALYST_PASSWORD = os.getenv("DEMO_ANALYST_PASSWORD", "demo_placeholder_analyst_2026")

if __name__ == "__main__":
    from scripts.seed_data import seed_database
    seed_database()
