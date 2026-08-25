# 📑 RazorGuard AI — Technical Decisions Log

This document outlines the core architectural choices, agent structures, and security considerations implemented in the RazorGuard AI Payment Risk Investigation & Decision Support console.

---

## 1. Deterministic Scoring vs. LLM Decisions

### Architectural choice
RazorGuard AI uses a **mathematically deterministic composite scoring engine** rather than allowing an LLM to dynamically predict risk scores.

### Rationale
- **Traceability & Compliance**: Financial audits require absolute reproducibility. A transaction evaluated twice under the same inputs must yield the exact same numeric score. LLM responses are subject to temperature drift and non-determinism.
- **Latency & Cost**: Real-time payment processing requires sub-second decisions. Aggregating heuristics, ML inferences, and graph walks takes < 50ms. Triggering a synchronous LLM call for risk score calculation would introduce 1.5 - 3s latency.
- **Role separation**: The deterministic core calculates the numeric score; the LLM is only utilized as a synthesizer to compile a grounded, natural-language explanation briefing for risk analysts.

---

## 2. AI Agent Architecture

RazorGuard AI implements a specialized, multi-agent pipeline where each agent is assigned a single, clear responsibility.

| Agent Name | Inputs Evaluated | Responsibility | Outputs Produced | Affects Scoring? | Failure Fallback Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ML Classifier** | Amount, location drift, velocity, device score | Predicts baseline risk probability | Score (0-100) & risk class | Yes (35% composite weight) | Defaults to 0.0 risk, logs warning |
| **Transaction Risk Agent** | Amount, card-present, billing country, card country | Static heuristic rules validation | Score (0-100) & rule violations list | Yes (Heuristic component: 10% effective weight; averaged with behavioral under the 20% Rules weight) | Defaults to 0.0 risk, logs warning |
| **Behavioral Risk Agent** | Historical transaction log, current hourly counts | Velocity check and ticket size baseline drifts | Score (0-100) & baseline deviation logs | Yes (Behavior component: 10% effective weight; averaged with rules under the 20% Rules weight) | Defaults to 0.0 risk, logs warning |
| **Fraud Investigation Agent** | Graph walk database edges, relationship nodes | Identifies hardware/device sharing overlaps | Score (0-100) & shared entity paths | Yes (30% composite weight) | Defaults to 0.0 risk, logs warning |
| **Policy Agent** | Ingestion context, compliance manuals vector store | Hybrid RAG retrieval of policy clauses | Score (0-100) & manual segment text | Yes (15% composite weight) | Defaults to 0.0 risk, logs warning |
| **Decision Agent** | Aggregate scores from individual risk agents | Computes composite score using weighted formula | Final score (0-100) & classification label | Yes (Evaluates composite formula) | Capped at 100.0, escalates transaction |
| **Action Agent** | Final score & classification label | Sets operational status (Approved / Escalated) | Transaction status transition | No (Operational Action Only) | Defaults to `Escalated` for safety |
| **Explanation Agent** | Agent evidence logs, prompt template, RAG documents | Compiles structured explanation briefing | Markdown explanation text | No (Explanatory Only) | Generates structured text fallback |

---

## 3. Why Knowledge Graph (NetworkX)

- **The Problem**: Compromised devices and card testing rings rotate user identities but reuse device fingerprints or local networks (IPs).
- **The Solution**: Maps relationships as graph edges (`User -[USED_DEVICE]-> Device`).
- **Algorithm**: Explores relational overlaps (User -> Transaction -> Device/IP/Card -> Transaction -> User) to count distinct accounts linked to the same device, IP, or card. Each shared entity adds 33.3% risk (capped at 100%).
- **Implementation**: Written using Python's `NetworkX` library in-memory, avoiding the overhead of running a dedicated graph database service.

---

## 4. Why RAG (PostgreSQL + pgvector)

- **The Problem**: Compliance policies (SCA, High Ticket CNP thresholds) update frequently. Hardcoding policies inside LLM system prompts bloats the context window and requires redeploying backend containers on policy changes.
- **The Solution**: Policies are indexed into chunks using `sentence-transformers` and stored in a vector database.
- **Hybrid Retrieval**: Combines pgvector cosine similarity search with sparse keyword search using Reciprocal Rank Fusion (RRF), ensuring highly relevant clauses are retrieved and cited correctly in explanation logs.

---

## 5. Human-in-the-Loop Override Architecture

- **Analyst Override**: High-risk transactions are suspended (`Escalated`). Analysts investigate the console and submit an override (`Approve` or `Block`) alongside justification notes.
- **Audit Persistence**: Every override logs:
  - Analyst User ID and email
  - Original AI recommended action (e.g. `Escalated`)
  - Final override action (e.g. `Approved`)
  - Justification notes
  - Timestamp
- **Audit View**: The frontend displays these overrides inside an Override Audit Log timeline panel.

---

## 6. PostgreSQL/pgvector and SQLite Fallback Strategy

- **Production Storage**: PostgreSQL with the `pgvector` extension is used to store both structured transaction data and high-dimensional semantic policy embeddings.
- **Local SQLite Fallback**: For unit tests and offline setups, the backend detects if the database is SQLite and automatically swaps vector cosine calculations with a lightweight, CPU-based cosine similarity function on local Python list parameters, ensuring tests execute instantly without external service dependencies.

---

## 7. Security & Key Management

- **Zero Hardcoded Secrets**: Removed insecure fallback secret key strings.
- **Startup Protection**: The backend validator checks `ENVIRONMENT`. If `production` is set, startup aborts unless `SECRET_KEY` is defined in env. In `development` mode, it dynamically generates a temporary random key (`secrets.token_hex(32)`) at startup.
- **Financial Data Safety**: All names, cards, billing countries, and merchant transactions are completely synthetic and marked as such inside layouts.
