# 🛡️ RazorGuard AI — Payment Risk Investigation & Decision Support

RazorGuard AI is an internal operations console designed for payment risk investigation, compliance verification, and human-in-the-loop analyst review. The system analyzes payment transaction streams to detect potential credit card fraud, spend velocity spikes, card-not-present compliance breaches, and relationship overlaps.

---

## 1. Problem
High-throughput payment gateways face two major problems in risk analysis:
- **Heuristic Rule Fatigue vs. LLM Latency:** Heuristics check simple static conditions but miss complex network relations. Conversely, running an LLM directly to predict numeric risk scores is too slow, expensive, and non-deterministic.
- **Explainability Gaps:** Traditional machine learning models (such as Nearest Centroid anomaly classifiers) output numeric risk probabilities but do not explain *why* a transaction was flagged or which compliance rules were violated.

## 2. Solution
RazorGuard AI resolves these limitations by separating the scoring logic from explanation generation:
- **Deterministic scoring:** Overall numeric risk values are calculated using fixed math weights applied to ML, rules, graph, and policy models.
- **Multi-Agent explanation:** Formulates evidence logs from specialized agents (Heuristics, Behavioral, Graph, RAG Compliance) and uses a retrieval-augmented LLM to synthesize a grounded, natural-language explanation briefing for risk operations analysts.

## 3. Key Design Decisions
- **Deterministic Core Scoring:** Numeric scores are never determined by the LLM. This guarantees consistency, traceability, and reproducibility.
- **pgvector dense-sparse Hybrid RAG:** Compliance manuals are vectorized using `sentence-transformers` and queried with hybrid Reciprocal Rank Fusion (RRF), ensuring explanation briefings cite real policy clauses.
- **Shared Hardware Relationship Walking:** Walks a NetworkX transaction graph to detect accounts sharing hardware (device fingerprints) or networks (IPs).

---

## 4. Architecture

```
Ingested Payment Event
      │
      ▼
┌────────────────────────────────────────────────────────┐
│               Deterministic Score Engine               │
│                                                        │
│  ┌────────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ Nearest        │ │ Heuristic &  │ │ NetworkX     │  │
│  │ Centroid ML    │ │ Vel. Rules   │ │ Graph Walk   │  │
│  │ (Amount, Drift)│ │ (History)    │ │ (Devices)    │  │
│  └───────┬────────┘ └──────┬───────┘ └──────┬───────┘  │
│          │                 │                │          │
│          ▼                 ▼                ▼          │
│        [35%]             [20%]            [30%]        │
│          │                 │                │          │
│          └─────────────────┼────────────────┘          │
│                            │                           │
│                            ▼                           │
│                 Weighted Score Aggregator              │
│                            │                           │
│                            ▼                           │
│         [15%] ◄─── Compliance Policy RAG               │
│          │                                             │
│          ▼                                             │
│    Composite Score & Classification (Safe/Susp/High)   │
└────────────────────────────┬───────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────┐
│             Multi-Agent Explanation Engine             │
│                                                        │
│   ┌────────────────────────────────────────────────┐   │
│   │ Agent Orchestrator                             │   │
│   │ - Collects evidence logs from agents           │   │
│   │ - Grounded LLM synthesizes markdown briefing    │   │
│   └────────────────────────┬───────────────────────┘   │
└────────────────────────────┼───────────────────────────┘
                             ▼
                 Risk Operations Dashboard
                 (Human Analyst Override)
```

---

## 5. Risk Scoring
The composite risk score is calculated deterministically using the following formula:
$$\text{Composite Score} = (0.35 \times \text{ML Anomaly Score}) + (0.20 \times \text{Rules/Behavior Score}) + (0.30 \times \text{Graph Score}) + (0.15 \times \text{Policy Score})$$

Where:
- **ML Anomaly Score (35%)**: Nearest Centroid distance calculation based on normalized transaction amount, geographical location drift, hourly velocity, and device footprint history.
- **Rules & Behavior Score (20%)**: Average of transaction heuristic violations (e.g., large ticket amount, geographic country mismatch) and behavioral deviations (e.g., payment amount > 3x average historical ticket size).
- **Graph Overlap Score (30%)**: Number of distinct accounts sharing the current device or IP address (33.3% per overlapping account, capped at 100%).
- **Policy Compliance Score (15%)**: Hard threshold enforcement. Evaluates to 100% if the payment triggers compliance verification rules (like Card-Not-Present limits).

---

