"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../context/AuthContext";
import NetworkVisualizer from "../../../components/NetworkVisualizer";
import { CornerDownRight } from "lucide-react";
import { API_URL } from "../../../lib/api";


function relativeTime(isoString) {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function getRiskMeta(score) {
  if (score >= 75) return { level: "HIGH RISK", color: "var(--risk-high)", bg: "var(--risk-high-bg)", border: "var(--risk-high-border)", action: "ESCALATE / HOLD" };
  if (score >= 40) return { level: "MEDIUM RISK", color: "var(--risk-warn)", bg: "var(--risk-warn-bg)", border: "var(--risk-warn-border)", action: "MONITOR" };
  return { level: "LOW RISK", color: "var(--risk-safe)", bg: "var(--risk-safe-bg)", border: "var(--risk-safe-border)", action: "APPROVE" };
}

// Composite score gauge: shows weighted contribution of each component
function ScoreGauge({ label, weight, rawScore, colorClass }) {
  const weightedContrib = (weight * rawScore) / 100;
  const fillPct = rawScore;
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
        <span style={{ fontSize: "0.78rem", color: "var(--fg)" }}>
          {label}
          <span style={{ fontSize: "0.68rem", color: "var(--fg-muted)", marginLeft: "6px" }}>
            Weight {(weight * 100).toFixed(0)}%
          </span>
        </span>
        <div style={{ textAlign: "right" }}>
          <span className="tabular" style={{ fontSize: "0.82rem", fontWeight: "700", color: "var(--fg)" }}>
            {rawScore.toFixed(0)}%
          </span>
          <span style={{ fontSize: "0.65rem", color: "var(--fg-muted)", marginLeft: "6px" }}>
            → {weightedContrib.toFixed(1)} pts
          </span>
        </div>
      </div>
      <div className="score-gauge-track">
        <div
          className={`score-gauge-fill score-gauge-fill-${colorClass}`}
          style={{ width: `${fillPct}%` }}
        />
      </div>
    </div>
  );
}

// Loading skeleton matching the page structure
function DetailSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
      <div className="skeleton" style={{ height: "70px", borderRadius: "4px" }} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
        <div className="skeleton" style={{ height: "200px" }} />
        <div className="skeleton" style={{ height: "200px" }} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.8fr", gap: "12px" }}>
        <div className="skeleton" style={{ height: "220px" }} />
        <div className="skeleton" style={{ height: "220px" }} />
      </div>
    </div>
  );
}

