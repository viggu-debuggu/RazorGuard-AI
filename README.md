# 🛡️ RazorGuard AI
### Autonomous Multi-Agent Payment Risk Manager

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.0-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![Next.js](https://img.shields.io/badge/Next.js-15.0-black?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.2-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![pgvector](https://img.shields.io/badge/pgvector-0.6.0-red?logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

**RazorGuard AI** is an autonomous risk mitigation and compliance platform built for the **Razorpay AI Builder Buildathon 2026** (AI Risk Manager Track). 

By integrating real-time transaction heuristics, **Multi-Agent Collaborative Reasoning**, a **Semantic Payment Knowledge Graph**, and a **Policy-Based RAG System**, the platform acts as an automated investigator for payment fraud detection and compliance verification.

---

## 🚀 Core Workflow

```
Payment Transaction
   │
   ▼
1. Risk Detection (ML Anomaly Classifier flagsSuspicious inputs)
   │
   ▼
2. Multi-Agent Investigation (Coordinated Specialists analyze transaction metadata, location drift, devices)
   │
   ▼
3. Evidence Retrieval (Hybrid RAG checks PSD2/compliance policies & queries NetworkX Knowledge Graph for fraud loops)
   │
   ▼
4. Unified Risk Scoring (Agents compute weighted scoring indexes)
   │
   ▼
5. Explainable Decision (LLM compiles a natural language reasoning trace & report)
   │
   ▼
6. Human Escalation (Dashboard enables analysts to review trace, investigate graph, override decisions)
```

---

## 📁 Project Structure

```
RazorGuard-AI/
├── backend/                       # FastAPI Web Services & DB integrations
├── frontend/                      # Next.js 15 Client Web Console
├── ml/                            # Centroid anomaly classifier files
├── rag/                           # Regulatory compliance documents
├── knowledge_graph/               # NetworkX relation builder
├── data/                          # SQLite/Postgres local configurations
├── docs/                          # Developer design guides
├── tests/                         # Pytest automated testing suite
└── scripts/                       # Database seeding and migration commands
```

---

## 🛠️ Installation & Setup (Local)

### Prerequisites
* **Python**: Version 3.12.x
* **Node.js**: Version 20.x or above
* **PostgreSQL**: Version 16.x (or run using Docker)

### Step 1: Clone and Configure Environment
```bash
git clone https://github.com/viggu-debuggu/RazorGuard-AI.git
cd RazorGuard-AI
cp .env.example .env
```

### Step 2: Backend Setup
```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
# Run migrations (after db setup)
alembic upgrade head
```

### Step 3: Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```

---

## 🐳 Docker Deployment (Recommended)

To spin up the entire cluster (PostgreSQL + pgvector, Backend, Frontend):
```bash
docker-compose up -d --build
```

Access the client interface at `http://localhost:3000` and API docs at `http://localhost:8000/docs`.

---

## 🔍 Synthetic Demo Scenario

The repository includes a pre-seeded suspicious transaction designed to showcase the complete autonomous investigation workflow:
* **Transaction ID**: `TXN-92817`
* **Amount**: ₹85,000 (breaches Card-Not-Present limitations)
* **Customer**: `CUST-7821` (historical average of ₹1,800)
* **Device**: `Previously unseen device` (fingerprint `df_demo_unseen_99`)
* **Failed Attempts**: 4 blocked transactions within 6 minutes
* **Location**: Geographic country mismatch (IN billing vs US card)
* **Linked Suspicious Entities**: 3 suspect accounts connected via device fingerprint overlaps

When ingested, the system outputs:
* **Risk Score**: ~87/100
* **Risk Classification**: **High Risk**
* **Recommended Action**: **HOLD FOR HUMAN REVIEW** (routing status shifted to **Escalated**)

---

## ⚠️ Disclaimer & Limitations
* **Prototype Status**: This is a proof-of-concept prototype built for the Razorpay AI Builder Buildathon 2026.
* **Synthetic Data Only**: All calculations, customer behaviors, device fingerprints, and payment relationships utilize synthetically generated parameters.
* **Production Readiness**: Do not use this configuration or codebase for real-world production fraud detection, credit screening, or live payment gateway compliance without proper auditing, hardened encryption, and model tuning.

---

## ⚖️ License
Distributed under the MIT License. See `LICENSE` for details.
