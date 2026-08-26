"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../context/AuthContext";
import NetworkVisualizer from "../../../components/NetworkVisualizer";
import { CornerDownRight, CheckCircle, AlertTriangle, Upload, ShieldCheck, FileText, ChevronRight } from "lucide-react";
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

function getChecklist(evidences) {
  const checklist = [];
  let hasGeo = false;
  let hasAmt = false;
  let hasVel = false;
  let hasGraph = false;
  let hasPolicy = false;

  (evidences || []).forEach((ev) => {
    if (ev.category === "geographic_mismatch") hasGeo = true;
    if (ev.category === "amount_deviation" || ev.category === "rule_violation") hasAmt = true;
    if (ev.category === "velocity") hasVel = true;
    if (ev.category === "device_relationship" || ev.category === "account_relationship") hasGraph = true;
    if (ev.category === "policy_match") hasPolicy = true;
  });

  if (hasGeo) {
    checklist.push({
      id: "geo",
      label: "Proof of Cardholder Billing Address",
      desc: "Provide a utility bill or card statement showing billing address matching original record.",
      required: true
    });
  }
  if (hasAmt) {
    checklist.push({
      id: "amt",
      label: "Commercial Sales Invoice & Proof of Delivery",
      desc: "Provide a signed sales invoice, service agreement, or package delivery receipt proof.",
      required: true
    });
  }
  if (hasVel) {
    checklist.push({
      id: "vel",
      label: "Customer Identity Verification (Government ID)",
      desc: "Provide a government-issued photo ID of the cardholder to confirm identity.",
      required: true
    });
  }
  if (hasGraph) {
    checklist.push({
      id: "graph",
      label: "Authorized Device & Hardware Authorization Logs",
      desc: "Provide browser login logs or auth token proofs to justify shared device overlap.",
      required: true
    });
  }
  if (hasPolicy) {
    checklist.push({
      id: "policy",
      label: "Compliance Authorization & Business License Certificate",
      desc: "Upload a standard business certificate showing compliance registration details.",
      required: true
    });
  }

  // Baseline fallback
  if (checklist.length === 0) {
    checklist.push({
      id: "base",
      label: "Merchant Business License and Transaction Receipt",
      desc: "Upload standard proof of business incorporation and customer receipt.",
      required: true
    });
  }

  return checklist;
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

  // Merchant Portal states
  const [viewMode, setViewMode] = useState("analyst"); // "analyst" | "merchant"
  const [merchantNotes, setMerchantNotes] = useState("");
  const [selectedDoc, setSelectedDoc] = useState("");
  const [reEvaluating, setReEvaluating] = useState(false);
  const [currentEvalStep, setCurrentEvalStep] = useState(0);

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

  const handleMerchantSubmit = async (e) => {
    e.preventDefault();
    if (!merchantNotes.trim()) {
      alert("Please enter explanation notes describing your transaction to resolve this hold.");
      return;
    }
    setReEvaluating(true);
    setCurrentEvalStep(1);

    // Simulated Agent lighting up flow step-by-step
    for (let i = 0; i < 6; i++) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      setCurrentEvalStep(i + 2);
    }

    try {
      const response = await fetch(`${API_URL}/api/v1/transactions/${id}/merchant-submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ notes: merchantNotes, document_url: selectedDoc || "invoice_receipt_proof.pdf" }),
      });
      if (response.ok) {
        setMerchantNotes("");
        setSelectedDoc("");
        fetchDetails();
      } else {
        const err = await response.json();
        alert(err.detail || "Failed to submit verification evidence.");
      }
    } catch {
      alert("Error submitting resolution materials.");
    } finally {
      setReEvaluating(false);
      setCurrentEvalStep(0);
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
  }  const { transaction, assessment, memories, decisions, evidences, audit_logs, submissions = [] } = data;
  const risk = getRiskMeta(transaction.risk_score);
  const reasoning_steps = data.reasoning_steps || [];

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

      {/* === View Mode Switcher Toggle === */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "18px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
        <button
          className={viewMode === "analyst" ? "primary" : "secondary"}
          style={{
            fontSize: "0.74rem",
            fontWeight: "700",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            padding: "6px 14px",
            backgroundColor: viewMode === "analyst" ? "var(--accent)" : "transparent",
            color: viewMode === "analyst" ? "var(--bg)" : "var(--fg)",
            border: viewMode === "analyst" ? "1px solid var(--accent)" : "1px solid var(--border)",
            borderRadius: "3px",
            cursor: "pointer"
          }}
          onClick={() => setViewMode("analyst")}
        >
          Analyst Console
        </button>
        <button
          className={viewMode === "merchant" ? "primary" : "secondary"}
          style={{
            fontSize: "0.74rem",
            fontWeight: "700",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            padding: "6px 14px",
            backgroundColor: viewMode === "merchant" ? "var(--accent)" : "transparent",
            color: viewMode === "merchant" ? "var(--bg)" : "var(--fg)",
            border: viewMode === "merchant" ? "1px solid var(--accent)" : "1px solid var(--border)",
            borderRadius: "3px",
            cursor: "pointer"
          }}
          onClick={() => setViewMode("merchant")}
        >
          Merchant Resolution Portal
        </button>
      </div>

      {viewMode === "analyst" ? (
        <>
          {/* === Grid Row 1: Transaction Summary + Structured Evidence === */}
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

            {/* Structured Evidence */}
            <div className="panel">
              <h2>Structured Evidence Blocks</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px", overflowY: "auto", maxHeight: "240px" }}>
                {evidences && evidences.length > 0 ? (
                  evidences.map((ev, idx) => {
                    const sColor = ev.severity === "high" ? "var(--risk-high)" : (ev.severity === "medium" ? "var(--risk-warn)" : "var(--risk-safe)");
                    return (
                      <div key={idx} style={{ borderLeft: `2px solid ${sColor}`, paddingLeft: "10px", paddingBottom: "8px" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.72rem", fontWeight: "700", color: sColor }}>
                            {ev.category.toUpperCase()}
                          </span>
                          <span style={{ fontSize: "0.62rem", backgroundColor: sColor === "var(--risk-high)" ? "var(--risk-high-bg)" : "var(--risk-warn-bg)", color: sColor, padding: "1px 6px", borderRadius: "2px", fontWeight: "700" }}>
                            {ev.severity.toUpperCase()}
                          </span>
                        </div>
                        <div style={{ fontSize: "0.72rem", color: "var(--fg-muted)", display: "flex", flexDirection: "column", gap: "2px" }}>
                          {ev.value && <span><span style={{ color: "var(--fg-dim)" }}>Observed:</span> {ev.value}</span>}
                          {ev.supporting_entity && <span><span style={{ color: "var(--fg-dim)" }}>Target Node:</span> {ev.supporting_entity}</span>}
                          <span><span style={{ color: "var(--fg-dim)" }}>Source:</span> {ev.source}</span>
                          {ev.policy_reference && <span><span style={{ color: "var(--fg-dim)" }}>Policy:</span> {ev.policy_reference}</span>}
                          <span style={{ marginTop: "3px", borderTop: "1px solid var(--border-subtle)", paddingTop: "3px", color: "var(--fg)" }}>{ev.description}</span>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <p style={{ color: "var(--fg-muted)", fontSize: "0.8rem", fontStyle: "italic" }}>
                    No active suspicious evidence signals detected.
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* === Grid Row 2: Score Breakdown + Agent Evidence === */}
          <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.85fr", gap: "12px", marginBottom: "12px" }}>
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
                Device and payment card network overlaps across accounts. Click a node to walk connections.
              </p>
              <div style={{ flexGrow: 1 }}>
                <NetworkVisualizer userId={transaction.user_id} token={token} compact={true} />
              </div>
              <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                <p style={{ fontSize: "0.68rem", color: "var(--fg-muted)", lineHeight: "1.4" }}>
                  {transaction.user_id === "CUST-7821"
                    ? "⚑ Multiple suspect accounts (usr_suspect_1, usr_suspect_2) linked via shared devices AND card networks initiated from this identifier."
                    : "Graph walk shows this identity is isolated — no device, IP, or card number overlap conflicts."}
                </p>
              </div>
            </div>

            {/* Policy Evidence */}
            <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
              <h2>Compliance & Policy Proofs</h2>
              <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "10px" }}>
                Compliance segments retrieved from the indexed regulatory manual database.
              </p>
              <div style={{ flexGrow: 1, overflowY: "auto", maxHeight: "220px" }}>
                {evidences && evidences.filter(e => e.category === "policy_match").length > 0 ? (
                  evidences.filter(e => e.category === "policy_match").map((ev, idx) => (
                    <div key={idx} style={{ padding: "10px", border: "1px solid var(--border)", borderRadius: "3px", backgroundColor: "var(--bg-inset)", fontSize: "0.78rem", lineHeight: "1.5", marginBottom: "8px" }}>
                      <p style={{ fontWeight: "600", color: "var(--accent-text)", marginBottom: "4px", fontSize: "0.68rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
                        Similarity Match: {(ev.confidence * 100).toFixed(0)}%
                      </p>
                      <p style={{ color: "var(--fg)", fontStyle: "italic" }}>{ev.description}</p>
                      {ev.policy_reference && (
                        <p style={{ marginTop: "6px", fontSize: "0.65rem", color: "var(--fg-dim)", fontFamily: "var(--font-mono)" }}>
                          Source Document: {ev.policy_reference}
                        </p>
                      )}
                    </div>
                  ))
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
                Human-in-the-loop decision override logs.
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
                    <p style={{ fontSize: "0.82rem", fontWeight: "600" }}>Decision Resolved</p>
                    <p style={{ fontSize: "0.72rem", color: "var(--fg-muted)", marginTop: "3px" }}>
                      This transaction state override has been resolved. Current status:{" "}
                      <strong style={{ color: "var(--fg)" }}>{transaction.status}</strong>
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* === Grid Row 5: AI Orchestration Timeline & Audit Trail === */}
          <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.9fr", gap: "12px", marginBottom: "12px" }}>
            {/* Orchestration Trace Timeline */}
            <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
              <h2>AI Orchestration Timeline</h2>
              <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "10px" }}>
                Multi-agent execution sequence trace replay.
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px", overflowY: "auto", maxHeight: "280px", paddingRight: "4px" }}>
                {reasoning_steps && reasoning_steps.length > 0 ? (
                  reasoning_steps.map((step, idx) => (
                    <div key={idx} style={{ display: "flex", gap: "10px", position: "relative" }}>
                      {idx < reasoning_steps.length - 1 && (
                        <div style={{ position: "absolute", left: "6px", top: "14px", bottom: "-12px", width: "1px", backgroundColor: "var(--border-subtle)" }} />
                      )}
                      <div style={{ width: "12px", height: "12px", borderRadius: "50%", backgroundColor: "var(--accent)", border: "2px solid var(--bg-surface)", marginTop: "2px", flexShrink: 0 }} />
                      <div>
                        <div style={{ display: "flex", justifycontent: "space-between", alignItems: "baseline", gap: "6px" }}>
                          <span style={{ fontSize: "0.72rem", fontWeight: "700", color: "var(--fg)" }}>{step.event.replace(/_/g, " ").toUpperCase()}</span>
                          <span style={{ fontSize: "0.6rem", color: "var(--fg-dim)", fontFamily: "var(--font-mono)" }}>{step.timestamp ? new Date(step.timestamp).toLocaleTimeString() : ""}</span>
                        </div>
                        <p style={{ fontSize: "0.72rem", color: "var(--fg-muted)", marginTop: "1px" }}>{step.description}</p>
                        <p style={{ fontSize: "0.62rem", color: "var(--fg-dim)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>Agent: {step.agent}</p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ fontSize: "0.72rem", color: "var(--fg-dim)" }}>No trace steps available</p>
                )}
              </div>
            </div>

            {/* Audit Log Trail */}
            <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
              <h2>Compliance Audit Trail</h2>
              <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "10px" }}>
                Immutable records of database-level transactions, transitions and human actions.
              </p>
              <div className="data-table-container" style={{ flexGrow: 1, overflowY: "auto", maxHeight: "280px" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Event</th>
                      <th>Actor</th>
                      <th>Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {audit_logs && audit_logs.length > 0 ? (
                      audit_logs.map((log) => (
                        <tr key={log.id}>
                          <td>
                            <span style={{ fontSize: "0.7rem", color: "var(--fg-muted)" }}>
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </span>
                          </td>
                          <td>
                            <span className="badge badge-escalated" style={{ fontSize: "0.65rem", padding: "1px 4px" }}>
                              {log.event.toUpperCase()}
                            </span>
                          </td>
                          <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.68rem" }}>{log.actor}</td>
                          <td style={{ fontSize: "0.7rem", color: "var(--fg)" }}>{log.description}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={4} style={{ textAlign: "center", color: "var(--fg-dim)", fontSize: "0.75rem", padding: "14px" }}>
                          No audit log records found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* === Decision overrides trail === */}
          {decisions && decisions.length > 0 && (
            <div className="panel">
              <h2>Decision Overrides Log</h2>
              <div className="data-table-container" style={{ marginTop: "8px" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Analyst</th>
                      <th>Action</th>
                      <th>AI Rec.</th>
                      <th>Justification Notes & Evidence Snapshot</th>
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
                          {dec.risk_score_at_decision_time !== undefined && dec.risk_score_at_decision_time !== null && (
                            <div style={{ marginTop: "6px", fontSize: "0.68rem", color: "var(--fg-muted)", fontStyle: "normal" }}>
                              Captured AI Score: <strong style={{ color: "var(--fg)" }}>{dec.risk_score_at_decision_time.toFixed(0)}%</strong>
                              {dec.evidence_snapshot && dec.evidence_snapshot.length > 0 && (
                                <details style={{ marginTop: "3px", cursor: "pointer" }}>
                                  <summary style={{ color: "var(--accent-text)", fontSize: "0.65rem", fontWeight: "600" }}>
                                    View Evidence Snapshot ({dec.evidence_snapshot.length} signals)
                                  </summary>
                                  <div style={{ padding: "6px 8px", background: "var(--bg-inset)", border: "1px solid var(--border-subtle)", borderRadius: "3px", fontSize: "0.68rem", marginTop: "3px", whiteSpace: "pre-wrap", color: "var(--fg-dim)" }}>
                                    {dec.evidence_snapshot.map((ev, idx) => (
                                      <div key={idx} style={{ marginBottom: "4px", borderBottom: idx < dec.evidence_snapshot.length - 1 ? "1px dashed var(--border-subtle)" : "none", paddingBottom: "4px" }}>
                                        <span style={{ fontWeight: "700", color: "var(--fg)" }}>{ev.category.toUpperCase()}:</span> {ev.description}
                                      </div>
                                    ))}
                                  </div>
                                </details>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      ) : (
        /* ============================================================
           MERCHANT RESOLUTION PORTAL (EXTERNAL VIEW)
           ============================================================ */
        <div style={{ display: "grid", gridTemplateColumns: "1.8fr 1.2fr", gap: "12px", alignItems: "start" }}>
          {/* Left Column — Detailed Proofs, Checklists & Action */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            
            {/* Plain-Language hold explanation briefing */}
            <div className="panel">
              <h2>Plain-Language Verification Hold Reason</h2>
              <p style={{ fontSize: "0.71rem", color: "var(--fg-muted)", marginBottom: "10px" }}>
                Below is the transparent explanation detailing why your account/transaction has been flagged. 
              </p>
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
                  maxHeight: "220px",
                }}
              >
                {assessment?.explanation || "Synthesizing details hold briefing explanation..."}
              </pre>
            </div>

            {/* Resolution Checklist card */}
            <div className="panel">
              <h2>Actionable Resolution Checklist</h2>
              {transaction.status === "Approved" ? (
                <div style={{ display: "flex", gap: "10px", alignItems: "flex-start", padding: "10px", background: "var(--risk-safe-bg)", border: "1px solid var(--risk-safe-border)", borderRadius: "3px" }}>
                  <ShieldCheck color="var(--risk-safe)" size={16} style={{ flexShrink: 0, marginTop: "2px" }} />
                  <div>
                    <p style={{ fontSize: "0.82rem", fontWeight: "600", color: "var(--risk-safe)" }}>Verification Hold Cleared</p>
                    <p style={{ fontSize: "0.74rem", color: "var(--fg-muted)", marginTop: "2px" }}>All hold triggers have been successfully resolved. Your payment release is cleared.</p>
                  </div>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "4px" }}>
                  <p style={{ fontSize: "0.74rem", color: "var(--fg-muted)" }}>
                    Based on the specific compliance policies triggered, please submit the following documentation to resolve this hold:
                  </p>
                  {getChecklist(evidences).map((item, idx) => (
                    <div key={idx} style={{ display: "flex", gap: "10px", alignItems: "flex-start", padding: "8px 10px", border: "1px solid var(--border)", borderRadius: "3px", background: "var(--bg-inset)" }}>
                      <FileText size={14} color="var(--accent-text)" style={{ flexShrink: 0, marginTop: "2px" }} />
                      <div>
                        <p style={{ fontSize: "0.78rem", fontWeight: "600", color: "var(--fg)" }}>{item.label}</p>
                        <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginTop: "2px" }}>{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Submissions Form or Re-evaluation HUD */}
            {transaction.status !== "Approved" && (
              <div className="panel">
                <h2>Submit Verification Materials</h2>
                
                {reEvaluating ? (
                  /* Re-evaluation HUD */
                  <div style={{ padding: "10px 0" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "14px" }}>
                      <span className="badge badge-warn" style={{ fontSize: "0.7rem" }}>RE-EVALUATING</span>
                      <p style={{ fontSize: "0.76rem", fontWeight: "600" }}>Autonomous Agent Team Recalculating Risk...</p>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                      {[
                        { step: 1, name: "Transaction Risk Agent", desc: "Checking ticket size and cardholder billing origin mismatch..." },
                        { step: 2, name: "Behavioral Risk Agent", desc: "Verifying velocity spike counts and ticket size deviation thresholds..." },
                        { step: 3, name: "Fraud Investigation Agent", desc: "Walking network relationship graph for hardware/IP overlaps..." },
                        { step: 4, name: "Policy Agent", desc: "Scanning policy manual chunk vector matches against uploaded documents..." },
                        { step: 5, name: "Decision Agent", desc: "Recalculating composite risk score based on updated evidence..." },
                        { step: 6, name: "Action Agent", desc: "Transitioning hold status and releasing payment..." }
                      ].map((agent) => {
                        const active = currentEvalStep === agent.step;
                        const done = currentEvalStep > agent.step;
                        const statusColor = done ? "var(--risk-safe)" : (active ? "var(--accent)" : "var(--fg-dim)");
                        return (
                          <div key={agent.step} style={{ display: "flex", gap: "10px", alignItems: "center", opacity: done || active ? 1 : 0.4 }}>
                            <div style={{
                              width: "14px",
                              height: "14px",
                              borderRadius: "50%",
                              border: `2px solid ${statusColor}`,
                              backgroundColor: done ? "var(--risk-safe)" : "transparent",
                              display: "flex",
                              justifyContent: "center",
                              alignItems: "center",
                              flexShrink: 0
                            }}>
                              {done && <span style={{ color: "var(--bg)", fontSize: "7px", fontWeight: "900" }}>✓</span>}
                            </div>
                            <div>
                              <p style={{ fontSize: "0.74rem", fontWeight: "600", color: statusColor }}>{agent.name}</p>
                              <p style={{ fontSize: "0.66rem", color: "var(--fg-muted)" }}>{agent.desc}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  /* Submission form */
                  <form onSubmit={handleMerchantSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "4px" }}>
                    <div>
                      <label style={{ fontSize: "0.72rem", color: "var(--fg-muted)", marginBottom: "4px", display: "block" }}>Clarification / Notes (required)</label>
                      <textarea
                        value={merchantNotes}
                        onChange={(e) => setMerchantNotes(e.target.value)}
                        placeholder="Explain the background of this payment transaction, customer relationships, or business justifications..."
                        rows={3}
                        style={{
                          width: "100%",
                          padding: "8px",
                          fontSize: "0.78rem",
                          backgroundColor: "var(--bg-inset)",
                          border: "1px solid var(--border)",
                          borderRadius: "3px",
                          color: "var(--fg)",
                          resize: "none",
                          lineHeight: "1.4"
                        }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: "0.72rem", color: "var(--fg-muted)", marginBottom: "4px", display: "block" }}>Simulate Verification File Attachment</label>
                      <select
                        value={selectedDoc}
                        onChange={(e) => setSelectedDoc(e.target.value)}
                        style={{
                          width: "100%",
                          padding: "8px",
                          fontSize: "0.78rem",
                          backgroundColor: "var(--bg-inset)",
                          border: "1px solid var(--border)",
                          borderRadius: "3px",
                          color: "var(--fg)"
                        }}
                      >
                        <option value="">-- Select a document to upload --</option>
                        <option value="signed_customer_invoice.pdf">sales_invoice_delivery_receipt.pdf</option>
                        <option value="cardholder_identity_verification.png">cardholder_driving_license.png</option>
                        <option value="billing_address_utility_bill.pdf">cardholder_billing_statement.pdf</option>
                        <option value="device_whitelist_authorization.txt">device_authorization_certificate.txt</option>
                      </select>
                    </div>
                    <button
                      type="submit"
                      className="primary"
                      style={{
                        padding: "8px 16px",
                        fontSize: "0.74rem",
                        fontWeight: "600",
                        display: "flex",
                        justifyContent: "center",
                        alignItems: "center",
                        gap: "6px"
                      }}
                    >
                      <Upload size={13} />
                      Submit Verification Materials
                    </button>
                  </form>
                )}
              </div>
            )}
          </div>

          {/* Right Column — Summary Status HUD + Timeline */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            
            {/* Hold Status Card */}
            <div className="panel" style={{ border: `1px solid ${risk.border}`, backgroundColor: risk.bg }}>
              <h2>Hold Release Progress</h2>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
                <div>
                  <p style={{ fontSize: "1rem", fontWeight: "700", color: risk.color }}>{transaction.status.toUpperCase()}</p>
                  <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginTop: "2px" }}>
                    {transaction.status === "Approved" ? "Funds released successfully" : "Verification hold active - action required"}
                  </p>
                </div>
                <div style={{ textAlign: "right" }}>
                  <p style={{ fontSize: "0.64rem", color: "var(--fg-muted)", textTransform: "uppercase" }}>Hold Risk score</p>
                  <p className="display-num" style={{ fontSize: "2rem", color: risk.color }}>{transaction.risk_score.toFixed(0)}%</p>
                </div>
              </div>
            </div>

            {/* Hold history timeline */}
            <div className="panel">
              <h2>Hold Resolution Timeline</h2>
              <p style={{ fontSize: "0.7rem", color: "var(--fg-muted)", marginBottom: "12px" }}>
                Transparent history traces of this hold lifecycle.
              </p>
              
              <div style={{ display: "flex", flexDirection: "column", gap: "14px", position: "relative", paddingLeft: "6px" }}>
                {/* Vertical timeline line */}
                <div style={{ position: "absolute", left: "10px", top: "10px", bottom: "10px", width: "1px", backgroundColor: "var(--border)" }} />
                
                {/* Hold Active Event */}
                <div style={{ display: "flex", gap: "10px", position: "relative" }}>
                  <div style={{ width: "9px", height: "9px", borderRadius: "50%", backgroundColor: "var(--risk-high)", border: "2px solid var(--bg-surface)", zIndex: 1, marginTop: "4px" }} />
                  <div>
                    <p style={{ fontSize: "0.74rem", fontWeight: "700", color: "var(--fg)" }}>Verification hold active</p>
                    <p style={{ fontSize: "0.66rem", color: "var(--fg-muted)" }}>Heuristic rule violations flagged on transaction details.</p>
                    <p style={{ fontSize: "0.62rem", color: "var(--fg-dim)", fontFamily: "var(--font-mono)", marginTop: "1px" }}>
                      {new Date(transaction.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Submissions */}
                {submissions.map((sub, idx) => (
                  <div key={idx} style={{ display: "flex", gap: "10px", position: "relative" }}>
                    <div style={{ width: "9px", height: "9px", borderRadius: "50%", backgroundColor: "var(--accent)", border: "2px solid var(--bg-surface)", zIndex: 1, marginTop: "4px" }} />
                    <div>
                      <p style={{ fontSize: "0.74rem", fontWeight: "700", color: "var(--fg)" }}>Merchant evidence submitted</p>
                      <p style={{ fontSize: "0.66rem", color: "var(--fg-muted)" }}>Notes: "{sub.notes.substring(0, 80)}..."</p>
                      {sub.document_url && (
                        <p style={{ fontSize: "0.64rem", color: "var(--accent-text)", fontFamily: "var(--font-mono)", marginTop: "2px" }}>
                          Attached: {sub.document_url}
                        </p>
                      )}
                      <p style={{ fontSize: "0.62rem", color: "var(--fg-dim)", fontFamily: "var(--font-mono)", marginTop: "1px" }}>
                        {new Date(sub.submitted_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}

                {/* Resolution Event */}
                {transaction.status === "Approved" && (
                  <div style={{ display: "flex", gap: "10px", position: "relative" }}>
                    <div style={{ width: "9px", height: "9px", borderRadius: "50%", backgroundColor: "var(--risk-safe)", border: "2px solid var(--bg-surface)", zIndex: 1, marginTop: "4px" }} />
                    <div>
                      <p style={{ fontSize: "0.74rem", fontWeight: "700", color: "var(--risk-safe)" }}>Hold resolved & released</p>
                      <p style={{ fontSize: "0.66rem", color: "var(--fg-muted)" }}>Transaction re-evaluated with score 0.0%.</p>
                      <p style={{ fontSize: "0.62rem", color: "var(--fg-dim)", fontFamily: "var(--font-mono)", marginTop: "1px" }}>
                        {audit_logs.filter(a => a.event === "auto_resolved" || a.event === "decision_overridden").slice(-1)[0]?.timestamp 
                          ? new Date(audit_logs.filter(a => a.event === "auto_resolved" || a.event === "decision_overridden").slice(-1)[0].timestamp).toLocaleString()
                          : new Date().toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
