"use client";

import React, { useEffect, useState } from "react";

export default function NetworkVisualizer({ userId, token }) {
  const [data, setData] = useState({ nodes: [], edges: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!userId || !token) return;
    
    // Fetch neighbors list for the active user
    fetch(`http://localhost:8000/api/v1/graph/neighbors?node_id=${userId}&node_type=User`, {
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
        console.error("Failed to load graph nodes", err);
        setLoading(false);
      });
  }, [userId, token]);

  if (loading) {
    return <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", padding: "20px" }}>Walking graph paths...</div>;
  }

  if (data.nodes.length === 0) {
    return <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", padding: "20px" }}>No relational graph links found.</div>;
  }

  // Position nodes in a simple circle for visual clarity and reliability
  const width = 340;
  const height = 240;
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = 80;

  const positionedNodes = data.nodes.map((node, index) => {
    if (index === 0) {
      // Center the starting user node
      return { ...node, x: centerX, y: centerY };
    }
    const angle = (2 * Math.PI * (index - 1)) / (data.nodes.length - 1);
    return {
      ...node,
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle)
    };
  });

  // Create lookup dictionary for coordinates
  const nodeCoords = {};
  positionedNodes.forEach(node => {
    nodeCoords[node.id] = { x: node.x, y: node.y };
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
      <svg width={width} height={height} style={{ backgroundColor: "rgba(9, 9, 11, 0.4)", borderRadius: "8px", border: "1px solid var(--card-border)" }}>
        {/* Draw edges/links */}
        {data.edges.map((edge, idx) => {
          const start = nodeCoords[edge.source];
          const end = nodeCoords[edge.target];
          if (!start || !end) return null;
          
          return (
            <line
              key={idx}
              x1={start.x}
              y1={start.y}
              x2={end.x}
              y2={end.y}
              stroke="rgba(255, 255, 255, 0.15)"
              strokeWidth="2"
              strokeDasharray={edge.relation === "SHARED_WITH" ? "4" : "0"}
            />
          );
        })}

        {/* Draw nodes */}
        {positionedNodes.map((node) => {
          // Color coding by type
          let color = "var(--accent)";
          if (node.type === "User") color = "#a855f7";      // Purple
          else if (node.type === "Device") color = "var(--success)"; // Green
          else if (node.type === "IP") color = "var(--warning)";     // Yellow
          else if (node.type === "Merchant") color = "var(--danger)"; // Red

          const isCenter = node.id === `User:${userId}`;

          return (
            <g key={node.id}>
              <circle
                cx={node.x}
                cy={node.y}
                r={isCenter ? 12 : 8}
                fill={color}
                stroke="#fff"
                strokeWidth={isCenter ? 2 : 1}
              />
              <text
                x={node.x}
                y={node.y - 14}
                fill="#f4f4f5"
                fontSize="9"
                fontWeight="600"
                textAnchor="middle"
                style={{ pointerEvents: "none", filter: "drop-shadow(0px 1px 2px rgba(0,0,0,0.8))" }}
              >
                {node.label.length > 14 ? node.label.substring(0, 12) + "..." : node.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div style={{ display: "flex", gap: "10px", marginTop: "10px", flexWrap: "wrap", justifyContent: "center" }}>
        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>• User Account (Purple)</span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>• Device Fingerprint (Green)</span>
        <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>• IP Address (Yellow)</span>
      </div>
    </div>
  );
}
