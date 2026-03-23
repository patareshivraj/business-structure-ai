import React, { useState, useRef, useCallback, useEffect } from "react";
import ReactFlow, {
  Background,
  Controls,
  Handle,
  Position,
  BaseEdge,
  getBezierPath,
  useReactFlow,
  ReactFlowProvider,
} from "reactflow";
import dagre from "dagre";
import "reactflow/dist/style.css";

// ─── Constants ────────────────────────────────────────────────────────────────
const NODE_W = 190;
const NODE_H = 42;

// Color palette per level — vivid enough for both themes
// Extended to support deep hierarchies (auto-cycles via Math.min for deeper levels)
const PALETTE = [
  { fill: "#3b5bdb", glow: "#4c6ef5" }, // blue   — Level 0
  { fill: "#2f9e44", glow: "#40c057" }, // green  — Level 1
  { fill: "#c92a2a", glow: "#fa5252" }, // red    — Level 2
  { fill: "#6741d9", glow: "#845ef7" }, // purple — Level 3
  { fill: "#e67700", glow: "#fd7e14" }, // orange — Level 4
  { fill: "#087f5b", glow: "#12b886" }, // teal   — Level 5
  { fill: "#ae3ec9", glow: "#be4bdb" }, // magenta — Level 6
  { fill: "#5c7cfa", glow: "#748ffc" }, // indigo — Level 7
  { fill: "#e03131", glow: "#f03e3e" }, // crimson — Level 8
  { fill: "#2f8af5", glow: "#4dabf7" }, // sky    — Level 9
  { fill: "#099268", glow: "#12b886" }, // emerald — Level 10
];

// Friendly names for each depth level (dynamic legend uses these)
// These are generic labels that apply to any discovered hierarchy
const LEVEL_NAMES = ["Company", "Business Unit", "Division", "Sub-unit", "Team", "Sub-team"];

// ─── Global CSS injected once ─────────────────────────────────────────────────
const FLOW_CSS = `
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

/* marching-ants animation on every edge path */
.react-flow__edge-path {
  stroke-dasharray: 10 6;
  animation: marchAnts 1.6s linear infinite;
}
@keyframes marchAnts {
  to { stroke-dashoffset: -32; }
}

/* node hover lift */
.react-flow__node:hover { filter: brightness(1.08); transform: translateY(-1px); transition: filter 0.15s, transform 0.15s; }

/* hide default edge label layer artefacts */
.react-flow__edge-textwrapper { display: none !important; }

/* controls theming */
.react-flow__controls-button { border: none !important; }
`;

function injectCSS() {
  if (document.getElementById("bsi-styles")) return;
  const el = document.createElement("style");
  el.id = "bsi-styles";
  el.textContent = FLOW_CSS;
  document.head.appendChild(el);
}

// ─── Custom Bezier Edge with animated dash + arrowhead ────────────────────────
function AnimatedEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data = {} }) {
  const [path] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const color  = data.color || "#6b7280";
  const markId = `arrow-${id}`;
  return (
    <>
      <defs>
        <marker id={markId} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L6,3 z" fill={color} opacity="0.85" />
        </marker>
      </defs>
      <path
        id={id}
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={1.8}
        strokeDasharray="10 6"
        style={{ animation: "marchAnts 1.6s linear infinite" }}
        markerEnd={`url(#${markId})`}
        opacity={0.9}
      />
    </>
  );
}

const edgeTypes = { animated: AnimatedEdge };

