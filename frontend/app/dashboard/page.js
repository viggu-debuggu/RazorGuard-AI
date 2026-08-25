"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { API_URL } from "../../lib/api";

const MOCK_CHART_DATA = [
  { time: "08:00", volume: 140, risk: 2 },
  { time: "10:00", volume: 220, risk: 4 },
  { time: "12:00", volume: 380, risk: 12 },
  { time: "14:00", volume: 310, risk: 8 },
  { time: "16:00", volume: 490, risk: 19 },
  { time: "18:00", volume: 410, risk: 14 },
  { time: "20:00", volume: 290, risk: 5 },
];

function relativeTime(isoString) {
  const diff = Date.now() - new Date(isoString).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function getRiskColor(score) {
  if (score >= 75) return "var(--risk-high)";
  if (score >= 40) return "var(--risk-warn)";
  return "var(--risk-safe)";
}

function MetricsSkeleton() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px", marginBottom: "20px" }}>
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="panel skeleton" style={{ height: "64px" }} />
      ))}
    </div>
  );
}

export default function DashboardHome() {
  const { token } = useAuth();
  const [escalations, setEscalations] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [efficiency, setEfficiency] = useState(null);
  const [loadingEfficiency, setLoadingEfficiency] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!token) return;

    fetch(`${API_URL}/api/v1/transactions?status=Escalated`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setEscalations(data.slice(0, 6));
          setMetrics({
            total: 1280,
            approved: 1154,
            flagged: data.length,
            blocked: 42,
          });
        }
        setLoadingMetrics(false);
      })
      .catch(() => {
        setMetrics({ total: 1280, approved: 1154, flagged: 0, blocked: 42 });
        setLoadingMetrics(false);
      });

    fetch(`${API_URL}/api/v1/transactions/metrics/efficiency`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        setEfficiency(data);
        setLoadingEfficiency(false);
      })
      .catch(() => {
        setLoadingEfficiency(false);
      });
  }, [token]);

  const escalatedCount = escalations.length;
  const subtitleText = loadingMetrics
    ? "Loading queue…"
    : escalatedCount === 0
    ? "Queue clear — no transactions awaiting override"
    : `${escalatedCount} transaction${escalatedCount !== 1 ? "s" : ""} awaiting analyst override`;

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Investigation Overview</h1>
        <span className="page-subtitle">{subtitleText}</span>
      </div>

      {/* Metrics Row */}
      {loadingMetrics ? (
        <MetricsSkeleton />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "10px",
            marginBottom: "20px",
          }}
        >
          {[
            { label: "Processed Today", value: metrics.total, color: "var(--fg)" },
            { label: "Auto-Approved", value: metrics.approved, color: "var(--risk-safe)" },
            { label: "Awaiting Review", value: metrics.flagged, color: "var(--risk-warn)" },
            { label: "Blocked", value: metrics.blocked, color: "var(--risk-high)" },
          ].map(({ label, value, color }) => (
            <div key={label} className="panel" style={{ padding: "12px 14px" }}>
              <p
                style={{
                  fontSize: "0.68rem",
                  fontWeight: "600",
                  textTransform: "uppercase",
                  letterSpacing: "0.07em",
                  color: "var(--fg-muted)",
                  marginBottom: "6px",
                }}
              >
                {label}
              </p>
              <p
                className="display-num"
                style={{ fontSize: "1.8rem", fontWeight: 400, color, lineHeight: 1 }}
              >
                {value.toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Analyst Efficiency Metrics Row */}
      <h2 style={{ fontSize: "0.8rem", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--fg-muted)", marginBottom: "10px", marginTop: "16px" }}>
        Analyst Efficiency
      </h2>
      {loadingEfficiency || !efficiency ? (
        <MetricsSkeleton />
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(4, 1fr)",
            gap: "10px",
            marginBottom: "20px",
          }}
        >
          {[
            {
              label: "Avg. analyst time per case",
              value: `${efficiency.avg_analyst_review_minutes.toFixed(1)} min`,
              color: "var(--accent-text)",
            },
            {
              label: "Cases processed",
              value: efficiency.total_cases_processed.toLocaleString(),
              color: "var(--fg)",
            },
            {
              label: "Audit-ready decisions",
              value: `${efficiency.pct_decisions_with_justification.toFixed(0)}%`,
              color: "var(--risk-safe)",
            },
            {
              label: "AI investigation speed",
              value: `${efficiency.avg_investigation_time_seconds.toFixed(1)}s`,
              color: "var(--fg)",
            },
          ].map(({ label, value, color }) => (
            <div key={label} className="panel" style={{ padding: "12px 14px" }}>
              <p
                style={{
                  fontSize: "0.68rem",
                  fontWeight: "600",
                  textTransform: "uppercase",
                  letterSpacing: "0.07em",
                  color: "var(--fg-muted)",
                  marginBottom: "6px",
                }}
              >
                {label}
              </p>
              <p
                className="display-num"
                style={{ fontSize: "1.8rem", fontWeight: 400, color, lineHeight: 1 }}
              >
                {value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Chart + Escalation Queue */}
      <div
        style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}
      >
        {/* Sparkline Chart */}
        <div className="panel">
          <h2>Payment Volume vs. Risk Events</h2>
          <div style={{ width: "100%", height: "220px", marginTop: "8px" }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={MOCK_CHART_DATA} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="2 4" stroke="var(--border-subtle)" />
                <XAxis
                  dataKey="time"
                  stroke="var(--fg-dim)"
                  fontSize={10}
                  tick={{ fill: "var(--fg-muted)" }}
                />
                <YAxis
                  stroke="var(--fg-dim)"
                  fontSize={10}
                  tick={{ fill: "var(--fg-muted)" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--bg-surface)",
                    border: "1px solid var(--border)",
                    borderRadius: "3px",
                    fontSize: "0.75rem",
                    color: "var(--fg)",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="volume"
                  stroke="#5B7FD4"
                  strokeWidth={1.5}
                  dot={false}
                  name="Payment Volume"
                />
                <Line
                  type="monotone"
                  dataKey="risk"
                  stroke="var(--risk-high)"
                  strokeWidth={1.5}
                  dot={false}
                  name="Flagged Events"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: "flex", gap: "16px", marginTop: "10px" }}>
            <span style={{ fontSize: "0.7rem", color: "var(--fg-muted)", display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ display: "inline-block", width: "14px", height: "2px", background: "#5B7FD4" }} />
              Payment Volume
            </span>
            <span style={{ fontSize: "0.7rem", color: "var(--fg-muted)", display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ display: "inline-block", width: "14px", height: "2px", background: "var(--risk-high)" }} />
              Flagged Events
            </span>
          </div>
        </div>

        {/* Escalation Queue */}
        <div className="panel" style={{ display: "flex", flexDirection: "column" }}>
          <h2>Escalation Queue</h2>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "1px",
              flexGrow: 1,
              overflowY: "auto",
            }}
          >
            {escalations.length === 0 ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  alignItems: "center",
                  flexGrow: 1,
                  padding: "30px 0",
                  color: "var(--fg-dim)",
                  gap: "6px",
                }}
              >
                <span style={{ fontSize: "1.4rem" }}>—</span>
                <p style={{ fontSize: "0.78rem", color: "var(--fg-muted)" }}>Queue is clear</p>
                <p style={{ fontSize: "0.7rem", color: "var(--fg-dim)" }}>No escalations pending analyst review</p>
              </div>
            ) : (
              escalations.map((tx) => {
                const riskColor = getRiskColor(tx.risk_score);
                return (
                  <div
                    key={tx.id}
                    onClick={() => router.push(`/transactions/${tx.id}`)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "9px 10px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      borderBottom: "1px solid var(--border-subtle)",
                      transition: "background-color 0.1s",
                    }}
                    onMouseEnter={(e) =>
                      (e.currentTarget.style.backgroundColor = "var(--bg-raised)")
                    }
                    onMouseLeave={(e) =>
                      (e.currentTarget.style.backgroundColor = "transparent")
                    }
                  >
                    <div>
                      <p
                        style={{
                          fontFamily: "var(--font-mono)",
                          fontSize: "0.78rem",
                          fontWeight: "600",
                          color: "var(--fg)",
                        }}
                      >
                        {tx.transaction_id}
                      </p>
                      <p style={{ fontSize: "0.68rem", color: "var(--fg-muted)", marginTop: "2px" }}>
                        {tx.currency}{" "}
                        {tx.amount.toLocaleString("en-IN")} · Escalated{" "}
                        {relativeTime(tx.timestamp)}
                      </p>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div style={{ textAlign: "right" }}>
                        <p
                          className="tabular"
                          style={{ fontSize: "0.82rem", fontWeight: "700", color: riskColor }}
                        >
                          {tx.risk_score.toFixed(0)}%
                        </p>
                        <div className="risk-inline-bar" style={{ marginTop: "3px" }}>
                          <div
                            className="risk-inline-fill"
                            style={{ width: `${tx.risk_score}%`, backgroundColor: riskColor }}
                          />
                        </div>
                      </div>
                      <span style={{ color: "var(--fg-dim)", fontSize: "0.75rem" }}>→</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
