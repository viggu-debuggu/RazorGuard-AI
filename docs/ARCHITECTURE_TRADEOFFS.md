# RazorGuard AI — Architecture Tradeoffs

## Deterministic Scoring vs LLM-Only Risk Scoring

This document benchmarks the current **Deterministic Score Engine** against a
hypothetical **LLM-only scoring** approach where a language model directly assigns
a risk score from raw transaction fields.

---

## Cost Per Transaction

| Approach | Model | Tokens In | Tokens Out | Cost/1K tokens | **Est. Cost / Transaction** |
|---|---|---|---|---|---|
| LLM-only scoring | GPT-4o-mini | ~250 | ~50 | $0.15 / $0.60 (in/out) | **~$0.000068** |
| LLM-only scoring | GPT-4o | ~250 | ~50 | $2.50 / $10.00 (in/out) | **~$0.001125** |
| LLM-only scoring | Gemini 1.5 Flash | ~250 | ~50 | $0.075 / $0.30 (in/out) | **~$0.000034** |
| **RazorGuard (current)** | Nearest Centroid + rules + graph | — | — | $0 | **~$0.000000** |
| RazorGuard explanation | Gemini 1.5 Flash (explanation only) | ~800 | ~300 | $0.075 / $0.30 (in/out) | **~$0.000150** |

> **Pricing assumptions** (labelled as estimates, sourced from public pricing pages
> as of mid-2026): GPT-4o-mini at $0.15/$0.60 per 1M tokens (in/out);
> GPT-4o at $2.50/$10.00; Gemini 1.5 Flash at $0.075/$0.30.
> Token counts are estimates for a typical RazorGuard transaction payload.
> Actual costs vary with payload size and provider promotions.

### At Scale

| Volume | LLM-only (GPT-4o-mini) | RazorGuard (deterministic core only) | RazorGuard (with Gemini explanation) |
|---|---|---|---|
| 10K txns/day | ~$0.68 / day | **$0.00 / day** | ~$1.50 / day |
| 1M txns/day | ~$68 / day | **$0.00 / day** | ~$150 / day |
| 1M txns/day (GPT-4o) | ~$1,125 / day | **$0.00 / day** | ~$150 / day |

The deterministic scoring core has **zero marginal API cost** at any volume.
LLM explanation (the natural-language briefing in the investigation panel) is
only triggered once per transaction and only when a human analyst opens the
investigation — not inline on every payment event.

---

## Latency Per Transaction

| Approach | Median (p50) | p95 | Notes |
|---|---|---|---|
| LLM-only scoring (GPT-4o-mini) | ~1,200 ms | ~3,500 ms | Network + model inference |
| LLM-only scoring (GPT-4o) | ~2,000 ms | ~6,000 ms | Slower model |
| LLM-only scoring (Gemini Flash) | ~800 ms | ~2,500 ms | Faster but still network-bound |
| **RazorGuard deterministic core** | **0.005 ms** | **0.007 ms** | Measured (see EVALUATION.md) |
| RazorGuard full pipeline (DB + graph) | ~80 ms | ~250 ms | Includes SQLite/Postgres I/O |
| RazorGuard + async LLM explanation | +500–2,000 ms | — | Dispatched async, does not block ingestion |

> Latency figures for LLM approaches are estimates based on public benchmark data
> and typical network conditions. Actual latency depends on region, provider load,
> and token count.

The ingestion endpoint (`POST /api/v1/transactions/`) returns `202 Accepted`
immediately after writing the transaction record. The multi-agent investigation
runs as a **background task** (`BackgroundTasks.add_task`), so end-user payment
confirmation is never blocked by LLM inference.

---

## Why Nearest Centroid Instead of Isolation Forest or XGBoost?

Three reasons drove this choice, in order of priority:

### 1. Interpretability
Nearest Centroid produces a distance vector — you can print the Safe, Suspicious,
and High Risk centroids, look at the coordinates, and immediately understand why
a transaction was classified the way it was. The centroid coordinates are stored
as a 200-byte JSON file (`ml/models/transaction_classifier.json`) readable by any
analyst without a data science background.

XGBoost produces an ensemble of hundreds of decision trees. Feature importance
is computable, but explaining *why this specific transaction got this specific score*
to a compliance auditor requires additional tooling (SHAP values, etc.) and
significantly increases cognitive overhead. In payment risk — where every escalation
decision must be defensible to regulators — interpretability is not optional.

Isolation Forest is even harder to interpret: its anomaly score is based on the
average path length through randomly constructed trees, with no intuitive mapping
back to business logic.

### 2. Cold-Start Performance
Nearest Centroid needs as few as 3 labelled samples (one per class) to produce a
valid model. The training pipeline (`ml/train.py`) runs in under 10 milliseconds
on the full synthetic dataset. This means the model can be retrained or recalibrated
instantly without GPU infrastructure, making it ideal for demo, CI, and on-call
incident response.

XGBoost and Isolation Forest require minimum dataset sizes (hundreds to thousands
of samples) to produce reliable scores — a meaningful barrier when launching a
new fraud detection product with limited historical data.

### 3. Zero Runtime Dependencies
The inference path (`ml/predict.py`) uses only Python standard library (`math`,
`json`, `os`). No scikit-learn, no numpy, no pickle files that can break across
Python versions. This eliminates an entire category of deployment failures and
CVE exposure. The model survives `pip install` churn unchanged.

---

## Summary

| Criterion | LLM-Only | Isolation Forest / XGBoost | **Nearest Centroid (current)** |
|---|---|---|---|
| Explainability | Low (black box) | Medium (SHAP needed) | **High (centroid distances)** |
| Latency | 800–6,000 ms | 1–5 ms | **0.005 ms** |
| Cost at 1M txns/day | $34–$1,125/day | $0 | **$0** |
| Cold-start (min samples) | 0 (prompt only) | 500+ | **3** |
| Runtime deps | LLM API | scikit-learn, numpy | **stdlib only** |
| Determinism | No | Yes | **Yes** |
| Auditability | Low | Medium | **High** |
