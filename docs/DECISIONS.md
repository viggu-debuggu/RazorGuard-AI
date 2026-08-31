# 📑 RazorGuard AI — Architectural Decisions & Trade-offs

This document outlines the top 5 technical trade-offs made during the design of the RazorGuard AI platform, along with the top 3 current system weaknesses and actionable plans to resolve them.

---

## 1. Top 5 Technical Decisions & Trade-offs

### I. Deterministic Scoring vs. LLM Decisions
- **Decision**: RazorGuard AI utilizes a mathematically deterministic, weighted formula to aggregate subscores across ML, static rules, behavioral metrics, and compliance RAG checks into a single composite score. The LLM is strictly used asynchronously to synthesize explanation briefings, rather than predicting risk inline.
- **Why**: 
  - **Traceability & Compliance**: Regulators require absolute auditability. A transaction evaluated twice with the same inputs must yield the exact same score. LLMs suffer from non-deterministic temperature drifts.
  - **Latency & Cost**: Aggregating heuristics, ML inferences, and graph walks runs in sub-milliseconds ($<$ 1ms). Making synchronous LLM calls on the payment pathway adds 1.5s - 3s latency and significant API costs.

### II. Nearest Centroid Classifier vs. Other Classifiers (XGBoost, Isolation Forest)
- **Decision**: Chosen the Nearest Centroid model for transaction classification.
- **Why**: 
  - **Explainability**: The model is based on raw Euclidean distance vectors from class centroids (Safe, Suspicious, High Risk), which is directly inspectable and easy to justify to compliance auditors.
  - **Cold-Start Performance**: Requires as few as 3 labeled samples to train, running in under 10ms.
  - **Zero Runtime Dependencies**: The inference script uses only the Python standard library. No `scikit-learn`, `numpy`, or `pickle` file dependencies, eliminating cross-environment deployment failures and CVE vulnerabilities.

### III. PostgreSQL + pgvector vs. Dedicated Vector Databases (Pinecone, Milvus)
- **Decision**: Stored high-dimensional policy embeddings using PostgreSQL with the `pgvector` extension.
- **Why**:
  - **Transactional Consistency (ACID)**: Storing document text chunks, metadata, and transaction tables within the same database prevents data sync drift and ensures transactions roll back correctly together.
  - **Reduced Infrastructure Overhead**: Avoids deploying, managing, and paying for a separate vector database cluster.
  - **Unified Queries**: Simplifies retrieval logic by allowing unified SQL queries blending structured metadata filtering with dense vector similarity joins.

### IV. Local SQLite Fallback Strategy
- **Decision**: Created an automatic database fallback. If PostgreSQL is unreachable at boot time, settings switch to a local SQLite database (`sqlite:///./razorguard.db`), and pgvector operators swap to pure Python list-based cosine calculations.
- **Why**: 
  - **Developer Velocity & CI Stability**: Allows the entire codebase and test suite (including hybrid RAG checks) to execute instantly in offline developer sandboxes and GitHub Actions pipelines without spin-up delays or external cloud database dependencies.

### V. In-Memory NetworkX Graph vs. Dedicated Graph DB (Neo4j)
- **Decision**: Modeled entity relationships as nodes/edges using Python's `NetworkX` library in-memory rather than running a Neo4j server.
- **Why**: 
  - **Ingestion Latency**: Querying and updating in-memory graphs avoids connection handshakes and query serialization overhead, completing multi-hop lookups in under 1ms.
  - **Zero Deploy Footprint**: Simplifies microservice scaling by avoiding the operations and cost of a dedicated multi-node graph database cluster.

---

## 2. Top 3 System Weaknesses & Fix Plans

### Weakness 1: In-Memory Graph Memory Footprint (NetworkX scaling limits)
Currently, `network_builder.py` rebuilds the NetworkX graph in memory by fetching all relational edges from the database at the start of each transaction assessment. As transaction volumes scale into millions of records, loading the global edge set will lead to memory exhaustion, long garbage collection pauses, and degraded API latency.
* **Fix Plan**: Decouple the graph query logic by moving relation traversals directly to the database layer. We will transition to using PostgreSQL recursive Common Table Expressions (CTEs) or introduce a dedicated graph index (like Neo4j) configured to query only the immediate ego-network of a specific User node up to 4 hops, avoiding loading the entire payment relationship network into memory.

### Weakness 2: Local CPU Embedding Generation Latency
The `PolicyRAGAgent` generates embeddings synchronously on the local CPU using `sentence-transformers` during manual document imports and policy searches. High-dimensional vector encoding on a CPU blocks FastAPI's event loop, causing request queuing and latency spikes under concurrent search volumes.
* **Fix Plan**: Offload embedding computation to a background worker pool or a dedicated microservice. We will delegate vector generation to an asynchronous Celery task queue targeting a GPU-powered instance or switch to a high-speed, managed cloud embedding API (like Google Vertex AI) backed by a Redis cache to prevent redundant embedding calculations for identical text segments.

### Weakness 3: Single-Node In-Process Background Task Execution
 फास्टAPI's built-in `BackgroundTasks` executes the agent orchestrator pipeline inline within the same worker process. If a container crashes, restarts, or runs out of memory mid-execution, active risk investigations are lost without a trace, leaving transactions stuck in `Pending` state.
* **Fix Plan**: Decouple risk investigation from the API gateway using a distributed message broker and task workers. We will publish new transaction events to an AMQP broker (like RabbitMQ or Apache Kafka) and consume them using independent worker nodes running Celery. This will implement durable task storage, automated retries with exponential backoffs, dead-letter queues, and horizontal scalability.
