"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "../../../context/AuthContext";
import NetworkVisualizer from "../../../components/NetworkVisualizer";
import { Shield, ShieldAlert, Cpu, CornerDownRight, FileText, CheckCircle2, XCircle } from "lucide-react";

export default function TransactionDetail() {
  const { id } = useParams();
  const { token } = useAuth();
  const router = useRouter();
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [overrideAction, setOverrideAction] = useState("Approve");
  const [overrideNotes, setOverrideNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchDetails = () => {
    if (!token || !id) return;
    
    fetch(`http://localhost:8000/api/v1/transactions/${id}/investigation`, {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(res => {
        if (!res.ok) throw new Error("Could not retrieve investigation details.");
        return res.json();
      })
      .then(resData => {
        setData(resData);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
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
        alert(err.detail || "Failed to submit decision override.");
      }
    } catch (err) {
      alert("Error submitting override.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div style={{ color: "var(--accent)", padding: "20px" }}>Loading risk metrics...</div>;
  }

  if (!data) {
    return <div style={{ color: "var(--danger)", padding: "20px" }}>Investigation details not found.</div>;
  }

  const { transaction, assessment, reasoning_steps, memories } = data;

  // Color mappings
  let scoreColor = "var(--success)";
  let scoreBg = "rgba(16, 185, 129, 0.15)";
  if (transaction.risk_score >= 75.0) {
    scoreColor = "var(--danger)";
    scoreBg = "rgba(239, 68, 68, 0.15)";
  } else if (transaction.risk_score >= 40.0) {
    scoreColor = "var(--warning)";
    scoreBg = "rgba(245, 158, 11, 0.15)";
  }

  return (
    <div>
      {/* Header Info */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "30px" }}>
        <div>
          <h1>Transaction Investigation</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem", marginTop: "-15px" }}>
            ID: <strong style={{ color: "#fff" }}>{transaction.transaction_id}</strong> • Ingested: {new Date(transaction.timestamp).toLocaleString()}
          </p>
        </div>
        <div style={{ display: "flex", gap: "15px", alignItems: "center" }}>
          <div style={{
            padding: "8px 16px",
            borderRadius: "8px",
            backgroundColor: scoreBg,
            border: `1px solid ${scoreColor}`,
            textAlign: "center"
          }}>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Risk Score</p>
            <p style={{ fontSize: "1.4rem", fontWeight: "800", color: scoreColor }}>{transaction.risk_score.toFixed(0)}%</p>
          </div>
          <span className={`status-badge status-${transaction.status.toLowerCase()}`} style={{ padding: "8px 16px", fontSize: "0.85rem" }}>
            {transaction.status}
          </span>
        </div>
      </div>

      {/* Main HUD layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.8fr", gap: "30px", marginBottom: "30px" }}>
        
        {/* Left Side: Metadata Card */}
        <div style={{ display: "flex", flexDirection: "column", gap: "30px" }}>
          
          {/* Metadata details */}
          <div className="glass-card">
            <h2 style={{ borderBottom: "1px solid var(--card-border)", paddingBottom: "10px", marginBottom: "15px" }}>Transaction Properties</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.85rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Amount</span>
                <strong style={{ fontSize: "1.0rem" }}>{transaction.currency} {transaction.amount.toLocaleString()}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Customer Account</span>
                <strong>{transaction.user_id}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Card Origin</span>
                <strong>{transaction.card_country}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Billing Origin</span>
                <strong>{transaction.billing_country}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>IP Address</span>
                <strong>{transaction.ip_address}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Card Present</span>
                <strong>{transaction.card_present ? "Yes" : "No (CNP)"}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Merchant ID</span>
                <strong>{transaction.merchant_id}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Merchant Category</span>
                <strong>{transaction.merchant_category}</strong>
              </div>
            </div>
          </div>

          {/* Core breakdown score chart */}
          {assessment && (
            <div className="glass-card">
              <h2 style={{ marginBottom: "15px" }}>Consensus Scores</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span>ML Centroid Model</span>
                    <strong>{assessment.ml_score.toFixed(0)}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${assessment.ml_score}%`, height: "100%", backgroundColor: "var(--accent)" }}></div>
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span>Heuristics & Velocity Rules</span>
                    <strong>{assessment.rule_score.toFixed(0)}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${assessment.rule_score}%`, height: "100%", backgroundColor: "var(--warning)" }}></div>
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span>KG Topological Overlap</span>
                    <strong>{assessment.graph_score.toFixed(0)}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${assessment.graph_score}%`, height: "100%", backgroundColor: "#a855f7" }}></div>
                  </div>
                </div>

                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "4px" }}>
                    <span>Policy compliance (RAG)</span>
                    <strong>{assessment.policy_score.toFixed(0)}%</strong>
                  </div>
                  <div style={{ width: "100%", height: "6px", backgroundColor: "#000", borderRadius: "3px", overflow: "hidden" }}>
                    <div style={{ width: `${assessment.policy_score}%`, height: "100%", backgroundColor: "var(--danger)" }}></div>
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Right Side: Multi-Agent and Explanation Details */}
        <div style={{ display: "flex", flexDirection: "column", gap: "30px" }}>
          
          {/* Multi-Agent Console Trace */}
          <div className="glass-card">
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "15px" }}>
              <Cpu size={22} color="var(--accent)" />
              <h2>Multi-Agent reasoning console</h2>
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "15px", maxHeight: "300px", overflowY: "auto", paddingRight: "5px" }}>
              {memories.map((mem, index) => {
                let statusIcon = <CheckCircle2 size={16} color="var(--success)" />;
                if (mem.confidence < 50.0) statusIcon = <ShieldAlert size={16} color="var(--danger)" />;

                return (
                  <div key={index} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", paddingBottom: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "var(--accent)" }}>{mem.agent_name}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                        {statusIcon}
                        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Confidence: {mem.confidence.toFixed(0)}%</span>
                      </div>
                    </div>
                    <p style={{ fontSize: "0.8rem", color: "#f4f4f5", lineHeight: "1.3" }}>{mem.reasoning}</p>
                    {mem.evidence && (
                      <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
                        <CornerDownRight size={14} color="var(--text-muted)" />
                        <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                          Evidence: {mem.evidence}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* SVG Graph Vis & Explainable Text Row */}
          <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1.8fr", gap: "25px" }}>
            
            {/* SVG Relationship Graph */}
            <div className="glass-card" style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
              <h2 style={{ fontSize: "1.0rem", marginBottom: "10px", textAlign: "center" }}>Linked Entities (KG Walk)</h2>
              <NetworkVisualizer userId={transaction.user_id} token={token} />
            </div>

            {/* RAG Explainable decision markdown output */}
            <div className="glass-card" style={{ display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                <FileText size={18} color="var(--accent)" />
                <h2 style={{ fontSize: "1.0rem", marginBottom: 0 }}>Grounded Explanation</h2>
              </div>
              <div style={{
                backgroundColor: "rgba(0,0,0,0.3)",
                border: "1px solid var(--card-border)",
                borderRadius: "6px",
                padding: "12px",
                fontSize: "0.8rem",
                lineHeight: "1.4",
                flexGrow: 1,
                overflowY: "auto",
                maxHeight: "220px",
                whiteSpace: "pre-wrap"
              }}>
                {assessment && assessment.explanation ? assessment.explanation : "Compiling RAG grounding briefs..."}
              </div>
            </div>

          </div>

          {/* Analyst decision override box */}
          {transaction.status === "Escalated" && (
            <div className="glass-card" style={{ border: "1px solid rgba(245, 158, 11, 0.4)", backgroundColor: "rgba(245, 158, 11, 0.03)" }}>
              <h2 style={{ fontSize: "1.1rem", marginBottom: "12px", color: "var(--warning)" }}>
                Analyst Intervention Required
              </h2>
              
              <form onSubmit={handleOverrideSubmit} style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                <div style={{ display: "flex", gap: "20px" }}>
                  <div style={{ width: "200px" }}>
                    <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "4px" }}>
                      Take Action
                    </label>
                    <select value={overrideAction} onChange={(e) => setOverrideAction(e.target.value)}>
                      <option value="Approve">Approve Payment</option>
                      <option value="Block">Block/Decline Payment</option>
                    </select>
                  </div>
                  
                  <div style={{ flexGrow: 1 }}>
                    <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "4px" }}>
                      Justification Notes
                    </label>
                    <input
                      type="text"
                      value={overrideNotes}
                      onChange={(e) => setOverrideNotes(e.target.value)}
                      placeholder="Add compliance notes or override reason..."
                      required
                    />
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button type="submit" disabled={submitting}>
                    {submitting ? "Submitting Override..." : "Submit Override Action"}
                  </button>
                </div>
              </form>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
