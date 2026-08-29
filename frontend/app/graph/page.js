"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { useAuth } from "../../context/AuthContext";
import dynamic from "next/dynamic";
import { API_URL } from "../../lib/api";


// react-force-graph-2d uses browser APIs — must be dynamically imported (no SSR)
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

// Node visual config: shape + color (redundant coding for accessibility)
const NODE_CONFIG = {
  User:        { color: "#818CF8", shape: "circle",   label: "User Account",        edgeColor: "#818CF8" },
  Transaction: { color: "#FBBF24", shape: "diamond",  label: "Transaction",         edgeColor: "#FBBF24" },
  Device:      { color: "#34D399", shape: "square",   label: "Device Fingerprint",  edgeColor: "#34D399" },
  IP:          { color: "#F97316", shape: "triangle",  label: "IP Address",          edgeColor: "#F97316" },
  Merchant:    { color: "#C084FC", shape: "hexagon",  label: "Merchant",            edgeColor: "#C084FC" },
};

const DEFAULT_COLOR = "#71717A";

const EDGE_LABEL_MAP = {
  "SHARED_WITH": "shares device with",
  "SAME_IP":     "same IP as",
  "USED_DEVICE": "uses device",
  "PROCESSED_BY": "processed by",
  "LINKED_TO":   "linked to",
};

function getEdgeLabel(relation) {
  if (!relation) return "connected to";
  return EDGE_LABEL_MAP[relation.toUpperCase()] || relation.toLowerCase().replace(/_/g, " ");
}

// Draw node shapes on canvas
function drawNode(node, ctx, globalScale) {
  const cfg = NODE_CONFIG[node.type] || { color: DEFAULT_COLOR, shape: "circle" };
  const r = node.isDimmed ? 5 : (node.isSelected ? 9 : 6);
  const alpha = node.isDimmed ? 0.15 : 1;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = cfg.color;
  ctx.strokeStyle = node.isSelected ? "#FFFFFF" : cfg.color;
  ctx.lineWidth = node.isSelected ? 2 : 0.5;
  ctx.beginPath();

  if (cfg.shape === "circle") {
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
  } else if (cfg.shape === "square") {
    ctx.rect(node.x - r, node.y - r, r * 2, r * 2);
  } else if (cfg.shape === "diamond") {
    ctx.moveTo(node.x, node.y - r * 1.2);
    ctx.lineTo(node.x + r, node.y);
    ctx.lineTo(node.x, node.y + r * 1.2);
    ctx.lineTo(node.x - r, node.y);
    ctx.closePath();
  } else if (cfg.shape === "triangle") {
    ctx.moveTo(node.x, node.y - r * 1.2);
    ctx.lineTo(node.x + r * 1.1, node.y + r * 0.8);
    ctx.lineTo(node.x - r * 1.1, node.y + r * 0.8);
    ctx.closePath();
  } else if (cfg.shape === "hexagon") {
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 6;
      const px = node.x + r * Math.cos(angle);
      const py = node.y + r * Math.sin(angle);
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
    }
    ctx.closePath();
  }

  ctx.fill();
  if (node.isSelected) ctx.stroke();

  // Label
  if (globalScale > 0.6 && !node.isDimmed) {
    ctx.font = `${node.isSelected ? 700 : 400} ${Math.max(3, 10 / globalScale)}px system-ui, sans-serif`;
    ctx.fillStyle = "#E8E8EC";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const label = node.label && node.label.length > 14 ? node.label.substring(0, 12) + "…" : (node.label || node.id);
    ctx.fillText(label, node.x, node.y + r + 2);
  }

  ctx.restore();
}