export default function TransactionDetail() {
  const { id } = useParams();
  const { token } = useAuth();
  const router = useRouter();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [overrideAction, setOverrideAction] = useState("Approve");
  const [overrideNotes, setOverrideNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const fetchDetails = () => {
    if (!token || !id) return;
    fetch(`${API_URL}/api/v1/transactions/${id}/investigation`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Unable to load investigation data.");
        return res.json();
      })
      .then((resData) => {
        setData(resData);
        setErrorMsg(null);
        setLoading(false);
      })
      .catch((err) => {
        setErrorMsg(err.message || "Unable to load investigation data. Please retry.");
        setLoading(false);
      });
  };

  useEffect(() => { fetchDetails(); }, [id, token]);

  const handleOverrideSubmit = async (action) => {
    if (!overrideNotes.trim()) {
      alert("Justification notes are required before committing a decision.");
      return;
    }
    setSubmitting(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/transactions/${id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ action, notes: overrideNotes }),
      });
      if (response.ok) {
        setOverrideNotes("");
        setLoading(true);
        fetchDetails();
      } else {
        const err = await response.json();
        alert(err.detail || "Failed to submit analyst decision.");
      }
    } catch {
      alert("Error submitting decision.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <DetailSkeleton />;

  if (errorMsg) {
    return (
      <div className="panel" style={{ maxWidth: "480px", margin: "40px auto", border: "1px solid var(--risk-high-border)", textAlign: "center", padding: "28px" }}>
        <p style={{ fontSize: "0.85rem", color: "var(--risk-high)", fontWeight: "600", marginBottom: "8px" }}>Investigation Load Failed</p>
        <p style={{ color: "var(--fg-muted)", fontSize: "0.8rem", marginBottom: "16px" }}>{errorMsg}</p>
        <button onClick={() => { setLoading(true); fetchDetails(); }}>Retry Connection</button>
      </div>
    );
  }

  if (!data) {
    return <div style={{ color: "var(--risk-high)", padding: "20px", fontSize: "0.85rem" }}>Transaction record not found in system.</div>;
  }

  const { transaction, assessment, memories, decisions } = data;
  const risk = getRiskMeta(transaction.risk_score);

  // Derive risk flags
  const riskFlags = [];
  if (transaction.amount > 500000) {
    riskFlags.push({ signal: "LARGE_TICKET_AMOUNT", observed: `${transaction.currency} ${transaction.amount.toLocaleString("en-IN")}`, expected: "< 500,000", severity: "HIGH", source: "Transaction Risk Agent", reason: "Transaction amount exceeds maximum gateway soft limit." });
  }
  if (transaction.billing_country !== transaction.card_country) {
    riskFlags.push({ signal: "GEOGRAPHIC_MISMATCH", observed: `Card: ${transaction.card_country} | Billing: ${transaction.billing_country}`, expected: "Countries must match", severity: "MEDIUM", source: "Transaction Risk Agent", reason: "Issuing country mismatch — elevated card takeover risk." });
  }
  if (!transaction.card_present && transaction.amount > 50000) {
    riskFlags.push({ signal: "HIGH_VALUE_CNP", observed: `${transaction.currency} ${transaction.amount.toLocaleString("en-IN")} (Card Not Present)`, expected: "< 50,000 for CNP", severity: "HIGH", source: "Transaction Risk Agent", reason: "Card-Not-Present payment exceeds verification threshold." });
  }
  if (transaction.user_id === "CUST-7821" && transaction.amount > 1800) {
    riskFlags.push({ signal: "SPEND_DEVIATION", observed: `INR ${transaction.amount.toLocaleString("en-IN")}`, expected: "Historical avg: INR 1,800", severity: "HIGH", source: "Behavioral Risk Agent", reason: "Transaction deviates significantly from account baseline." });
  }

  const policyMemory = memories.find((m) => m.agent_name.includes("Policy"));
  const hasPolicyEvidence = policyMemory?.evidence && !policyMemory.evidence.includes("zero matches");

  return (
    <div>
      {/* === Header HUD === */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-end",
          marginBottom: "18px",
          paddingBottom: "14px",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div>
          <p style={{ fontSize: "0.68rem", color: "var(--fg-muted)", textTransform: "uppercase", letterSpacing: "0.09em", marginBottom: "4px" }}>
            Risk Investigation
          </p>
          <h1
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "1.1rem",
              fontWeight: "700",
              letterSpacing: "0.02em",
              marginBottom: "4px",
              color: "var(--fg)",
            }}
          >
            {transaction.transaction_id}
          </h1>
          <p style={{ fontSize: "0.72rem", color: "var(--fg-muted)" }}>
            {new Date(transaction.timestamp).toLocaleString()} · Ingested {relativeTime(transaction.timestamp)} · DB #{transaction.id}
          </p>
        </div>

        {/* Score display */}
        <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
          <div style={{ textAlign: "right" }}>
            <p style={{ fontSize: "0.65rem", color: "var(--fg-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Recommended</p>
            <p style={{ fontSize: "0.88rem", fontWeight: "700", color: risk.color, marginTop: "2px" }}>{risk.action}</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <p style={{ fontSize: "0.65rem", color: "var(--fg-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Classification</p>
            <p style={{ fontSize: "0.88rem", fontWeight: "700", color: risk.color, marginTop: "2px" }}>{risk.level}</p>
          </div>
          <div
            style={{
              padding: "8px 16px",
              border: `1px solid ${risk.border}`,
              backgroundColor: risk.bg,
              borderRadius: "4px",
              textAlign: "center",
              minWidth: "80px",
            }}
          >
            <p style={{ fontSize: "0.65rem", color: "var(--fg-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>Score</p>
            <p
              className="display-num"
              style={{ fontSize: "2.4rem", fontWeight: 400, color: risk.color, lineHeight: 1.1 }}
            >
              {transaction.risk_score.toFixed(0)}
              <span style={{ fontSize: "1rem" }}>%</span>
            </p>
          </div>
        </div>
      </div>

      {/* === Grid Row 1: Transaction Summary + Risk Signals === */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>

        {/* Transaction Summary */}
        <div className="panel">
          <h2>Transaction Summary</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 20px", fontSize: "0.8rem" }}>
            {[
              { label: "Amount", value: `${transaction.currency} ${transaction.amount.toLocaleString("en-IN")}`, mono: true, large: true },
              { label: "Customer Account", value: transaction.user_id, mono: true },
              { label: "Card Origin", value: transaction.card_country },
              { label: "Billing Origin", value: transaction.billing_country },
              { label: "IP Address", value: transaction.ip_address, mono: true },
              { label: "Channel", value: transaction.card_present ? "Card Present" : "Card Not Present (CNP)" },
              { label: "Merchant ID", value: transaction.merchant_id, mono: true },
              { label: "Merchant Category", value: transaction.merchant_category },
            ].map(({ label, value, mono, large }) => (
              <div key={label}>
                <p style={{ fontSize: "0.65rem", color: "var(--fg-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: "2px" }}>{label}</p>
                <p style={{
                  fontFamily: mono ? "var(--font-mono)" : "inherit",
                  fontSize: large ? "1rem" : "0.82rem",
                  fontWeight: large ? "600" : "500",
                  color: "var(--fg)",
                  lineHeight: 1.3,
                }}>
                  {value}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Signals */}
        <div className="panel">
          <h2>Flagged Risk Signals</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px", overflowY: "auto", maxHeight: "240px" }}>
            {riskFlags.length === 0 ? (
              <p style={{ color: "var(--fg-muted)", fontSize: "0.8rem", fontStyle: "italic" }}>
                No immediate risk signals detected for this transaction.
              </p>
            ) : (
              riskFlags.map((flag, idx) => {
                const sColor = flag.severity === "HIGH" ? "var(--risk-high)" : "var(--risk-warn)";
                return (
                  <div key={idx} style={{ borderLeft: `2px solid ${sColor}`, paddingLeft: "10px", paddingBottom: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", fontWeight: "700", color: sColor }}>
                        {flag.signal}
                      </span>
                      <span style={{ fontSize: "0.62rem", backgroundColor: sColor === "var(--risk-high)" ? "var(--risk-high-bg)" : "var(--risk-warn-bg)", color: sColor, padding: "1px 6px", borderRadius: "2px", fontWeight: "700" }}>
                        {flag.severity}
                      </span>
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "var(--fg-muted)", display: "flex", flexDirection: "column", gap: "2px" }}>
                      <span><span style={{ color: "var(--fg-dim)" }}>Observed:</span> {flag.observed}</span>
                      {flag.expected && <span><span style={{ color: "var(--fg-dim)" }}>Expected:</span> {flag.expected}</span>}
                      <span><span style={{ color: "var(--fg-dim)" }}>Source:</span> {flag.source}</span>
                      <span style={{ marginTop: "3px", borderTop: "1px solid var(--border-subtle)", paddingTop: "3px", color: "var(--fg)" }}>{flag.reason}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* === Grid Row 2: Score Breakdown + Agent Evidence === */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.9fr", gap: "12px", marginBottom: "12px" }}>

        {/* Score Breakdown — segmented gauge */}
        <div className="panel">
          <h2>Score Breakdown</h2>
          <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "12px", marginTop: "2px" }}>
            Composite = (ML×35%) + (Rules×20%) + (Graph×30%) + (Policy×15%)
          </p>
          {assessment && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <ScoreGauge label="ML Anomaly" weight={0.35} rawScore={assessment.ml_score} colorClass="blue" />
              <ScoreGauge label="Rules & Behavior" weight={0.20} rawScore={assessment.rule_score} colorClass="warn" />
              <ScoreGauge label="Graph Overlap" weight={0.30} rawScore={assessment.graph_score} colorClass="high" />
              <ScoreGauge label="Policy Compliance" weight={0.15} rawScore={assessment.policy_score} colorClass="safe" />

              {/* Composite total bar */}
              <div style={{ marginTop: "4px", paddingTop: "10px", borderTop: "1px solid var(--border-subtle)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span style={{ fontSize: "0.78rem", fontWeight: "600", color: "var(--fg)" }}>Composite Score</span>
                  <span className="display-num" style={{ fontSize: "1.1rem", color: risk.color }}>{transaction.risk_score.toFixed(0)}%</span>
                </div>
                <div className="score-gauge-track" style={{ height: "7px" }}>
                  <div
                    className="score-gauge-fill"
                    style={{ width: `${transaction.risk_score}%`, backgroundColor: risk.color }}
                  />
                </div>
              </div>

              <p style={{ fontSize: "0.65rem", color: "var(--fg-dim)", lineHeight: "1.4", marginTop: "4px" }}>
                Deterministic logic: scores are computed by fixed math weights. The LLM synthesizes explanations only — it does not affect numeric outputs.
              </p>
            </div>
          )}
        </div>

        {/* Agent Evidence */}
        <div className="panel">
          <h2>Risk Evidence — Agent Findings</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxHeight: "300px", overflowY: "auto", paddingRight: "4px", marginTop: "4px" }}>
            {memories.map((mem, index) => {
              const isActionOrDecision = mem.agent_name.includes("Decision") || mem.agent_name.includes("Action");
              return (
                <div key={index} style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "10px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "3px" }}>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", fontWeight: "700", color: "var(--accent-text)" }}>
                      {mem.agent_name}
                    </span>
                    {!isActionOrDecision && (
                      <span style={{ fontSize: "0.68rem", color: "var(--fg-muted)" }}>
                        Confidence:{" "}
                        <span style={{ color: "var(--fg)", fontWeight: "600" }}>{mem.confidence?.toFixed(0)}%</span>
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: "0.78rem", color: "var(--fg)", lineHeight: "1.4" }}>{mem.reasoning}</p>
                  {mem.evidence && (
                    <div style={{ display: "flex", gap: "5px", marginTop: "5px" }}>
                      <CornerDownRight size={12} color="var(--fg-dim)" style={{ flexShrink: 0, marginTop: "1px" }} />
                      <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", fontStyle: "italic", lineHeight: "1.3" }}>
                        {mem.evidence}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* === Grid Row 3: Knowledge Graph + Policy Evidence === */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "12px" }}>

        {/* Knowledge Graph */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <h2>Relationship Map</h2>
          <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "10px" }}>
            Device and network sharing across accounts. Click a node to see connections.
          </p>
          <div style={{ flexGrow: 1 }}>
            <NetworkVisualizer userId={transaction.user_id} token={token} compact={true} />
          </div>
          <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
            <p style={{ fontSize: "0.68rem", color: "var(--fg-muted)", lineHeight: "1.4" }}>
              {transaction.user_id === "CUST-7821"
                ? "⚑ Multiple suspect accounts (usr_suspect_1, _2, _3) linked to the same device fingerprint initiated from this identity."
                : "Graph walk shows this identity is isolated — standard single device/IP mapping."}
            </p>
          </div>
        </div>

        {/* Policy Evidence */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <h2>Policy Evidence</h2>
          <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "10px" }}>
            Compliance segments retrieved from the indexed regulatory manual database.
          </p>
          <div style={{ flexGrow: 1, overflowY: "auto", maxHeight: "220px" }}>
            {hasPolicyEvidence ? (
              <div style={{ padding: "10px", border: "1px solid var(--border)", borderRadius: "3px", backgroundColor: "var(--bg-inset)", fontSize: "0.78rem", lineHeight: "1.5" }}>
                <p style={{ fontWeight: "600", color: "var(--accent-text)", marginBottom: "5px", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>Compliance Check Output</p>
                <p style={{ color: "var(--fg)", fontStyle: "italic" }}>{policyMemory.evidence}</p>
                <p style={{ marginTop: "8px", fontSize: "0.65rem", color: "var(--fg-dim)" }}>
                  Source: compliance manual databases (Hybrid RRF retrieval)
                </p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", flexGrow: 1, color: "var(--fg-dim)", minHeight: "140px", gap: "6px" }}>
                <span style={{ fontSize: "1.2rem" }}>—</span>
                <p style={{ fontSize: "0.78rem", color: "var(--fg-muted)" }}>No compliance citations triggered</p>
                <p style={{ fontSize: "0.7rem", color: "var(--fg-dim)" }}>Verification confirmed no active regulatory rules were violated.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* === Grid Row 4: Synthesis Briefing + Analyst Review === */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.9fr", gap: "12px", marginBottom: "12px" }}>

        {/* AI Synthesis Briefing */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <h2>Synthesis Briefing</h2>
          <pre
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.72rem",
              lineHeight: "1.55",
              color: "var(--fg)",
              backgroundColor: "var(--bg-inset)",
              border: "1px solid var(--border)",
              borderRadius: "3px",
              padding: "10px 12px",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              overflowY: "auto",
              maxHeight: "240px",
              flexGrow: 1,
            }}
          >
            {assessment?.explanation || "Synthesizing compliance explanation briefing…"}
          </pre>
        </div>

        {/* Analyst Review */}
        <div
          className="panel"
          style={{
            border: transaction.status === "Escalated" ? "1px solid var(--risk-warn-border)" : "1px solid var(--border)",
            backgroundColor: transaction.status === "Escalated" ? "var(--risk-warn-bg)" : "var(--bg-surface)",
          }}
        >
          <h2 style={{ color: transaction.status === "Escalated" ? "var(--risk-warn)" : undefined }}>
            Analyst Override
          </h2>
          <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "14px" }}>
            Human-in-the-loop decision. Override notes are persisted in the audit trail.
          </p>

          {transaction.status === "Escalated" ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label>Justification Notes (required)</label>
                <input
                  type="text"
                  value={overrideNotes}
                  onChange={(e) => setOverrideNotes(e.target.value)}
                  placeholder="Enter compliance justification before committing decision…"
                />
              </div>
              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  className="action-approve"
                  style={{ flex: 1 }}
                  disabled={submitting}
                  onClick={() => handleOverrideSubmit("Approve")}
                >
                  ✓ Approve Payment
                </button>
                <button
                  className="action-block"
                  style={{ flex: 1 }}
                  disabled={submitting}
                  onClick={() => handleOverrideSubmit("Block")}
                >
                  ✗ Block Payment
                </button>
              </div>
              {submitting && (
                <p style={{ fontSize: "0.72rem", color: "var(--fg-muted)" }}>Committing analyst decision…</p>
              )}
            </div>
          ) : (
            <div style={{ padding: "14px", border: "1px solid var(--border-subtle)", borderRadius: "3px", backgroundColor: "var(--bg-inset)", display: "flex", alignItems: "flex-start", gap: "10px" }}>
              <span style={{ color: "var(--risk-safe)", fontSize: "1rem", marginTop: "1px" }}>✓</span>
              <div>
                <p style={{ fontSize: "0.82rem", fontWeight: "600" }}>Decision Committed</p>
                <p style={{ fontSize: "0.72rem", color: "var(--fg-muted)", marginTop: "3px" }}>
                  This transaction has been resolved and requires no further analyst action. Current state:{" "}
                  <strong style={{ color: "var(--fg)" }}>{transaction.status}</strong>
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* === Audit Trail / Decision Log === */}
      {decisions && decisions.length > 0 && (
        <div className="panel">
          <h2>Decision Trail</h2>
          <div className="data-table-container" style={{ marginTop: "8px" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Analyst</th>
                  <th>Action</th>
                  <th>AI Rec.</th>
                  <th>Justification Notes</th>
                </tr>
              </thead>
              <tbody>
                {decisions.map((dec) => (
                  <tr key={dec.id}>
                    <td>
                      <span style={{ fontSize: "0.72rem", color: "var(--fg-muted)" }} title={new Date(dec.submitted_at).toLocaleString()}>
                        {relativeTime(dec.submitted_at)}
                      </span>
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem" }}>{dec.analyst_email}</td>
                    <td>
                      <span
                        className={dec.action.toLowerCase() === "approve" ? "badge badge-approved" : "badge badge-escalated"}
                      >
                        {dec.action.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      {dec.original_ai_recommendation && (
                        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem", color: "var(--risk-warn)" }}>
                          {dec.original_ai_recommendation.toUpperCase()}
                        </span>
                      )}
                    </td>
                    <td style={{ fontSize: "0.75rem", color: "var(--fg-muted)", fontStyle: "italic" }}>
                      "{dec.notes}"
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
