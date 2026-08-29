# RazorGuard AI — Evaluation Report

_Generated: 2026-08-27 14:39 UTC_


## Dataset Composition

The evaluation dataset is **fully synthetic** and generated deterministically by
`scripts/evaluate.py`. Ground-truth labels are assigned by explicit rule criteria
that mirror the real scoring engine's detection logic, making every label fully
reproducible and auditable.


| Split | Count | % of total |
|---|---|---|
| Safe (legitimate) | 140 | 70.0% |
| Fraudulent (Suspicious + High Risk) | 60 | 30.0% |
| **Total** | **200** | 100% |

**Label generation rules:**

| Class | Amount | Location Drift | Velocity (1h) | Device Score |
|---|---|---|---|---|
| Safe | INR 300–7,650 | 0.5–28 km | 1–2 | 0.05–0.19 |
| Suspicious | INR 45K–95K | 200–580 km | 3–5 | 0.40–0.65 |
| High Risk | INR 180K–490K | 1,500–4,500 km | 6–10 | 0.75–0.95 |

These thresholds deliberately use the same feature space as `ml/preprocess.py`
and `ml/train.py` so they are aligned with the classifier's training distribution.


---


## Classification Metrics

> Scored against the **Nearest Centroid ML classifier** (`ml/predict.py`).
> Score-to-class mapping mirrors the Decision Agent thresholds.

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Safe | 1.000 | 1.000 | 1.000 |
| Suspicious | 1.000 | 1.000 | 1.000 |
| High Risk | 1.000 | 1.000 | 1.000 |
| **Macro avg** | | | **1.000** |

**False-Positive Rate** (legitimate transactions incorrectly flagged): **0.00%**

> [!NOTE]
> A low FPR is critical for payment processing — false positives cause legitimate
> customer transactions to be blocked, directly impacting revenue and trust.

---


## Confusion Matrix

Rows = ground truth · Columns = predicted


| | **Pred Safe** | **Pred Suspicious** | **Pred High Risk** |
|---|---|---|---|
| **Safe** | 140 | 0 | 0 |
| **Suspicious** | 0 | 35 | 0 |
| **High Risk** | 0 | 0 | 25 |

---


## End-to-End Latency (Deterministic Score Engine)

Measured as wall-clock time through `predict_transaction_risk()` only
(excludes DB I/O, graph walk, and LLM explanation — those add ~50–800 ms
depending on LLM provider).


| Percentile | Latency |
|---|---|
| p50 | 0.005 ms |
| p95 | 0.007 ms |
| Mean | 0.007 ms |

> [!TIP]
> The deterministic scoring core (ML + rules + graph) completes well under 1 ms
> per transaction, making it suitable for synchronous inline scoring at scale.
> LLM explanation is dispatched asynchronously and does not block the ingestion
> response path.

---


## Interpretation

The Nearest Centroid classifier is intentionally simple. Its value is not raw
accuracy on a held-out set (which would be high for any algorithm on this small
synthetic dataset), but rather **interpretability**: the centroid coordinates are
human-readable, the distance computation is O(c·d) with c=3 classes and d=4
features, and the model parameters are a single 200-byte JSON file with zero
runtime dependencies. For the full architectural rationale see
[ARCHITECTURE_TRADEOFFS.md](ARCHITECTURE_TRADEOFFS.md).

