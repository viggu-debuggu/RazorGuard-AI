"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useRouter } from "next/navigation";
import { ShieldCheck, AlertTriangle, UserX, CreditCard, ChevronRight } from "lucide-react";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

const MOCK_CHART_DATA = [
  { name: "08:00", volume: 140, risk: 2 },
  { name: "10:00", volume: 220, risk: 4 },
  { name: "12:00", volume: 380, risk: 12 },
  { name: "14:00", volume: 310, risk: 8 },
  { name: "16:00", volume: 490, risk: 19 },
  { name: "18:00", volume: 410, risk: 14 },
  { name: "20:00", volume: 290, risk: 5 }
];

export default function DashboardHome() {
  const { token } = useAuth();
  const [escalations, setEscalations] = useState([]);
  const [metrics, setMetrics] = useState({
    total: 1280,
    approved: 1154,
    flagged: 84,
    blocked: 42
  });
  const router = useRouter();

  useEffect(() => {
    if (!token) return;
    
    // Fetch escalated items for the quick queue summary
    fetch("http://localhost:8000/api/v1/transactions?status=Escalated", {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setEscalations(data.slice(0, 5));
          // Dynamically override metrics counts based on live database values for demo feedback
          setMetrics(prev => ({
            ...prev,
            flagged: data.length
          }));
        }
      })
      .catch(err => console.error("Failed to load metrics", err));
  }, [token]);

  return (
    <div>
      <h1>Risk Command Center</h1>
      
      {/* Metrics Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", marginBottom: "30px" }}>
        
        <div className="glass-card" style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <div style={{ padding: "12px", borderRadius: "10px", backgroundColor: "rgba(56, 189, 248, 0.15)", color: "var(--accent)" }}>
            <CreditCard size={24} />
          </div>
          <div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", fontWeight: "600", textTransform: "uppercase" }}>Processed Payments</p>
            <p style={{ fontSize: "1.6rem", fontWeight: "700", marginTop: "2px" }}>{metrics.total}</p>
          </div>
        </div>

        <div className="glass-card" style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <div style={{ padding: "12px", borderRadius: "10px", backgroundColor: "rgba(16, 185, 129, 0.15)", color: "var(--success)" }}>
            <ShieldCheck size={24} />
          </div>
          <div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", fontWeight: "600", textTransform: "uppercase" }}>Auto Approved</p>
            <p style={{ fontSize: "1.6rem", fontWeight: "700", marginTop: "2px" }}>{metrics.approved}</p>
          </div>
        </div>

        <div className="glass-card" style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <div style={{ padding: "12px", borderRadius: "10px", backgroundColor: "rgba(245, 158, 11, 0.15)", color: "var(--warning)" }}>
            <AlertTriangle size={24} />
          </div>
          <div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", fontWeight: "600", textTransform: "uppercase" }}>Pending Review</p>
            <p style={{ fontSize: "1.6rem", fontWeight: "700", marginTop: "2px" }}>{metrics.flagged}</p>
          </div>
        </div>

        <div className="glass-card" style={{ display: "flex", alignItems: "center", gap: "15px" }}>
          <div style={{ padding: "12px", borderRadius: "10px", backgroundColor: "rgba(239, 68, 68, 0.15)", color: "var(--danger)" }}>
            <UserX size={24} />
          </div>
          <div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.8rem", fontWeight: "600", textTransform: "uppercase" }}>Blocked Fraud</p>
            <p style={{ fontSize: "1.6rem", fontWeight: "700", marginTop: "2px" }}>{metrics.blocked}</p>
          </div>
        </div>

      </div>

      {/* Chart and Priority Row */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "30px", marginBottom: "30px" }}>
        
        {/* Chart Card */}
        <div className="glass-card">
          <h2 style={{ marginBottom: "20px" }}>Risk Volume Matrix</h2>
          <div style={{ width: "100%", height: "260px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={MOCK_CHART_DATA}>
                <defs>
                  <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--accent)" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--danger)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--danger)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} />
                <YAxis stroke="var(--text-muted)" fontSize={12} />
                <Tooltip contentStyle={{ backgroundColor: "#18181b", borderColor: "var(--card-border)" }} />
                <Area type="monotone" dataKey="volume" stroke="var(--accent)" fillOpacity={1} fill="url(#colorVolume)" name="Payment Volume" />
                <Area type="monotone" dataKey="risk" stroke="var(--danger)" fillOpacity={1} fill="url(#colorRisk)" name="Flagged Risk Events" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Priority Escalations Panel */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column" }}>
          <h2>High Priority review</h2>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", flexGrow: 1, overflowY: "auto" }}>
            {escalations.length === 0 ? (
              <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", height: "100%", color: "var(--text-muted)" }}>
                <p style={{ fontSize: "0.85rem" }}>Clear Queue</p>
                <p style={{ fontSize: "0.75rem", marginTop: "4px" }}>No escalated transactions on hold.</p>
              </div>
            ) : (
              escalations.map((tx) => (
                <div
                  key={tx.id}
                  onClick={() => router.push(`/transactions/${tx.id}`)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 14px",
                    backgroundColor: "rgba(9, 9, 11, 0.4)",
                    border: "1px solid var(--card-border)",
                    borderRadius: "8px",
                    cursor: "pointer",
                    transition: "border-color 0.2s"
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.borderColor = "var(--accent)"}
                  onMouseLeave={(e) => e.currentTarget.style.borderColor = "var(--card-border)"}
                >
                  <div>
                    <p style={{ fontSize: "0.85rem", fontWeight: "600" }}>{tx.transaction_id}</p>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                      {tx.currency} {tx.amount.toLocaleString()} • User: {tx.user_id}
                    </p>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{
                      fontSize: "0.8rem",
                      fontWeight: "700",
                      color: "var(--danger)"
                    }}>
                      {tx.risk_score.toFixed(0)}%
                    </span>
                    <ChevronRight size={16} color="var(--text-muted)" />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
