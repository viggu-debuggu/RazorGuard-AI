"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
import { API_URL } from "../lib/api";


const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false });

const NODE_CONFIG = {
  User:        { color: "#6B7FD4", shape: "circle"  },
  Transaction: { color: "#C9974A", shape: "diamond" },
  Device:      { color: "#3D7A5C", shape: "square"  },
  IP:          { color: "#B08040", shape: "triangle" },
  Merchant:    { color: "#8E44AD", shape: "hexagon" },
};

const DEFAULT_COLOR = "#7A7A88";

const EDGE_LABEL_MAP = {
  "SHARED_WITH":  "shares device with",
  "SAME_IP":      "same IP as",
  "USED_DEVICE":  "uses device",
  "PROCESSED_BY": "processed by",
  "LINKED_TO":    "linked to",
};

function getEdgeLabel(relation) {
  if (!relation) return "connected to";
  return EDGE_LABEL_MAP[relation.toUpperCase()] || relation.toLowerCase().replace(/_/g, " ");
}

function drawNode(node, ctx, globalScale) {
  const cfg = NODE_CONFIG[node.type] || { color: DEFAULT_COLOR, shape: "circle" };
  const r = node.isDimmed ? 4 : (node.isSelected ? 8 : 5.5);
  const alpha = node.isDimmed ? 0.15 : 1;

  ctx.save();
  ctx.globalAlpha = alpha;
  ctx.fillStyle = cfg.color;
  ctx.strokeStyle = node.isSelected ? "#FFFFFF" : cfg.color;
  ctx.lineWidth = node.isSelected ? 1.5 : 0.5;
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

  if (globalScale > 0.7 && !node.isDimmed) {
    ctx.font = `${Math.max(3, 9 / globalScale)}px system-ui, sans-serif`;
    ctx.fillStyle = "#E8E8EC";
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    const lbl = (node.label || node.id || "");
    ctx.fillText(lbl.length > 12 ? lbl.substring(0, 11) + "…" : lbl, node.x, node.y + r + 2);
  }

  ctx.restore();
}

function buildSummary(selectedNode, links) {
  if (!selectedNode) return null;
  const neighborLinks = links.filter((l) => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    return s === selectedNode.id || t === selectedNode.id;
  });
  const neighbors = neighborLinks.map((l) => {
    const s = typeof l.source === "object" ? l.source : null;
    const t = typeof l.target === "object" ? l.target : null;
    const sId = s?.id;
    const tId = t?.id;
    return sId === selectedNode.id ? t : s;
  }).filter(Boolean);

  const byType = (type) => neighbors.filter((n) => n.type === type);
  const parts = [];
  const name = `"${selectedNode.label || selectedNode.id}"`;

  if (selectedNode.type === "User") {
    parts.push(`Account ${name}`);
    const d = byType("Device");
    const ip = byType("IP");
    const u = byType("User");
    if (d.length) parts.push(`shares ${d.length} device fingerprint${d.length > 1 ? "s" : ""}`);
    if (ip.length) parts.push(`originates from ${ip.length} IP address${ip.length > 1 ? "es" : ""}`);
    if (u.length) parts.push(`overlaps with ${u.length} other account${u.length > 1 ? "s" : ""} via shared hardware`);
  } else if (selectedNode.type === "Device") {
    const u = byType("User");
    parts.push(`Device ${name}`);
    if (u.length > 1) parts.push(`is shared by ${u.length} distinct accounts — elevated card-ring risk`);
    else parts.push(`is used by ${u.length} account`);
  } else if (selectedNode.type === "IP") {
    const u = byType("User");
    parts.push(`IP address ${name}`);
    if (u.length > 1) parts.push(`is the network origin for ${u.length} distinct accounts`);
    else parts.push(`is linked to ${u.length} account`);
  } else {
    parts.push(`Node ${name} (${selectedNode.type}) has ${neighbors.length} direct connection${neighbors.length !== 1 ? "s" : ""}`);
  }

  return parts.join(", ") + ".";
}

