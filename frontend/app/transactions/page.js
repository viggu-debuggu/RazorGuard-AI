"use client";

import React, { useState, useEffect } from "react";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "next/navigation";
import { Search, Eye, Filter } from "lucide-react";

export default function TransactionsQueue() {
  const { token } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [minScore, setMinScore] = useState(0);
  const [search, setSearch] = useState("");
  const router = useRouter();

  const fetchTransactions = () => {
    if (!token) return;
    
    let url = "http://localhost:8000/api/v1/transactions?";
    if (statusFilter) url += `status=${statusFilter}&`;
    if (minScore > 0) url += `min_score=${minScore}&`;
    
    fetch(url, {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setTransactions(data);
        }
      })
      .catch(err => console.error("Failed to load queue", err));
  };

  useEffect(() => {
    fetchTransactions();
    // Poll queue list every 6 seconds
    const interval = setInterval(fetchTransactions, 6000);
    return () => clearInterval(interval);
  }, [token, statusFilter, minScore]);

  // Apply local text search filter
  const filteredTransactions = transactions.filter(tx => 
    tx.transaction_id.toLowerCase().includes(search.toLowerCase()) ||
    tx.user_id.toLowerCase().includes(search.toLowerCase()) ||
    tx.merchant_id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <h1>Transactions Queue</h1>

      {/* Filters Bar */}
      <div className="glass-card" style={{ display: "flex", flexWrap: "wrap", gap: "20px", alignItems: "center", marginBottom: "25px" }}>
        
        {/* Search */}
        <div style={{ flexGrow: 1, minWidth: "200px", position: "relative" }}>
          <Search size={18} color="var(--text-muted)" style={{ position: "absolute", left: "12px", top: "12px" }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transaction ID, customer, merchant..."
            style={{ paddingLeft: "38px" }}
          />
        </div>

        {/* Status Dropdown */}
        <div style={{ width: "160px", display: "flex", alignItems: "center", gap: "10px" }}>
          <Filter size={18} color="var(--text-muted)" />
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="Pending">Pending</option>
            <option value="Approved">Approved</option>
            <option value="Blocked">Blocked</option>
            <option value="Escalated">Escalated</option>
          </select>
        </div>

        {/* Risk Score Threshold */}
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", whiteSpace: "nowrap" }}>
            Min Risk: <strong>{minScore}%</strong>
          </span>
          <input
            type="range"
            min="0"
            max="100"
            value={minScore}
            onChange={(e) => setMinScore(parseInt(e.target.value))}
            style={{ width: "120px", height: "4px", padding: 0, cursor: "pointer" }}
          />
        </div>

      </div>

      {/* Queue Table */}
      <div className="glass-card" style={{ padding: "0 10px" }}>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Transaction ID</th>
                <th>Timestamp</th>
                <th>Customer</th>
                <th>Amount</th>
                <th>Merchant</th>
                <th>Risk Score</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: "center", padding: "30px", color: "var(--text-muted)" }}>
                    No payments found matching the current search parameters.
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((tx) => {
                  // Determine score label color
                  let scoreColor = "var(--success)";
                  if (tx.risk_score >= 75.0) scoreColor = "var(--danger)";
                  else if (tx.risk_score >= 40.0) scoreColor = "var(--warning)";

                  // Determine status badge class
                  const statusClass = `status-badge status-${tx.status.toLowerCase()}`;

                  return (
                    <tr key={tx.id}>
                      <td style={{ fontWeight: "600" }}>{tx.transaction_id}</td>
                      <td style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                        {new Date(tx.timestamp).toLocaleString()}
                      </td>
                      <td>{tx.user_id}</td>
                      <td>{tx.currency} {tx.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                      <td>{tx.merchant_category}</td>
                      <td style={{ fontWeight: "700", color: scoreColor }}>
                        {tx.risk_score.toFixed(0)}%
                      </td>
                      <td>
                        <span className={statusClass}>{tx.status}</span>
                      </td>
                      <td>
                        <button
                          onClick={() => router.push(`/transactions/${tx.id}`)}
                          className="secondary"
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "6px 10px",
                            fontSize: "0.8rem"
                          }}
                        >
                          <Eye size={14} />
                          Investigate
                        </button>
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
