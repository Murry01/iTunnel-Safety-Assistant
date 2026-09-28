import { useEffect, useRef, useState } from "react";
import { DataSet } from "vis-data";
import { Network } from "vis-network";
import { fetchGraph } from "../api.js";
import { ChevronIcon } from "./Icons.jsx";

// Categorical node colors — fixed in both themes, they distinguish node
// type rather than acting as UI chrome.
const COLORS = {
  Accident: "#e8823a",
  AccidentType: "#7f77dd",
  TunnelType: "#1d9e75",
  WorkProcess: "#1d9e75",
  AccidentObject: "#378add",
  Cause: "#d4537e",
};

// vis-network draws to <canvas> with these as literal option values,
// outside the CSS cascade, so label/edge chrome needs an explicit swap —
// the --ink-*/--fog-* variables don't reach in here for free.
const CHROME = {
  dark: { nodeLabel: "#d5d0c9", edge: "#4a453e", edgeLabel: "#7a7469" },
  light: { nodeLabel: "#2b2620", edge: "#c9c2b3", edgeLabel: "#6b6259" },
};

/**
 * Renders the vis-network canvas once data is loaded. Fetching and network
 * construction are deliberately two separate effects: the container <div>
 * only exists in the DOM once `status === "ready"`, so building the Network
 * inside the *fetch* effect would run before React has committed that div —
 * `ref.current` would still be null at that point (this was the bug that
 * made the graph never actually draw). Splitting them guarantees the
 * construction effect only fires after the ref-bearing div has mounted.
 */
export function GraphCanvas({ caseIds, height = "360px", theme = "dark" }) {
  const containerRef = useRef(null);
  const [status, setStatus] = useState("loading"); // loading | empty | unavailable | ready
  const [graphData, setGraphData] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    setGraphData(null);

    fetchGraph(caseIds)
      .then((data) => {
        if (cancelled) return;
        if (!data.available) {
          setStatus("unavailable");
          return;
        }
        if (!data.edges || data.edges.length === 0) {
          setStatus("empty");
          return;
        }
        setGraphData(data);
        setStatus("ready");
      })
      .catch(() => !cancelled && setStatus("unavailable"));

    return () => {
      cancelled = true;
    };
  }, [caseIds.join(",")]);

  useEffect(() => {
    if (status !== "ready" || !graphData || !containerRef.current) return;
    const c = CHROME[theme] ?? CHROME.dark;

    const nodes = new DataSet(
      graphData.nodes.map((n) => ({
        id: n.id,
        label: n.label,
        color: COLORS[n.group] || "#888",
        shape: n.group === "Accident" ? "star" : "dot",
        size: 18,
        font: { color: c.nodeLabel, size: 12 },
      }))
    );
    const edges = new DataSet(graphData.edges.map((e) => ({ from: e.from, to: e.to, label: e.label, arrows: "to" })));
    const network = new Network(
      containerRef.current,
      { nodes, edges },
      {
        height,
        physics: { solver: "repulsion", repulsion: { nodeDistance: 130, springLength: 150 } },
        edges: { color: c.edge, font: { color: c.edgeLabel, size: 10, strokeWidth: 0 } },
      }
    );

    return () => network.destroy();
  }, [status, graphData, height, theme]);

  if (status === "loading") return <p className="px-3.5 pb-3 text-[12px] text-fog-600">Loading graph…</p>;
  if (status === "unavailable")
    return <p className="px-3.5 pb-3 text-[12px] text-fog-600">Graph view unavailable.</p>;
  if (status === "empty") return <p className="px-3.5 pb-3 text-[12px] text-fog-600">No graph connections found for this case.</p>;
  return <div ref={containerRef} style={{ height }} className="mx-3.5 mb-3 overflow-hidden rounded-lg bg-ink-900" />;
}

export default function CausalGraph({ caseIds, theme = "dark" }) {
  const [open, setOpen] = useState(false);
  if (!caseIds || caseIds.length === 0) return null;

  return (
    <div className="overflow-hidden rounded-xl border border-ink-600 bg-ink-850">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3.5 py-2.5 text-fog-350"
      >
        <span className="text-[12.5px] font-medium">🕸 Causal graph of cited cases</span>
        <ChevronIcon open={open} />
      </button>
      {open && <GraphCanvas caseIds={caseIds.slice(0, 5)} theme={theme} />}
    </div>
  );
}
