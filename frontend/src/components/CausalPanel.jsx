import { useEffect } from "react";
import { CloseIcon, GraphIcon, ACCENT } from "./Icons.jsx";
import { GraphCanvas } from "./CausalGraph.jsx";

export default function CausalPanel({ caseIds, theme = "dark", onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div onClick={onClose} className="absolute inset-0 z-40 flex items-center justify-center bg-black/60 p-8">
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex h-[85vh] w-full max-w-[1100px] flex-col overflow-hidden rounded-[18px] border border-ink-500 bg-ink-950 shadow-[0_20px_60px_rgba(0,0,0,0.5)] animate-fadeUp"
      >
        <div className="flex items-center justify-between border-b-[0.5px] border-ink-800 px-6 py-4">
          <h2 className="text-[15px] font-semibold text-fog-100">Causal Analysis</h2>
          <button onClick={onClose} className="rounded-md p-1.5 text-fog-600 hover:bg-ink-750">
            <CloseIcon />
          </button>
        </div>

        {caseIds.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 px-8 text-center">
            <GraphIcon size={32} color={ACCENT} sw={1.4} />
            <p className="max-w-sm text-[13px] leading-relaxed text-fog-700">
              Ask a question that cites specific accident cases, then reopen this panel to see how they connect —
              tunnel type, work process, and root cause.
            </p>
          </div>
        ) : (
          <div className="flex flex-1 flex-col overflow-hidden px-5 pb-5 pt-3">
            <p className="px-1 pb-2 text-[12px] text-fog-700">
              Showing the causal graph for the most recently cited case{caseIds.length > 1 ? "s" : ""}:{" "}
              <span className="text-fog-400">{caseIds.join(", ")}</span>
            </p>
            <div className="min-h-0 flex-1">
              <GraphCanvas caseIds={caseIds} height="100%" theme={theme} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