// ─── Custom Pill Node ─────────────────────────────────────────────────────────
function OrgNode({ data }) {
  const { label, fill, glow, hasChildren, isCollapsed } = data;
  return (
    <>
      <Handle type="target" position={Position.Left}
        style={{ opacity: 0, width: 1, height: 1, border: "none", background: "transparent" }} />
      <div style={{
        background: fill,
        color: "#fff",
        borderRadius: 22,
        width: NODE_W,
        height: NODE_H,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 5,
        fontSize: 13,
        fontWeight: 600,
        fontFamily: "'DM Sans', sans-serif",
        cursor: hasChildren ? "pointer" : "default",
        userSelect: "none",
        boxShadow: `0 0 0 1.5px ${glow}55, 0 4px 16px ${fill}55`,
        padding: "0 16px",
        textAlign: "center",
        lineHeight: 1.3,
        overflow: "hidden",
        whiteSpace: "nowrap",
        textOverflow: "ellipsis",
        transition: "box-shadow 0.2s",
      }}>
        <span style={{ flex: 1, textAlign: "center", overflow: "hidden", textOverflow: "ellipsis" }}>
          {label}
        </span>
        {hasChildren && (
          <span style={{ fontSize: 9, opacity: 0.75, flexShrink: 0 }}>
            {isCollapsed ? "▶" : "▼"}
          </span>
        )}
      </div>
      <Handle type="source" position={Position.Right}
        style={{ opacity: 0, width: 1, height: 1, border: "none", background: "transparent" }} />
    </>
  );
}

const nodeTypes = { orgNode: OrgNode };

// ─── Dagre Layout ─────────────────────────────────────────────────────────────
function layoutGraph(nodes, edges) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 32, ranksep: 120, edgesep: 8 });
  nodes.forEach((n) => g.setNode(n.id, { width: NODE_W, height: NODE_H }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return {
    nodes: nodes.map((n) => {
      const pos = g.node(n.id);
      return { ...n, position: { x: pos.x - NODE_W / 2, y: pos.y - NODE_H / 2 } };
    }),
    edges,
  };
}

// ─── Build graph from tree, track max depth ───────────────────────────────────
function buildGraph(tree, parentId = null, path = "root", level = 0, nodes = [], edges = [], collapsedState = {}, maxDepthRef = { val: 0 }) {
  const id          = path;
  const palette     = PALETTE[Math.min(level, PALETTE.length - 1)];
  const isCollapsed = !!collapsedState[id];
  const hasChildren = !!(tree.children && tree.children.length > 0);
  if (level > maxDepthRef.val) maxDepthRef.val = level;

  nodes.push({
    id,
    type: "orgNode",
    data: { label: tree.name, fill: palette.fill, glow: palette.glow, hasChildren, isCollapsed },
    position: { x: 0, y: 0 },
  });

  if (parentId) {
    const parentLevel = Math.max(0, level - 1);
    const edgeColor   = PALETTE[Math.min(parentLevel, PALETTE.length - 1)].glow;
    edges.push({
      id:     `e-${parentId}-${id}`,
      source: parentId,
      target: id,
      type:   "animated",
      data:   { color: edgeColor },
    });
  }

  if (!isCollapsed && tree.children) {
    tree.children.forEach((child, idx) => {
      buildGraph(child, id, `${path}-${idx}`, level + 1, nodes, edges, collapsedState, maxDepthRef);
    });
  }

  return { nodes, edges, maxDepth: maxDepthRef.val };
}

// ─── Dynamic Legend — only shows levels actually present in data ──────────────
function DynamicLegend({ maxDepth, darkMode }) {
  const textColor = darkMode ? "#dce8f5" : "#1e293b";
  const count     = Math.min(maxDepth + 1, PALETTE.length);
  if (count === 0) return null;
  return (
    <div style={{
      position: "absolute", top: 18, left: 18, zIndex: 10,
      pointerEvents: "none", userSelect: "none",
    }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: i < count - 1 ? 10 : 0 }}>
          <div style={{
            width: 14, height: 14, borderRadius: "50%",
            background: PALETTE[i].fill,
            flexShrink: 0,
            boxShadow: `0 0 7px ${PALETTE[i].glow}88`,
          }} />
          <span style={{ fontSize: 13.5, fontWeight: 500, color: textColor, fontFamily: "'DM Sans', sans-serif" }}>
            {LEVEL_NAMES[i] || `Level ${i}`}
          </span>
        </div>
      ))}
    </div>
  );
}

