# 🛡️ Risk Scoring Derivation & Determinism Guarantees

This document outlines the design, formula, and architectural constraints of the RazorGuard AI scoring engine.

---

## 1. The Risk Scoring Formula

The overall composite risk score is calculated using a mathematically deterministic formula:

$$\text{Composite Score} = (0.35 \times \text{ML Anomaly Score}) + (0.20 \times \text{Rules \& Behavior Score}) + (0.30 \times \text{Graph Overlap Score}) + (0.15 \times \text{Policy Score})$$

### Components:
1. **ML Anomaly Score (35%)**: Nearest Centroid distance calculation based on normalized transaction amount, geographical location drift, hourly velocity (including current transaction), and device footprint history.
2. **Rules & Behavior Score (20%)**: A unified block representing standard heuristic violations and behavioral deviations. Formulated as:
   $$\text{Rules \& Behavior Score} = \frac{\text{Heuristic Rules Score} + \text{Behavioral Velocity Score}}{2.0}$$
3. **Graph Overlap Score (30%)**: Calculated via NetworkX walks checking hardware/device reuse. Each shared account adds 33.3% risk (capped at 100%).
4. **Policy Compliance Score (15%)**: Hard threshold compliance triggers (e.g. Card-Not-Present limitations). Set to 100% if high ticket limits are breached without secondary compliance checks.

---

## 2. Why Heuristics and Behavior are Averaged

Instead of separating static heuristic rules and behavioral history into two separate 20% components, RazorGuard AI averages them into a single 20% block:
- **Avoiding Double-Penalization**: High-velocity order rushes often trigger both heuristic constraints (e.g. ticket amount deviation) and behavioral limits (e.g. hourly counts exceeding baseline). Treating them separately would double-penalize a single transaction flow, raising false positive rates.
- **Balanced Signal Aggregation**: Averaging them ensures that structural fraud signals—namely relational hardware networks (30%) and regulatory/compliance triggers (15%)—remain heavily weighted, preventing simple transaction profile anomalies from overshadowing complex fraud pattern detections.

---

## 3. The Determinism Guarantee

To ensure compliance with audits, standard financial guidelines, and human-in-the-loop consistency:
- **Mathematical Determinism**: Numeric scores and risk classifications (`Safe`, `Suspicious`, `High Risk`) are computed solely by deterministic Python code running the consensus formula.
- **Exclusion of LLM Influence**: The Large Language Model (LLM) is **strictly** restricted to the multi-agent explanation engine. The LLM consumes the structured evidence and agent outcomes to synthesize a readable compliance briefing. It has **no** access or authority to alter the numeric risk score or transition classifications.
- **Traceable Invariance**: Two independent analysts reviewing the same transaction under the same database state will see the exact same risk scores and classification recommendations.

---

## 4. LLM Boundaries & Responsibilities

### What the LLM IS Responsible For:
- **Structured Synthesis**: Aggregating the outputs of Heuristics, Behavioral, Graph, and Policy agents into a readable markdown briefing.
- **Grounding**: Translating dry, structured JSON evidence into a logical summary for analysts.
- **Policy Citations**: Presenting policy references (such as `policies/rbi_cnp.pdf#chunk_5`) accurately within the natural-language explanation.

### What the LLM IS NOT Responsible For:
- **Composite Scoring**: The LLM does not calculate, modify, or output the composite score.
- **Operational Status**: Status transitions (Approved vs. Escalated) are determined by threshold boundary rules, not LLM reasoning.

---

## 5. Known Limitations

- **Card-Node Collision by Country**: Since card transaction routing networks and country metrics are mapped, a lack of highly specific device identifiers could result in card-node collisions when users transacting from the same country share high-level gateway paths.
- **Small Synthetic Training Set**: The Nearest Centroid Classifier is trained on a small, mock synthetic dataset. While this establishes clear safe, suspicious, and high-risk centroids for demo and testing, production deployment requires retraining on a large corpus of real payment gateway event telemetry.
