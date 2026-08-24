"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../context/AuthContext";
import NetworkVisualizer from "../../../components/NetworkVisualizer";
import { Shield, ShieldAlert, Cpu, CornerDownRight, FileText, CheckCircle2, AlertOctagon, HelpCircle } from "lucide-react";

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
    
    fetch(`http://localhost:8000/api/v1/transactions/${id}/investigation`, {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error("Unable to load investigation data. Please retry.");
        return res.json();
      })
      .then(resData => {
        setData(resData);
        setErrorMsg(null);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setErrorMsg("Unable to load investigation data. Please retry.");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchDetails();
  }, [id, token]);

  const handleOverrideSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const response = await fetch(`http://localhost:8000/api/v1/transactions/${id}/resolve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          action: overrideAction,
          notes: overrideNotes
        })
      });

      if (response.ok) {
        setOverrideNotes("");
        fetchDetails(); // Reload state
      } else {
        const err = await response.json();
        alert(err.detail || "Failed to submit analyst decision override.");
      }
    } catch (err) {
      alert("Error submitting analyst decision override.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh", color: "var(--accent)" }}>
        <p style={{ fontWeight: "600" }}>Retrieving risk metrics & relationship graphs...</p>
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className="glass-card" style={{ maxWidth: "500px", margin: "40px auto", border: "1px solid var(--danger)", textAlign: "center" }}>
        <AlertOctagon size={40} color="var(--danger)" style={{ marginBottom: "15px" }} />
        <h2 style={{ color: "var(--danger)" }}>Load Failed</h2>
        <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", margin: "10px 0 20px" }}>{errorMsg}</p>
        <button onClick={() => { setLoading(true); fetchDetails(); }}>Retry Connection</button>
      </div>
    );
  }

  if (!data) {
    return <div style={{ color: "var(--danger)", padding: "20px" }}>Transaction record not found in system.</div>;
  }

  const { transaction, assessment, reasoning_steps, memories } = data;

  // Deriving risk level & color coding
  let riskLevel = "LOW";
  let scoreColor = "var(--success)";
  let scoreBg = "rgba(16, 185, 129, 0.15)";
  let recommendedAction = "APPROVE";

  if (transaction.risk_score >= 75.0) {
    riskLevel = "HIGH";
    scoreColor = "var(--danger)";
    scoreBg = "rgba(239, 68, 68, 0.15)";
    recommendedAction = "ESCALATE";
  } else if (transaction.risk_score >= 40.0) {
    riskLevel = "MEDIUM";
    scoreColor = "var(--warning)";
    scoreBg = "rgba(245, 158, 11, 0.15)";
    recommendedAction = "MONITOR";
  }

  // Derive explicit risk flags for Section 2
  const riskFlags = [];
  if (transaction.amount > 500000.0) {
    riskFlags.push({
      title: "HIGH VALUE LIMIT EXCEEDED",
      description: `Transaction amount (${transaction.currency} ${transaction.amount.toLocaleString()}) exceeds the soft limit threshold of 500,000.`
    });
  }
  if (transaction.billing_country !== transaction.card_country) {
    riskFlags.push({
      title: "LOCATION MISMATCH",
      description: `Card origin country (${transaction.card_country}) differs from billing destination (${transaction.billing_country}).`
    });
  }
  if (!transaction.card_present && transaction.amount > 50000.0) {
    riskFlags.push({
      title: "HIGH VALUE CARD-NOT-PRESENT (CNP)",
      description: "Card-Not-Present transaction amount exceeds the security verification limit of 50,000."
    });
  }
  
  // Find policy memory
  const policyMemory = memories.find(m => m.agent_name === "Policy Agent" || m.agent_name.includes("Policy"));

  return (
    <div>
      {/* HUD Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "30px", borderBottom: "1px solid var(--card-border)", paddingBottom: "20px" }}>
        <div>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "1px" }}>Risk Investigation</span>
          <h1 style={{ margin: "5px 0 10px", fontSize: "2rem" }}>Transaction ID: {transaction.transaction_id}</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
            Ingested: {new Date(transaction.timestamp).toLocaleString()} • DB Identifier: {transaction.id}
          </p>
        </div>
        
        <div style={{ display: "flex", gap: "15px", alignItems: "center" }}>
          <div style={{ textAlign: "center", padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--card-border)", backgroundColor: "rgba(0,0,0,0.2)" }}>
            <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase" }}>Risk Level</p>
            <p style={{ fontSize: "1.1rem", fontWeight: "700", color: scoreColor, marginTop: "2px" }}>{riskLevel}</p>
          </div>
          
          <div style={{ textAlign: "center", padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--card-border)", backgroundColor: "rgba(0,0,0,0.2)" }}>
            <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase" }}>Recommended Action</p>
            <p style={{ fontSize: "1.1rem", fontWeight: "700", color: scoreColor, marginTop: "2px" }}>{recommendedAction}</p>
          </div>

          <div style={{
            padding: "10px 20px",
            borderRadius: "8px",
            backgroundColor: scoreBg,
            border: `1px solid ${scoreColor}`,
            textAlign: "center"
          }}>
            <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Risk Score</p>
            <p style={{ fontSize: "1.6rem", fontWeight: "800", color: scoreColor }}>{transaction.risk_score.toFixed(0)}%</p>
          </div>
        </div>
      </div>

      {/* Grid: Properties Summary & Flagged Reasons */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px", marginBottom: "30px" }}>
        
        {/* Section 1: Transaction Summary */}
        <div className="glass-card">
          <h2>Transaction Summary</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", fontSize: "0.85rem", marginTop: "15px" }}>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Amount</p>
              <strong style={{ fontSize: "1.05rem" }}>{transaction.currency} {transaction.amount.toLocaleString()}</strong>
            </div>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Customer Account</p>
              <strong>{transaction.user_id}</strong>
            </div>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Card Origin</p>
              <strong>{transaction.card_country}</strong>
            </div>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Billing Origin</p>
              <strong>{transaction.billing_country}</strong>
            </div>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>IP Address</p>
              <strong>{transaction.ip_address}</strong>
            </div>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Transaction Channel</p>
              <strong>{transaction.card_present ? "Card Present" : "Card Not Present (CNP)"}</strong>
            </div>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Merchant ID</p>
              <strong>{transaction.merchant_id}</strong>
            </div>
            <div>
              <p style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>Merchant Category</p>
              <strong>{transaction.merchant_category}</strong>
            </div>
          </div>
        </div>

        {/* Section 2: Why was this transaction flagged? */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column" }}>
          <h2>Why was this transaction flagged?</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "15px", flexGrow: 1, overflowY: "auto" }}>
            {riskFlags.length === 0 ? (
              <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", fontStyle: "italic" }}>No immediate rule breaches detected.</p>
            ) : (
              riskFlags.map((flag, idx) => (
                <div key={idx} style={{ padding: "10px 14px", borderLeft: "3px solid var(--danger)", backgroundColor: "rgba(239, 68, 68, 0.05)", borderRadius: "0 6px 6px 0" }}>
                  <p style={{ fontSize: "0.8rem", fontWeight: "700", color: "var(--danger)" }}>{flag.title}</p>
                  <p style={{ fontSize: "0.75rem", color: "var(--foreground)", marginTop: "3px", lineHeight: "1.3" }}>{flag.description}</p>
                </div>
              ))
            )}
            {/* Velocity/Behavior Indicator */}
            {assessment && assessment.rule_score > 0 && (
              <div style={{ padding: "10px 14px", borderLeft: "3px solid var(--warning)", backgroundColor: "rgba(245, 158, 11, 0.05)", borderRadius: "0 6px 6px 0" }}>
                <p style={{ fontSize: "0.8rem", fontWeight: "700", color: "var(--warning)" }}>VELOCITY OR HISTORICAL DEVIATION</p>
                <p style={{ fontSize: "0.75rem", color: "var(--foreground)", marginTop: "3px", lineHeight: "1.3" }}>
                  Behavioral analysis flagged velocity checks or spending deviations exceeding historical account baseline averages.
                </p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Grid: Score Breakdown & Agent Console */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.8fr", gap: "30px", marginBottom: "30px" }}>
        
        {/* Section 3: Risk Score Breakdown */}
        <div className="glass-card">
          <h2>Risk Score Breakdown</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: "15px" }}>
            The overall Risk Score is computed deterministically using standard weighted metrics:
          </p>
          
          {assessment && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.85rem" }}>
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span>ML Anomaly Score <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>(Weight: 35%)</span></span>
                  <strong>{assessment.ml_score.toFixed(0)}%</strong>
                </div>
                <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                  <div style={{ width: `${assessment.ml_score}%`, height: "100%", backgroundColor: "var(--accent)" }}></div>
                </div>
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span>Rules & Behavior Score <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>(Weight: 20%)</span></span>
                  <strong>{assessment.rule_score.toFixed(0)}%</strong>
                </div>
                <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                  <div style={{ width: `${assessment.rule_score}%`, height: "100%", backgroundColor: "var(--warning)" }}></div>
                </div>
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span>Graph Overlap Score <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>(Weight: 30%)</span></span>
                  <strong>{assessment.graph_score.toFixed(0)}%</strong>
                </div>
                <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                  <div style={{ width: `${assessment.graph_score}%`, height: "100%", backgroundColor: "#a855f7" }}></div>
                </div>
              </div>

              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                  <span>Policy Compliance Score <span style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>(Weight: 15%)</span></span>
                  <strong>{assessment.policy_score.toFixed(0)}%</strong>
                </div>
                <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                  <div style={{ width: `${assessment.policy_score}%`, height: "100%", backgroundColor: "var(--danger)" }}></div>
                </div>
              </div>

              <div style={{ marginTop: "15px", padding: "10px", borderRadius: "6px", backgroundColor: "rgba(255, 255, 255, 0.02)", border: "1px solid var(--card-border)" }}>
                <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", lineHeight: "1.3" }}>
                  ℹ️ <strong>Deterministic Logic:</strong> The overall numeric score is computed by applying hardcoded weights. The LLM is used to synthesize explanation summaries for analysts, not to determine or alter scores.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Section 4: Risk Evidence (Agent Findings) */}
        <div className="glass-card">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "15px" }}>
            <Cpu size={20} color="var(--accent)" />
            <h2>Risk Evidence (Agent Findings)</h2>
          </div>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "15px", maxHeight: "290px", overflowY: "auto", paddingRight: "5px" }}>
            {memories.map((mem, index) => {
              const isActionOrDecision = mem.agent_name.includes("Decision") || mem.agent_name.includes("Action");
              const agentSeverity = (100.0 - mem.confidence).toFixed(0);
              
              return (
                <div key={index} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "var(--accent)" }}>{mem.agent_name}</span>
                    {!isActionOrDecision && (
                      <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)" }}>
                        Severity Contribution: <span style={{ color: "#fff" }}>{agentSeverity}%</span>
                      </span>
                    )}
                  </div>
                  <p style={{ fontSize: "0.8rem", color: "#f4f4f5", lineHeight: "1.35" }}>{mem.reasoning}</p>
                  {mem.evidence && (
                    <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
                      <CornerDownRight size={14} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                      <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic", lineHeight: "1.3" }}>
                        Evidence: {mem.evidence}
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

      </div>

      {/* Grid: Graph Visualizer & Policy Evidence */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "30px", marginBottom: "30px" }}>
        
        {/* Section 5: Knowledge Graph */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <h2>Knowledge Graph (Topological Walk)</h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: "15px" }}>
              Identifies hardware sharing, common billing channels, and overlapping connections.
            </p>
          </div>
          <NetworkVisualizer userId={transaction.user_id} token={token} />
        </div>

        {/* Section 6: Policy Evidence */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column" }}>
          <h2>Policy Evidence</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: "15px" }}>
            Regulatory manual segments retrieved dynamically from compliance knowledgebase base (RAG).
          </p>
          
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", flexGrow: 1, overflowY: "auto", maxHeight: "250px" }}>
            {policyMemory && policyMemory.evidence && policyMemory.evidence !== "No active regulatory rules breached. RAG returned empty search index." ? (
              <div style={{ padding: "12px", border: "1px solid var(--card-border)", borderRadius: "8px", backgroundColor: "rgba(0,0,0,0.15)", fontSize: "0.8rem", lineHeight: "1.4" }}>
                <p style={{ fontWeight: "700", color: "var(--accent)", marginBottom: "5px" }}>Compliance Check Output:</p>
                <p style={{ fontStyle: "italic", color: "#e4e4e7" }}>{policyMemory.evidence}</p>
                <div style={{ marginTop: "10px", fontSize: "0.7rem", color: "var(--text-muted)", display: "flex", alignItems: "center", gap: "5px" }}>
                  <FileText size={12} />
                  <span>Grounding source: compliance manual databases</span>
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", flexGrow: 1, color: "var(--text-muted)", minHeight: "150px" }}>
                <HelpCircle size={28} style={{ marginBottom: "10px" }} />
                <p style={{ fontSize: "0.8rem" }}>No compliance citations triggered</p>
                <p style={{ fontSize: "0.7rem", marginTop: "2px" }}>RAG search verified no active regulatory rules were violated.</p>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* Grid: AI Explanation & Analyst Review */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.8fr", gap: "30px", marginBottom: "30px" }}>
        
        {/* Section 7: AI Explanation */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
            <FileText size={20} color="var(--accent)" />
            <h2>AI Explanation</h2>
          </div>
          <div style={{
            backgroundColor: "rgba(0,0,0,0.3)",
            border: "1px solid var(--card-border)",
            borderRadius: "6px",
            padding: "14px",
            fontSize: "0.8rem",
            lineHeight: "1.45",
            flexGrow: 1,
            overflowY: "auto",
            maxHeight: "240px",
            whiteSpace: "pre-wrap"
          }}>
            {assessment && assessment.explanation ? assessment.explanation : "Synthesizing RAG compliance grounding trace..."}
          </div>
        </div>

        {/* Section 8: Analyst Review */}
        <div className="glass-card" style={{ border: transaction.status === "Escalated" ? "1px solid rgba(245, 158, 11, 0.4)" : "1px solid var(--card-border)", backgroundColor: transaction.status === "Escalated" ? "rgba(245, 158, 11, 0.01)" : "rgba(0,0,0,0.1)" }}>
          <h2 style={{ color: transaction.status === "Escalated" ? "var(--warning)" : "var(--foreground)" }}>
            Analyst Review
          </h2>
          <p style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginBottom: "15px" }}>
            Human-in-the-loop compliance override. Audit trail notes are logged on override submission.
          </p>
          
          {transaction.status === "Escalated" ? (
            <form onSubmit={handleOverrideSubmit} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
              <div style={{ display: "flex", gap: "20px" }}>
                <div style={{ width: "200px" }}>
                  <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "600", textTransform: "uppercase" }}>
                    Select Action
                  </label>
                  <select value={overrideAction} onChange={(e) => setOverrideAction(e.target.value)}>
                    <option value="Approve">Approve Payment</option>
                    <option value="Block">Block/Decline Payment</option>
                  </select>
                </div>
                
                <div style={{ flexGrow: 1 }}>
                  <label style={{ display: "block", fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "600", textTransform: "uppercase" }}>
                    Justification Notes
                  </label>
                  <input
                    type="text"
                    value={overrideNotes}
                    onChange={(e) => setOverrideNotes(e.target.value)}
                    placeholder="Enter compliance justification notes..."
                    required
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "5px" }}>
                <button type="submit" disabled={submitting}>
                  {submitting ? "Submitting Decision..." : "Commit Analyst Decision"}
                </button>
              </div>
            </form>
          ) : (
            <div style={{ padding: "20px", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.03)", backgroundColor: "rgba(0,0,0,0.2)", display: "flex", alignItems: "center", gap: "10px" }}>
              <CheckCircle2 color="var(--success)" size={20} />
              <div>
                <p style={{ fontSize: "0.85rem", fontWeight: "700" }}>Analyst Action Executed</p>
                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                  This transaction has already been resolved and does not require further analyst review. Current State: <strong>{transaction.status}</strong>.
                </p>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
