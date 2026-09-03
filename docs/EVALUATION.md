# RazorGuard AI — Evaluation Report

_Generated: 2026-09-03 13:08 UTC_


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

**Label generation rules (with controlled boundary overlap):**

| Class | Amount | Location Drift | Velocity (1h) | Device Score | Boundary Overlap Profile |
|---|---|---|---|---|---|
| Safe | INR 300–7,650 (edge: 32K–40K) | 0.5–28 km (edge: 120–210 km) | 1–2 (edge: 2–3) | 0.05–0.19 (edge: 0.32–0.42) | ~2.1% domestic travel/higher ticket overlap |
| Suspicious | INR 45K–95K (edge: 18K–26K / 165K) | 200–580 km (edge: 45–85 km / 1,450 km) | 3–5 (edge: 2 / 6) | 0.40–0.65 (edge: 0.22–0.26 / 0.78) | Borderline overlap with both Safe and High Risk |
| High Risk | INR 180K–490K (edge: 130K) | 1,500–4,500 km (edge: 850 km) | 6–10 (edge: 5) | 0.75–0.95 (edge: 0.68) | ~4% lower-drift edge cases resembling Suspicious |

Realistic boundary overlap is intentionally introduced across adjacent classes
so the classifier must evaluate multi-dimensional trade-offs rather than trivially separating clusters.


---


## Classification Metrics

> Scored against the **Nearest Centroid ML classifier** (`ml/predict.py`).
> Score-to-class mapping mirrors the Decision Agent thresholds.

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Safe | 0.986 | 0.979 | 0.982 |
| Suspicious | 0.889 | 0.914 | 0.901 |
| High Risk | 0.960 | 0.960 | 0.960 |
| **Macro avg** | | | **0.948** |

**False-Positive Rate** (legitimate transactions incorrectly flagged): **2.14%**

> [!NOTE]
> A low FPR is critical for payment processing — false positives cause legitimate
> customer transactions to be blocked, directly impacting revenue and trust.

---


## Confusion Matrix

Rows = ground truth · Columns = predicted


| | **Pred Safe** | **Pred Suspicious** | **Pred High Risk** |
|---|---|---|---|
| **Safe** | 137 | 3 | 0 |
| **Suspicious** | 2 | 32 | 1 |
| **High Risk** | 0 | 1 | 24 |

---


## End-to-End Latency (Deterministic Score Engine)

Measured as wall-clock time through `predict_transaction_risk()` only
(excludes DB I/O, graph walk, and LLM explanation — those add ~50–800 ms
depending on LLM provider).


| Percentile | Latency |
|---|---|
| p50 | 0.006 ms |
| p95 | 0.014 ms |
| Mean | 0.031 ms |

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