// ─── Inner App (needs ReactFlowProvider context) ──────────────────────────────
function AppInner() {
  const [company,   setCompany]   = useState("");
  const [treeData,  setTreeData]  = useState(null);
  const [collapsed, setCollapsed] = useState({});
  const [nodes,     setNodes]     = useState([]);
  const [edges,     setEdges]     = useState([]);
  const [maxDepth,  setMaxDepth]  = useState(0);
  const [darkMode,  setDarkMode]  = useState(true);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const debounceRef = useRef(null);

  useEffect(() => { injectCSS(); }, []);

  const rebuildGraph = useCallback((tree, collapsedState) => {
    const maxDepthRef = { val: 0 };
    const graph       = buildGraph(tree, null, "root", 0, [], [], collapsedState, maxDepthRef);
    const laid        = layoutGraph(graph.nodes, graph.edges);
    setNodes(laid.nodes);
    setEdges(laid.edges);
    setMaxDepth(maxDepthRef.val);
  }, []);

  // Get API URL from environment variable, fallback to localhost for development
  const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000';

  const searchCompany = () => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      const q = company.trim();
      if (!q) return;
      setLoading(true);
      setError(null);
      try {
        const res  = await fetch(`${API_URL}/company/${encodeURIComponent(q)}/intelligence`);
        if (!res.ok) {
          const errData = await res.json().catch(() => null);
          const msg = errData?.error?.message || `Request failed with status ${res.status}`;
          throw new Error(msg);
        }
        const data = await res.json();
        setTreeData(data.structure);
        setCollapsed({});
        rebuildGraph(data.structure, {});
      } catch (err) {
        setError(err.message);
        // Auto-dismiss after 8 seconds
        setTimeout(() => setError(null), 8000);
      }
      setLoading(false);
    }, 400);
  };

  const onNodeClick = useCallback((_, node) => {
    if (!treeData) return;
    const newCollapsed = { ...collapsed, [node.id]: !collapsed[node.id] };
    setCollapsed(newCollapsed);
    setTimeout(() => rebuildGraph(treeData, newCollapsed), 50);
  }, [treeData, collapsed, rebuildGraph]);

  const handleKeyDown = (e) => { if (e.key === "Enter") searchCompany(); };

  // ── theme tokens ──────────────────────────────────────────────────────────
  const T = darkMode ? {
    bg: "#0b1526", header: "#080f1e", border: "#1c3555",
    inputBg: "#091422", inputFg: "#dce8f5", mutedFg: "#4a6280",
    textFg: "#dce8f5", subtextFg: "#7a9bbf", gridCol: "#142035",
    ctrlBg: "#0f1e35", btnBg: "#091422",
  } : {
    bg: "#f2f5fb", header: "#ffffff", border: "#d8e0ee",
    inputBg: "#eef2f9", inputFg: "#0f172a", mutedFg: "#93a3b4",
    textFg: "#0f172a", subtextFg: "#5a6a85", gridCol: "#c5cfde",
    ctrlBg: "#ffffff", btnBg: "#eef2f9",
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100vh",
      fontFamily: "'DM Sans', sans-serif",
      background: T.bg, color: T.textFg,
      transition: "background 0.25s, color 0.25s",
    }}>

      {/* ── Header ── */}
      <div style={{
        height: 56, padding: "0 20px",
        borderBottom: `1px solid ${T.border}`,
        background: T.header,
        display: "flex", alignItems: "center", gap: 10,
        flexShrink: 0, transition: "background 0.25s",
      }}>
        {/* Logo pill */}
        <div style={{
          width: 32, height: 32, borderRadius: 8, flexShrink: 0,
          background: PALETTE[0].fill,
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: `0 2px 8px ${PALETTE[0].glow}66`,
        }}>
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
            <rect x="2" y="3" width="6" height="6" rx="1.5" />
            <rect x="16" y="3" width="6" height="6" rx="1.5" />
            <rect x="9" y="15" width="6" height="6" rx="1.5" />
            <path d="M5 9v3h14V9" /><path d="M12 12v3" />
          </svg>
        </div>

        {/* Title */}
        <div style={{ marginRight: "auto" }}>
          <div style={{ fontWeight: 700, fontSize: 14.5, letterSpacing: "-0.2px", lineHeight: 1.2 }}>
            Business Structure Intelligence
          </div>
          <div style={{ fontSize: 11, color: T.subtextFg }}>Company org explorer</div>
        </div>

        {/* Search input */}
        <div style={{
          display: "flex", alignItems: "center",
          background: T.inputBg, border: `1px solid ${T.border}`,
          borderRadius: 8, overflow: "hidden",
        }}>
          <svg style={{ marginLeft: 10, flexShrink: 0 }} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={T.mutedFg} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
          </svg>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search company…"
            style={{
              padding: "7px 11px 7px 7px", border: "none",
              background: "transparent", color: T.inputFg,
              fontSize: 13, outline: "none", width: 185,
            }}
          />
        </div>

        {/* Search button */}
        <button
          onClick={searchCompany} disabled={loading}
          style={{
            background: PALETTE[0].fill, color: "#fff", border: "none",
            padding: "7px 18px", borderRadius: 8, fontSize: 13, fontWeight: 700,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.65 : 1,
            boxShadow: `0 2px 8px ${PALETTE[0].glow}55`,
            transition: "opacity 0.2s",
          }}
        >
          {loading ? "Loading…" : "Search"}
        </button>

        {/* Dark / Light toggle */}
        <button
          onClick={() => setDarkMode((d) => !d)}
          style={{
            background: T.btnBg, border: `1px solid ${T.border}`,
            color: T.textFg, padding: "6px 13px", borderRadius: 8,
            cursor: "pointer", fontSize: 13, fontWeight: 600,
            display: "flex", alignItems: "center", gap: 6, flexShrink: 0,
          }}
        >
          <span>{darkMode ? "☀️" : "🌙"}</span>
          <span style={{ color: T.subtextFg }}>{darkMode ? "Light" : "Dark"}</span>
        </button>
      </div>

      {/* ── Error Toast ── */}
      {error && (
        <div style={{
          position: "fixed", top: 68, left: "50%", transform: "translateX(-50%)",
          zIndex: 100, padding: "10px 20px", borderRadius: 10,
          background: darkMode ? "#3b1010" : "#fef2f2",
          border: `1px solid ${darkMode ? "#7f1d1d" : "#fca5a5"}`,
          color: darkMode ? "#fca5a5" : "#991b1b",
          fontSize: 13, fontWeight: 500, fontFamily: "'DM Sans', sans-serif",
          display: "flex", alignItems: "center", gap: 10,
          boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
          animation: "fadeIn 0.2s ease-out",
        }}>
          <span>⚠️ {error}</span>
          <button onClick={() => setError(null)} style={{
            background: "none", border: "none", cursor: "pointer",
            color: darkMode ? "#fca5a5" : "#991b1b", fontSize: 16,
            padding: "0 4px", lineHeight: 1,
          }}>✕</button>
        </div>
      )}

      {/* ── Canvas ── */}
      <div style={{ flex: 1, position: "relative", minHeight: 0 }}>

        {/* Empty state */}
        {!treeData && !loading && (
          <div style={{
            position: "absolute", inset: 0, zIndex: 5, pointerEvents: "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            flexDirection: "column", gap: 14,
          }}>
            <div style={{
              width: 60, height: 60, borderRadius: "50%",
              background: `${PALETTE[0].fill}18`,
              border: `1.5px dashed ${PALETTE[0].fill}55`,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={PALETTE[0].fill} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity={0.7}>
                <circle cx="11" cy="11" r="8" /><path d="m21 21-4.35-4.35" />
              </svg>
            </div>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 15, fontWeight: 600, color: T.textFg, marginBottom: 4 }}>No company loaded</div>
              <div style={{ fontSize: 13, color: T.mutedFg }}>Type a company name and press Search</div>
            </div>
          </div>
        )}

        {/* Dynamic legend — only levels present in data */}
        <DynamicLegend maxDepth={maxDepth} darkMode={darkMode} />

        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.22 }}
          style={{ background: T.bg }}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant="dots" color={T.gridCol} gap={24} size={1.2} />
          <Controls
            style={{
              background: T.ctrlBg,
              border: `1px solid ${T.border}`,
              borderRadius: 9,
              boxShadow: "0 3px 10px rgba(0,0,0,0.12)",
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ReactFlowProvider>
      <AppInner />
    </ReactFlowProvider>
  );
}