// Generate plain-English summary for a selected node
function buildSummary(selectedNode, graphData) {
  if (!selectedNode) return null;
  const { nodes, links } = graphData;

  const neighborLinks = links.filter(
    (l) => l.source.id === selectedNode.id || l.target.id === selectedNode.id
  );
  const neighbors = neighborLinks.map((l) =>
    l.source.id === selectedNode.id ? l.target : l.source
  );

  const userNeighbors    = neighbors.filter((n) => n.type === "User");
  const deviceNeighbors  = neighbors.filter((n) => n.type === "Device");
  const ipNeighbors      = neighbors.filter((n) => n.type === "IP");
  const txNeighbors      = neighbors.filter((n) => n.type === "Transaction");
  const merchantNeighbors = neighbors.filter((n) => n.type === "Merchant");

  const parts = [];

  if (selectedNode.type === "User") {
    parts.push(`Account "${selectedNode.label || selectedNode.id}"`);
    if (deviceNeighbors.length > 0) parts.push(`shares ${deviceNeighbors.length} device fingerprint${deviceNeighbors.length > 1 ? "s" : ""}`);
    if (ipNeighbors.length > 0) parts.push(`is associated with ${ipNeighbors.length} IP address${ipNeighbors.length > 1 ? "es" : ""}`);
    if (userNeighbors.length > 0) parts.push(`overlaps with ${userNeighbors.length} other account${userNeighbors.length > 1 ? "s" : ""} via shared hardware`);
    if (txNeighbors.length > 0) parts.push(`has ${txNeighbors.length} linked transaction${txNeighbors.length > 1 ? "s" : ""} in the graph`);
  } else if (selectedNode.type === "Device") {
    parts.push(`Device "${selectedNode.label || selectedNode.id}"`);
    if (userNeighbors.length > 1) {
      parts.push(`is shared by ${userNeighbors.length} distinct accounts — a high-risk device-sharing pattern`);
    } else if (userNeighbors.length === 1) {
      parts.push(`is used by 1 account`);
    }
  } else if (selectedNode.type === "IP") {
    parts.push(`IP address "${selectedNode.label || selectedNode.id}"`);
    if (userNeighbors.length > 1) {
      parts.push(`originates from ${userNeighbors.length} distinct accounts — multiple accounts sharing a network source`);
    } else {
      parts.push(`is linked to ${userNeighbors.length} account${userNeighbors.length !== 1 ? "s" : ""}`);
    }
  } else if (selectedNode.type === "Transaction") {
    parts.push(`Transaction "${selectedNode.label || selectedNode.id}"`);
    if (userNeighbors.length > 0) parts.push(`initiated by ${userNeighbors.length} account`);
    if (merchantNeighbors.length > 0) parts.push(`processed by ${merchantNeighbors[0].label || "merchant"}`);
  } else if (selectedNode.type === "Merchant") {
    parts.push(`Merchant "${selectedNode.label || selectedNode.id}"`);
    if (txNeighbors.length > 0) parts.push(`has ${txNeighbors.length} linked transaction${txNeighbors.length > 1 ? "s" : ""} in the current graph`);
  } else {
    parts.push(`Node "${selectedNode.label || selectedNode.id}" (${selectedNode.type}) has ${neighbors.length} direct connection${neighbors.length !== 1 ? "s" : ""}`);
  }

  if (parts.length === 1) parts.push(`has ${neighbors.length} direct connection${neighbors.length !== 1 ? "s" : ""} in the graph`);

  return parts.join(", ") + ".";
}

// Node type counts helper
function countByType(nodes) {
  const counts = {};
  nodes.forEach((n) => {
    counts[n.type] = (counts[n.type] || 0) + 1;
  });
  return counts;
}

