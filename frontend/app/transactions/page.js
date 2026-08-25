"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";

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

function statusBadgeClass(status) {
  const map = {
    Approved: "badge badge-approved",
    Flagged: "badge badge-warn",
    Escalated: "badge badge-escalated",
    Blocked: "badge badge-blocked",
    Pending: "badge badge-warn",
  };
  return map[status] || "badge badge-neutral";
}

export default function TransactionsQueue() {
  const { token } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const fetchTransactions = () => {
    if (!token) return;
    let url = "http://localhost:8000/api/v1/transactions?";
    if (statusFilter) url += `status=${statusFilter}&`;
    if (minScore > 0) url += `min_score=${minScore}&`;

    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) setTransactions(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    setLoading(true);
    fetchTransactions();
    const interval = setInterval(fetchTransactions, 6000);
    return () => clearInterval(interval);
  }, [token, statusFilter, minScore]);

  const filtered = transactions.filter(
    (tx) =>
      tx.transaction_id.toLowerCase().includes(search.toLowerCase()) ||
      tx.user_id.toLowerCase().includes(search.toLowerCase()) ||
      tx.merchant_id.toLowerCase().includes(search.toLowerCase())
  );

  const escalatedCount = transactions.filter((t) => t.status === "Escalated").length;
  const flaggedCount = transactions.filter((t) => t.status !== "Approved" && t.status !== "Blocked").length;

  return (
    <div>
      {/* Page header */}
      <div className="page-header">
        <h1 className="page-title">Investigation Queue</h1>
        <span className="page-subtitle">
          {loading ? "Loading…" : `${flaggedCount} flagged · ${escalatedCount} escalated`}
        </span>
      </div>

      {/* Filter bar — compact strip, no glass card */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          alignItems: "center",
          marginBottom: "14px",
          padding: "10px 14px",
          borderBottom: "1px solid var(--border)",
          backgroundColor: "var(--bg-surface)",
          borderRadius: "4px 4px 0 0",
        }}
      >
        {/* Search */}
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter by transaction ID, customer, merchant…"
          style={{ width: "280px", padding: "6px 10px", fontSize: "0.78rem" }}
        />

        {/* Status filter */}
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ width: "140px", padding: "6px 10px", fontSize: "0.78rem" }}
        >
          <option value="">All Statuses</option>
          <option value="Pending">Pending</option>
          <option value="Approved">Approved</option>
          <option value="Blocked">Blocked</option>
          <option value="Escalated">Escalated</option>
        </select>

        {/* Risk threshold */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "0.72rem", color: "var(--fg-muted)", whiteSpace: "nowrap" }}>
            Min risk:{" "}
            <span
              className="tabular"
              style={{ color: minScore >= 75 ? "var(--risk-high)" : minScore >= 40 ? "var(--risk-warn)" : "var(--fg)", fontWeight: "700" }}
            >
              {minScore}%
            </span>
          </span>
          <input
            type="range"
            min="0"
            max="100"
            value={minScore}
            onChange={(e) => setMinScore(parseInt(e.target.value))}
            style={{ width: "100px", height: "3px", padding: 0, cursor: "pointer" }}
          />
        </div>

        <span style={{ marginLeft: "auto", fontSize: "0.72rem", color: "var(--fg-dim)" }}>
          {filtered.length} result{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Queue Table */}
      <div className="panel" style={{ padding: "0", borderRadius: "0 0 4px 4px", borderTop: "none" }}>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Time</th>
                <th>Customer</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th>Merchant</th>
                <th style={{ textAlign: "right" }}>Risk Score</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    {Array.from({ length: 8 }).map((_, j) => (
                      <td key={j}>
                        <div className="skeleton" style={{ height: "10px", width: j === 7 ? "40px" : "80%" }} />
                      </td>
                    ))}
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td
                    colSpan="8"
                    style={{
                      textAlign: "center",
                      padding: "40px",
                      color: "var(--fg-muted)",
                      fontSize: "0.82rem",
                    }}
                  >
                    No transactions match these filters — try widening the risk threshold or clearing the status filter.
                  </td>
                </tr>
              ) : (
                filtered.map((tx) => {
                  const riskColor = getRiskColor(tx.risk_score);
                  return (
                    <tr key={tx.id}>
                      <td>
                        <span
                          className="tabular"
                          style={{ fontWeight: "600", fontSize: "0.78rem" }}
                        >
                          {tx.transaction_id}
                        </span>
                      </td>
                      <td>
                        <span
                          title={new Date(tx.timestamp).toLocaleString()}
                          style={{ color: "var(--fg-muted)", fontSize: "0.75rem", cursor: "default" }}
                        >
                          {relativeTime(tx.timestamp)}
                        </span>
                      </td>
                      <td style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>
                        {tx.user_id}
                      </td>
                      <td className="num">
                        <span style={{ fontSize: "0.82rem" }}>
                          {tx.currency}{" "}
                          {tx.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </span>
                      </td>
                      <td style={{ color: "var(--fg-muted)", fontSize: "0.78rem" }}>
                        {tx.merchant_category}
                      </td>
                      <td className="num">
                        <div className="risk-inline" style={{ justifyContent: "flex-end" }}>
                          <div className="risk-inline-bar">
                            <div
                              className="risk-inline-fill"
                              style={{ width: `${tx.risk_score}%`, backgroundColor: riskColor }}
                            />
                          </div>
                          <span
                            className="tabular"
                            style={{ fontSize: "0.82rem", fontWeight: "700", color: riskColor, minWidth: "32px" }}
                          >
                            {tx.risk_score.toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className={statusBadgeClass(tx.status)}>{tx.status}</span>
                      </td>
                      <td>
                        <span
                          className="text-action"
                          onClick={() => router.push(`/transactions/${tx.id}`)}
                        >
                          Open →
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