export default function NetworkVisualizer({ userId, token, compact = false }) {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredLink, setHoveredLink] = useState(null);
  const graphRef = useRef(null);

  useEffect(() => {
    if (!userId || !token) return;
    fetch(`${API_URL}/api/v1/graph/neighbors?node_id=${userId}&node_type=User`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data?.nodes) {
          const links = (data.edges || []).map((e, i) => ({
            id: `e${i}`,
            source: e.source,
            target: e.target,
            relation: e.relation || e.type || "",
          }));
          setGraphData({ nodes: data.nodes, links });
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [userId, token]);

  const neighborIds = useCallback(() => {
    if (!selectedNode) return null;
    const ids = new Set([selectedNode.id]);
    graphData.links.forEach((l) => {
      const s = typeof l.source === "object" ? l.source.id : l.source;
      const t = typeof l.target === "object" ? l.target.id : l.target;
      if (s === selectedNode.id) ids.add(t);
      if (t === selectedNode.id) ids.add(s);
    });
    return ids;
  }, [selectedNode, graphData.links]);

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

  const summary = buildSummary(selectedNode, graphData.links);
  const height = compact ? 280 : 400;

  if (loading) {
    return (
      <div style={{ height: `${height}px` }} className="skeleton" />
    );
  }

  if (graphData.nodes.length === 0) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: `${height}px`, color: "var(--fg-dim)", gap: "6px" }}>
        <span style={{ fontSize: "1.4rem" }}>◌</span>
        <p style={{ fontSize: "0.78rem", color: "var(--fg-muted)" }}>No relationship links found for this account.</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      <div style={{ border: "1px solid var(--border)", borderRadius: "3px", overflow: "hidden", position: "relative" }}>
        <ForceGraph2D
          ref={graphRef}
          graphData={paintedData}
          nodeId="id"
          backgroundColor="#0A0A0C"
          height={height}
          nodeCanvasObject={(node, ctx, globalScale) => drawNode(node, ctx, globalScale)}
          nodeCanvasObjectMode={() => "replace"}
          linkColor={(link) => {
            if (hoveredLink === link) return "rgba(201,151,74,0.85)";
            if (selectedNode) {
              const nbrs = neighborIds();
              const s = typeof link.source === "object" ? link.source.id : link.source;
              const t = typeof link.target === "object" ? link.target.id : link.target;
              if (nbrs?.has(s) && nbrs?.has(t)) return "rgba(255,255,255,0.35)";
              return "rgba(255,255,255,0.04)";
            }
            return "rgba(255,255,255,0.18)";
          }}
          linkWidth={1}
          linkLineDash={(l) => (l.relation === "SHARED_WITH" ? [3, 3] : null)}
          onNodeClick={(node) => setSelectedNode((p) => p?.id === node.id ? null : node)}
          onBackgroundClick={() => setSelectedNode(null)}
          onLinkHover={setHoveredLink}
          enableNodeDrag={true}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.35}
          cooldownTicks={80}
        />

        {/* Hovering edge label */}
        {hoveredLink && (
          <div style={{
            position: "absolute",
            bottom: "8px",
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "var(--bg-surface)",
            border: "1px solid var(--border)",
            borderRadius: "3px",
            padding: "3px 10px",
            fontSize: "0.68rem",
            color: "var(--fg)",
            pointerEvents: "none",
            whiteSpace: "nowrap",
          }}>
            <span style={{ color: "var(--accent-text)", fontStyle: "italic" }}>
              {getEdgeLabel(hoveredLink.relation)}
            </span>
          </div>
        )}
      </div>

      {/* Plain-English selection summary */}
      {selectedNode && summary && (
        <div style={{ padding: "8px 10px", backgroundColor: "var(--bg-inset)", border: "1px solid var(--border-active)", borderRadius: "3px" }}>
          <p style={{ fontSize: "0.7rem", fontWeight: "700", color: "var(--accent-text)", marginBottom: "3px" }}>
            {selectedNode.type}: {selectedNode.label || selectedNode.id}
          </p>
          <p style={{ fontSize: "0.72rem", color: "var(--fg)", lineHeight: "1.5" }}>{summary}</p>
        </div>
      )}

      {/* Compact legend strip */}
      {compact && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
          {Object.entries(NODE_CONFIG).map(([type, cfg]) => (
            <span key={type} style={{ fontSize: "0.65rem", color: "var(--fg-muted)", display: "flex", alignItems: "center", gap: "4px" }}>
              <svg width="10" height="10">
                {cfg.shape === "circle"   && <circle cx="5" cy="5" r="4" fill={cfg.color} />}
                {cfg.shape === "square"   && <rect x="1" y="1" width="8" height="8" fill={cfg.color} />}
                {cfg.shape === "diamond"  && <polygon points="5,1 9,5 5,9 1,5" fill={cfg.color} />}
                {cfg.shape === "triangle" && <polygon points="5,1 9,9 1,9" fill={cfg.color} />}
                {cfg.shape === "hexagon"  && (
                  <polygon points={Array.from({ length: 6 }, (_, i) => {
                    const a = (Math.PI / 3) * i - Math.PI / 6;
                    return `${5 + 4 * Math.cos(a)},${5 + 4 * Math.sin(a)}`;
                  }).join(" ")} fill={cfg.color} />
                )}
              </svg>
              {type}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