export default function GraphPlayground() {
  const { token } = useAuth();
  const [rawData, setRawData] = useState({ nodes: [], edges: [] });
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredLink, setHoveredLink] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const graphRef = useRef(null);

  // Fetch graph data
  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/api/v1/graph/visualize`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data?.nodes) {
          setRawData(data);
          const links = (data.edges || []).map((e, idx) => ({
            id: `e${idx}`,
            source: e.source,
            target: e.target,
            relation: e.relation || e.type || "",
          }));
          setGraphData({ nodes: data.nodes, links });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [token]);

  // Build neighbor set when a node is selected
  const neighborIds = useCallback(() => {
    if (!selectedNode) return null;
    const ids = new Set([selectedNode.id]);
    graphData.links.forEach((l) => {
      const srcId = typeof l.source === "object" ? l.source.id : l.source;
      const tgtId = typeof l.target === "object" ? l.target.id : l.target;
      if (srcId === selectedNode.id) ids.add(tgtId);
      if (tgtId === selectedNode.id) ids.add(srcId);
    });
    return ids;
  }, [selectedNode, graphData.links]);

  // Attach isSelected / isDimmed flags to nodes before rendering
  const paintedData = React.useMemo(() => {
    const nbrs = neighborIds();
    return {
      nodes: graphData.nodes.map((n) => ({
        ...n,
        isSelected: selectedNode?.id === n.id,
        isDimmed: nbrs !== null && !nbrs.has(n.id),
      })),
      links: graphData.links,
    };
  }, [graphData, selectedNode, neighborIds]);

  // Filter highlight (search query dims non-matching nodes)
  const displayData = React.useMemo(() => {
    if (!searchQuery) return paintedData;
    const q = searchQuery.toLowerCase();
    return {
      ...paintedData,
      nodes: paintedData.nodes.map((n) => ({
        ...n,
        isDimmed: !(n.id.toLowerCase().includes(q) || (n.type || "").toLowerCase().includes(q) || (n.label || "").toLowerCase().includes(q)),
      })),
    };
  }, [paintedData, searchQuery]);

  const typeCounts = countByType(rawData.nodes);
  const summary = buildSummary(selectedNode, { nodes: graphData.nodes, links: graphData.links });

  const handleNodeClick = useCallback((node) => {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  }, []);

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const resetView = () => {
    graphRef.current?.zoomToFit(400, 40);
    setSelectedNode(null);
  };

  if (loading) {
    return (
      <div>
        <div className="page-header">
          <h1 className="page-title">Relationship Map</h1>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: "12px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div className="skeleton panel" style={{ height: "130px" }} />
            <div className="skeleton panel" style={{ height: "200px" }} />
          </div>
          <div className="skeleton panel" style={{ height: "500px" }} />
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Relationship Map</h1>
        <span className="page-subtitle">
          {rawData.nodes.length} nodes · {rawData.edges?.length || 0} edges
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: "12px", alignItems: "start" }}>

        {/* === Left Panel === */}
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>

          {/* Graph statistics */}
          <div className="panel">
            <h2>Graph Statistics</h2>
            <table className="data-table" style={{ marginTop: "6px" }}>
              <thead>
                <tr>
                  <th>Type</th>
                  <th style={{ textAlign: "right" }}>Count</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(typeCounts).map(([type, count]) => {
                  const cfg = NODE_CONFIG[type] || { color: DEFAULT_COLOR };
                  return (
                    <tr key={type}>
                      <td style={{ fontSize: "0.75rem" }}>
                        <span style={{ color: cfg.color, marginRight: "6px", fontWeight: "700" }}>●</span>
                        {type}
                      </td>
                      <td className="num" style={{ fontSize: "0.8rem", fontWeight: "700" }}>{count}</td>
                    </tr>
                  );
                })}
                <tr>
                  <td style={{ fontSize: "0.75rem", fontWeight: "600", color: "var(--fg-muted)" }}>Relations</td>
                  <td className="num" style={{ fontSize: "0.8rem", fontWeight: "700" }}>{rawData.edges?.length || 0}</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Search */}
          <div className="panel">
            <h2>Search Nodes</h2>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="ID, type, or label…"
              style={{ fontSize: "0.78rem", padding: "6px 10px", marginBottom: "10px" }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "180px", overflowY: "auto" }}>
              {rawData.nodes.filter(n =>
                !searchQuery ||
                n.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (n.label || "").toLowerCase().includes(searchQuery.toLowerCase())
              ).map((n) => {
                const cfg = NODE_CONFIG[n.type] || { color: DEFAULT_COLOR };
                return (
                  <div
                    key={n.id}
                    onClick={() => setSelectedNode(selectedNode?.id === n.id ? null : n)}
                    style={{
                      padding: "5px 8px",
                      borderRadius: "3px",
                      cursor: "pointer",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      backgroundColor: selectedNode?.id === n.id ? "var(--accent-dim)" : "transparent",
                      border: selectedNode?.id === n.id ? "1px solid var(--border-active)" : "1px solid transparent",
                    }}
                  >
                    <span style={{ fontSize: "0.72rem", fontFamily: "var(--font-mono)", color: "var(--fg)" }}>
                      {(n.label || n.id).substring(0, 18)}
                    </span>
                    <span style={{ fontSize: "0.65rem", color: cfg.color, fontWeight: "700" }}>{n.type}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selection summary */}
          {selectedNode && (
            <div className="panel" style={{ border: "1px solid var(--border-active)" }}>
              <h2>Selection Insight</h2>
              <p style={{ fontFamily: "var(--font-mono)", fontSize: "0.7rem", color: "var(--accent-text)", marginBottom: "8px", fontWeight: "700" }}>
                {selectedNode.type}: {selectedNode.label || selectedNode.id}
              </p>
              <p style={{ fontSize: "0.76rem", color: "var(--fg)", lineHeight: "1.55" }}>
                {summary}
              </p>
              <button
                className="ghost"
                style={{ marginTop: "10px", fontSize: "0.7rem", width: "100%", textAlign: "center" }}
                onClick={() => setSelectedNode(null)}
              >
                Clear selection
              </button>
            </div>
          )}

          {/* Legend */}
          <div className="panel">
            <h2>Legend</h2>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "6px" }}>
              {Object.entries(NODE_CONFIG).map(([type, cfg]) => (
                <div key={type} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <svg width="14" height="14" style={{ flexShrink: 0 }}>
                    {cfg.shape === "circle" && <circle cx="7" cy="7" r="5.5" fill={cfg.color} />}
                    {cfg.shape === "square" && <rect x="1" y="1" width="12" height="12" fill={cfg.color} />}
                    {cfg.shape === "diamond" && <polygon points="7,1 13,7 7,13 1,7" fill={cfg.color} />}
                    {cfg.shape === "triangle" && <polygon points="7,1 13,13 1,13" fill={cfg.color} />}
                    {cfg.shape === "hexagon" && (
                      <polygon
                        points={Array.from({ length: 6 }, (_, i) => {
                          const a = (Math.PI / 3) * i - Math.PI / 6;
                          return `${7 + 6 * Math.cos(a)},${7 + 6 * Math.sin(a)}`;
                        }).join(" ")}
                        fill={cfg.color}
                      />
                    )}
                  </svg>
                  <div>
                    <p style={{ fontSize: "0.72rem", fontWeight: "600", color: "var(--fg)" }}>{type}</p>
                    <p style={{ fontSize: "0.65rem", color: "var(--fg-muted)" }}>{cfg.label}</p>
                  </div>
                </div>
              ))}
              <hr className="section-divider" style={{ margin: "6px 0" }} />
              <div style={{ fontSize: "0.65rem", color: "var(--fg-muted)", lineHeight: "1.5" }}>
                <p>— Solid line: direct relationship</p>
                <p>— Dashed line: shared / indirect link</p>
                <p>Click a node to highlight its direct connections.</p>
                <p>Hover an edge to see the relationship label.</p>
              </div>
            </div>
          </div>

          {/* Zoom controls */}
          <div className="panel">
            <h2>View Controls</h2>
            <div style={{ display: "flex", gap: "6px", marginTop: "6px" }}>
              <button className="secondary" style={{ flex: 1, padding: "6px" }} onClick={() => graphRef.current?.zoom(graphRef.current.zoom() * 1.3, 200)}>+</button>
              <button className="secondary" style={{ flex: 1, padding: "6px" }} onClick={() => graphRef.current?.zoom(graphRef.current.zoom() * 0.77, 200)}>−</button>
              <button className="secondary" style={{ flex: 2, padding: "6px", fontSize: "0.72rem" }} onClick={resetView}>⊙ Reset View</button>
            </div>
          </div>
        </div>

        {/* === Right Panel — Graph Canvas === */}
        <div className="panel" style={{ padding: "0", overflow: "hidden", position: "relative", minHeight: "560px" }}>
          {displayData.nodes.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", minHeight: "480px", color: "var(--fg-dim)", gap: "8px" }}>
              <span style={{ fontSize: "2rem" }}>◌</span>
              <p style={{ fontSize: "0.82rem", color: "var(--fg-muted)" }}>No graph data loaded</p>
              <p style={{ fontSize: "0.72rem", color: "var(--fg-dim)" }}>Start the backend service to populate the relationship map.</p>
            </div>
          ) : (
            <ForceGraph2D
              ref={graphRef}
              graphData={displayData}
              nodeId="id"
              backgroundColor="#0A0A0C"
              width={undefined}
              height={560}
              nodeCanvasObject={(node, ctx, globalScale) => drawNode(node, ctx, globalScale)}
              nodeCanvasObjectMode={() => "replace"}
              linkColor={(link) => {
                if (hoveredLink === link) return "rgba(99, 102, 241, 0.9)";
                if (selectedNode) {
                  const srcId = typeof link.source === "object" ? link.source.id : link.source;
                  const tgtId = typeof link.target === "object" ? link.target.id : link.target;
                  const nbrs = neighborIds();
                  if (nbrs && nbrs.has(srcId) && nbrs.has(tgtId)) return "rgba(255,255,255,0.35)";
                  return "rgba(255,255,255,0.04)";
                }
                return "rgba(255,255,255,0.14)";
              }}
              linkWidth={(link) => (hoveredLink === link ? 2 : 1)}
              linkDirectionalParticles={0}
              linkLineDash={(link) => (link.relation === "SHARED_WITH" ? [4, 4] : null)}
              onNodeClick={handleNodeClick}
              onBackgroundClick={handleBackgroundClick}
              onLinkHover={setHoveredLink}
              onNodeHover={setHoveredNode}
              enableNodeDrag={true}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
              cooldownTicks={120}
            />
          )}

          {/* Hovered edge tooltip */}
          {hoveredLink && (
            <div style={{
              position: "absolute",
              bottom: "14px",
              left: "50%",
              transform: "translateX(-50%)",
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border)",
              borderRadius: "3px",
              padding: "5px 12px",
              fontSize: "0.72rem",
              color: "var(--fg)",
              pointerEvents: "none",
              whiteSpace: "nowrap",
            }}>
              {typeof hoveredLink.source === "object" ? (hoveredLink.source.label || hoveredLink.source.id) : hoveredLink.source}
              {" "}
              <span style={{ color: "var(--accent-text)", fontStyle: "italic" }}>
                {getEdgeLabel(hoveredLink.relation)}
              </span>
              {" "}
              {typeof hoveredLink.target === "object" ? (hoveredLink.target.label || hoveredLink.target.id) : hoveredLink.target}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