## 6. Multi-Agent Investigation
The system triggers six specialized agents during ingestion:
1. **Transaction Risk Agent:** Evaluates immediate properties (amount, card-present status, billing country vs card country).
2. **Behavioral Risk Agent:** Reviews velocity counts and historical average transaction size.
3. **Fraud Investigation Agent:** Builds and traverses the network graph to flag shared devices and IPs.
4. **Policy Agent:** Searches indexed compliance documentation via hybrid RAG.
5. **Decision Agent:** Computes the overall composite score and assigns classification.
6. **Action Agent:** Transitions transaction status (Approved, Escalated) based on thresholds.

---

## 7. RAG (Retrieval-Augmented Generation)
Compliance document policies are chunked using sliding windows and stored in PostgreSQL using the `pgvector` extension.
- **Hybrid Retrieval:** Blends dense vector search (using `all-MiniLM-L6-v2` embeddings) with sparse keyword queries using Reciprocal Rank Fusion (RRF).
- **Grounding Citations:** Each retrieved chunk is referenced in the explanation briefing with its source file and index, preventing the LLM from inventing policies.

---

## 8. Knowledge Graph
Built on top of SQLAlchemy model edges and NetworkX, the relationship graph maps nodes for `User`, `Transaction`, `Device`, `IP`, and `Merchant`.
- **Topological Walks:** Explores up to 3 hops from the initiating user to find distinct accounts linked to the same device fingerprint or IP.
- **Visual Evidence:** Visualized in the analyst UI via SVG paths showing the exact links.

---

## 9. Human Review
Transactions with high composite scores are enqueued as **Escalated** (suspended). Analysts review the evidence console, explore the relationship graph, and submit an override decision (`Approve` or `Block`) with justification notes that are persisted for auditing.

---

## 10. Demo Scenario (TXN-92817)
To run the complete workflow, seed the database. It contains `TXN-92817` representing a credit card takeover scenario:
- **Customer:** `CUST-7821` (historical average ticket size is ₹1,800).
- **Transaction:** ₹85,000 Card-Not-Present payment.
- **Risk Indicators:** Unseen device, IN billing vs US card geographic mismatch, 4 blocked attempts in under 6 minutes, and device fingerprint shared with 3 suspect accounts.
- **Calculated Composite Score:** ~87% (High Risk - Escalated status).

---

## 11. Tech Stack
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL + pgvector, NetworkX.
- **Frontend:** Next.js (App Router), Lucide Icons, Recharts.
- **Testing:** Pytest, SQLite fallback for unit testing.

---

## 12. Why these technologies?
- **FastAPI:** High performance, asynchronous request concurrency, and automated OpenAPI documentation.
- **PostgreSQL + pgvector:** Enables storing structured relational payment data and dense semantic policy embeddings in a single database engine.
- **NetworkX:** Offers lightweight, highly optimized, in-memory graph operations for fast topological path walking.
- **Deterministic Scoring:** Ensures auditability. We can explain exactly how the risk score was computed.
- **RAG & Multi-Agent:** Grounding the LLM using real policy segments and graph walks prevents hallucinations.

---

## 13. Engineering Trade-offs
- **Deterministic Core vs LLM Score:** We chose deterministic composite scoring over direct LLM score prediction. This guarantees that numeric results are reproducible and not subject to LLM non-determinism.
- **Local SQLite Fallback:** We included a CPU-bound in-memory cosine similarity fallback in tests. This enables running unit test suites locally without requiring a live PostgreSQL + pgvector instance.
- **RAG for Policy Grounding:** Storing manuals in RAG instead of hardcoding prompt instructions prevents context window bloat and allows updating manuals without code changes.

---

## 14. Installation & Setup (Local)

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
# Run migrations
alembic upgrade head
```

### Step 3: Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
```

---

## 15. Docker Deployment (Recommended)

To spin up the entire cluster (PostgreSQL + pgvector, Backend, Frontend):
```bash
docker compose up -d --build
```

Access the client interface at `http://localhost:3000` and API docs at `http://localhost:8000/docs`.

---

## 16. Testing

Run backend tests:
```bash
cd backend
pytest
```

---

## 17. Limitations
- **Prototype Status:** Built as a proof-of-concept. All data parameters and behaviors are synthetic.
- **No Real Gateway Hooks:** Designed for risk analysis, does not connect to live card networks.

---

## 18. Future Work
- **Advanced Graph Features:** Integrating real-time message queues (like Kafka) for streaming transactions.
- **Active Model Tuning:** Transitioning Nearest Centroid classifier to online learning classifiers.
