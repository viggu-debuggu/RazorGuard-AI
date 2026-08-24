"use client";

import React, { useEffect, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Share2, Search, Activity } from "lucide-react";

export default function GraphPlayground() {
  const { token } = useAuth();
  const [data, setData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");

  const fetchGraph = () => {
    if (!token) return;
    
    fetch("http://localhost:8000/api/v1/graph/visualize", {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then(res => res.json())
      .then(resData => {
        if (resData && resData.nodes) {
          setData(resData);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchGraph();
  }, [token]);

  if (loading) {
    return <div style={{ color: "var(--accent)", padding: "20px" }}>Loading payment network map...</div>;
  }

  // Filter nodes matching text search query
  const filteredNodes = data.nodes.filter(n => 
    n.id.toLowerCase().includes(searchQuery.toLowerCase()) || 
    n.type.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div>
      <h1>Network Graph Playground</h1>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "30px" }}>
        
        {/* Left column: search and statistics */}
        <div style={{ display: "flex", flexDirection: "column", gap: "25px" }}>
          
          <div className="glass-card">
            <h2>Graph Diagnostics</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.85rem", marginTop: "15px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Total Nodes</span>
                <strong>{data.nodes.length}</strong>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-muted)" }}>Total Relations</span>
                <strong>{data.edges.length}</strong>
              </div>
            </div>
          </div>

          <div className="glass-card" style={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
            <h2>Search Nodes</h2>
            <div style={{ position: "relative", marginBottom: "15px" }}>
              <Search size={16} color="var(--text-muted)" style={{ position: "absolute", left: "10px", top: "10px" }} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search account, device, IP..."
                style={{ paddingLeft: "34px", fontSize: "0.85rem" }}
              />
            </div>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", overflowY: "auto", maxHeight: "300px", flexGrow: 1 }}>
              {filteredNodes.length === 0 ? (
                <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", textAlign: "center" }}>No node matches found.</p>
              ) : (
                filteredNodes.map((n) => (
                  <div
                    key={n.id}
                    style={{
                      padding: "8px 12px",
                      backgroundColor: "rgba(0,0,0,0.3)",
                      border: "1px solid var(--card-border)",
                      borderRadius: "6px",
                      fontSize: "0.8rem",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center"
                    }}
                  >
                    <span style={{ fontWeight: "600" }}>{n.label}</span>
                    <span style={{ fontSize: "0.7rem", padding: "2px 6px", borderRadius: "4px", backgroundColor: "rgba(255,255,255,0.05)" }}>
                      {n.type}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>

        {/* Right column: Vis panel */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", minHeight: "450px" }}>
          <h2>Network Visualization Map</h2>
          
          <div style={{
            flexGrow: 1,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            border: "1px dashed var(--card-border)",
            borderRadius: "8px",
            backgroundColor: "rgba(0,0,0,0.2)",
            position: "relative"
          }}>
            {/* Draw a centralized grid map of all nodes */}
            <svg width="100%" height="400" style={{ pointerEvents: "all" }}>
              {/* Render background connection paths */}
              {data.edges.map((e, idx) => {
                // Find node index to distribute points
                const uIdx = data.nodes.findIndex(n => n.id === e.source);
                const vIdx = data.nodes.findIndex(n => n.id === e.target);
                if (uIdx === -1 || vIdx === -1) return null;
                
                const angleU = (2 * Math.PI * uIdx) / data.nodes.length;
                const angleV = (2 * Math.PI * vIdx) / data.nodes.length;
                
                const ux = 270 + 120 * Math.cos(angleU);
                const uy = 200 + 120 * Math.sin(angleU);
                const vx = 270 + 120 * Math.cos(angleV);
                const vy = 200 + 120 * Math.sin(angleV);

                return (
                  <line
                    key={idx}
                    x1={ux}
                    y1={uy}
                    x2={vx}
                    y2={vy}
                    stroke="rgba(56, 189, 248, 0.15)"
                    strokeWidth="1.5"
                  />
                );
              })}

              {/* Render node circles */}
              {data.nodes.map((n, idx) => {
                const angle = (2 * Math.PI * idx) / data.nodes.length;
                const x = 270 + 120 * Math.cos(angle);
                const y = 200 + 120 * Math.sin(angle);

                let color = "var(--accent)";
                if (n.type === "User") color = "#a855f7";
                else if (n.type === "Device") color = "var(--success)";
                else if (n.type === "IP") color = "var(--warning)";
                else if (n.type === "Merchant") color = "var(--danger)";

                return (
                  <g key={n.id}>
                    <circle cx={x} cy={y} r="8" fill={color} stroke="#09090b" strokeWidth="1.5" />
                    <text
                      x={x}
                      y={y - 12}
                      fill="#a1a1aa"
                      fontSize="8"
                      fontWeight="600"
                      textAnchor="middle"
                    >
                      {n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
            
            <div style={{ position: "absolute", bottom: "15px", right: "15px", fontSize: "0.75rem", display: "flex", gap: "10px" }}>
              <span style={{ color: "#a855f7" }}>● User</span>
              <span style={{ color: "var(--success)" }}>● Device</span>
              <span style={{ color: "var(--warning)" }}>● IP</span>
              <span style={{ color: "var(--danger)" }}>● Merchant</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
