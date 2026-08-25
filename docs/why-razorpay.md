# RazorGuard AI — Why This Complements Razorpay's Stack

**For reviewers and judges evaluating this project's relevance to Razorpay.**

---

## 1. The Existing Layer: Thirdwatch

Razorpay's **Thirdwatch** product is a merchant-facing fraud intelligence system designed to address **order-level ecommerce fraud** — specifically:

- **Return-to-Origin (RTO) risk**: predicting which orders are likely to be refused at delivery
- **Cash-on-Delivery (COD) fraud**: scoring buyer intent to pay at the door
- **Order-level risk at checkout**: real-time risk assessment before an order is placed

Thirdwatch operates at the **merchant-to-buyer relationship layer** — it answers "should this merchant fulfill this order for this buyer?"

This is well-documented public product functionality. No internal Razorpay architecture is claimed here beyond what is publicly described.

---

## 2. The Gap RazorGuard Fills

**RazorGuard AI operates at a different layer entirely.**

When a payment transaction is processed through a gateway, it passes through automated risk scoring. Transactions that trigger risk thresholds are **escalated** — suspended pending human review. This is where RazorGuard begins.

RazorGuard is the tool a **risk operations analyst** opens *after escalation*, to:

1. Understand *why* a transaction was flagged (not just a numeric score)
2. Investigate the customer's network relationships (shared devices, shared IPs)
3. Check which compliance policy was potentially violated
4. Submit an **auditable override decision** (Approve / Block) with written justification
5. Generate a decision record suitable for RBI/PCI-DSS audit review

**This is post-flag investigation at the payment-gateway/transaction level**, not order-level ecommerce fraud detection. The two tools address different layers of the same risk stack.

---

## 3. Where RazorGuard Sits in the Risk Stack

```
Buyer places order
        │
        ▼
Merchant / Thirdwatch layer  ←── Thirdwatch: RTO, COD, order-level risk
        │
        ▼
Payment gateway processes transaction
        │
        ▼
Auto-scoring engine flags transaction (Escalated)
        │
        ▼
Risk operations analyst console  ←── RazorGuard AI: post-escalation investigation
        │
        ▼
Override decision submitted (Approve / Block) + audit trail
```

---

## 4. Feature-to-Need Mapping

| RazorGuard Feature | Risk-Ops Need It Addresses |
|---|---|
| **Multi-agent explanation briefing** | Analyst understands *why* a transaction scored high — not just a number. Reduces mis-overrides. |
| **Human override with justification notes** | Produces an auditable decision trail. Required for RBI/PCI-DSS compliance review and chargeback dispute evidence. |
| **Deterministic composite scoring** | Reproducible risk computation. Two analysts reviewing the same transaction at different times see the same score — critical for audit consistency. |
| **Knowledge graph (device/IP sharing)** | Detects card-testing rings that rotate customer identities but reuse device fingerprints or network sources. |
| **Compliance RAG (hybrid retrieval)** | Grounds override decisions in real indexed policy clauses — not analyst memory or LLM hallucination. |
| **Force-directed relationship map** | Gives a non-technical reviewer (compliance officer, regulator) an interpretable view of why two accounts are considered related. |

---

## 5. Measurable Investigation Goals

A primary design goal of RazorGuard is **reducing analyst time-per-case** — the average minutes an analyst spends from opening an escalated transaction to submitting a justified override.

Baseline and target benchmarks (to be filled after measuring the demo environment):

| Metric | Without RazorGuard | With RazorGuard | Target Delta |
|---|---|---|---|
| Avg. time per escalated case | `[N]` min | `[M]` min | `[N - M]` min saved |
| Avg. cases processed per analyst per shift | `[X]` | `[Y]` | `+[Y - X]` throughput |
| Override decisions with written justification | `[A]`% | 100% | Full audit compliance |

> **Note**: Replace `[N]`, `[M]`, `[X]`, `[Y]`, `[A]` with real measurements after running the demo scenarios (TXN-10021, TXN-40293, TXN-92817) and timing analyst investigation flows.

---

## 6. Honest Architectural Framing

RazorGuard AI is **designed to plug into a gateway's existing event stream** — architecturally, it would consume escalation events from a Kafka topic, SQS queue, or webhook callback from the gateway's scoring engine.

It does **not** claim:
- Actual integration with Razorpay's production systems
- Knowledge of Razorpay's internal event bus, data models, or scoring logic
- That it replaces, competes with, or duplicates Thirdwatch

It **does** demonstrate:
- How a post-escalation investigation console would behave in a realistic risk-ops workflow
- How explainability, audit trails, and relationship graphs reduce analyst cognitive load
- How deterministic scoring + LLM-synthesized explanations can coexist without letting the LLM influence numeric outcomes

All customer, transaction, device, and merchant data in this environment is **synthetic** and does not represent real payment activity.

---

## 7. References

- Razorpay Thirdwatch product page: [https://razorpay.com/thirdwatch/](https://razorpay.com/thirdwatch/) (public)
- RBI Master Direction on Digital Payment Security Controls (public regulatory document)
- PCI DSS v4.0 Requirements (public standard)
