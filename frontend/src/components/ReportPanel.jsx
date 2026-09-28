import { useEffect, useState } from "react";
import { CloseIcon, ReportIcon, ACCENT } from "./Icons.jsx";
import { fetchWorkProcesses, generateReport } from "../api.js";

const TUNNEL_TYPES = ["도로터널", "철도터널", "지하차도", "기타"];
const BUCKET_LABELS = { man: "Man (인력)", machine: "Machine (기계)", material: "Material (재료)", method: "Method (방법)" };
const BUCKET_ORDER = ["man", "machine", "material", "method"];

function Select({ label, value, onChange, children }) {
  return (
    <label className="flex flex-col gap-1.5 text-[12px] text-fog-500">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-lg border border-ink-500 bg-ink-800 px-3 py-2 text-[13px] text-fog-100 outline-none focus:border-ink-300"
      >
        {children}
      </select>
    </label>
  );
}

function RiskSummary({ summary }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-[13px] font-semibold text-fog-100">Historical risk summary</h3>
      <p className="text-[12.5px] text-fog-500">
        {summary.total_cases} case{summary.total_cases === 1 ? "" : "s"} on record for this work process
        {summary.total_fatalities > 0 && (
          <span className="text-risk-text"> · {summary.total_fatalities} involved fatalities</span>
        )}
      </p>
      <div className="overflow-hidden rounded-xl border border-ink-600">
        <table className="w-full text-left text-[12.5px]">
          <thead>
            <tr className="bg-ink-850 text-fog-500">
              <th className="px-3 py-2 font-medium">Accident type</th>
              <th className="px-3 py-2 font-medium">Cases</th>
              <th className="px-3 py-2 font-medium">Fatalities</th>
            </tr>
          </thead>
          <tbody>
            {summary.by_accident_type.map((row) => (
              <tr key={row.accident_type} className="print-avoid-break border-t border-ink-600/60 text-fog-300">
                <td className="px-3 py-2">{row.accident_type}</td>
                <td className="px-3 py-2">{row.count}</td>
                <td className="px-3 py-2">{row.fatalities > 0 ? <span className="text-risk-text">{row.fatalities}</span> : 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function CausesJHA({ causes, available }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-[13px] font-semibold text-fog-100">Root-cause breakdown</h3>
      {!available && <p className="text-[12.5px] text-fog-600">Graph store unavailable — cause hierarchy omitted.</p>}
      {available && causes.length === 0 && <p className="text-[12.5px] text-fog-600">No cause data linked for this work process.</p>}
      <div className="flex flex-col gap-[7px]">
        {causes.map((c, i) => (
          <div key={i} className="print-avoid-break rounded-lg border border-ink-600 bg-ink-850 px-3 py-2 text-[12.5px]">
            <span className="text-fog-500">{c.l1}</span>
            <span className="mx-1.5 text-fog-700">›</span>
            <span className="text-fog-400">{c.l2}</span>
            <span className="mx-1.5 text-fog-700">›</span>
            <span className="font-medium text-fog-100">{c.l3}</span>
            <span className="ml-2 text-fog-600">({c.n} case{c.n === 1 ? "" : "s"})</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function Causes4M({ causes, available }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-[13px] font-semibold text-fog-100">유해위험요인 파악 (4M)</h3>
      {!available && <p className="text-[12.5px] text-fog-600">Graph store unavailable — 4M breakdown omitted.</p>}
      {available && (
        <div className="grid grid-cols-2 gap-3">
          {BUCKET_ORDER.map((bucket) => (
            <div key={bucket} className="print-avoid-break rounded-lg border border-ink-600 bg-ink-850 p-3">
              <p className="mb-1.5 text-[12px] font-semibold text-fog-200">{BUCKET_LABELS[bucket]}</p>
              {causes[bucket].length === 0 ? (
                <p className="text-[11.5px] text-fog-700">No matches</p>
              ) : (
                <ul className="flex flex-col gap-1">
                  {causes[bucket].map((c, i) => (
                    <li key={i} className="text-[11.5px] text-fog-400">
                      {c.category} <span className="text-fog-700">({c.dimension === "cause" ? "원인" : "대상물"} · {c.count})</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function MeasureCard({ m }) {
  return (
    <div className="print-avoid-break rounded-lg border border-ink-600 bg-ink-850 px-3 py-2.5 text-[12.5px]">
      <p className="mb-1 flex items-center gap-2">
        <span className="font-medium text-accent">{m.case_id}</span>
        <span className="text-fog-600">{m.accident_type}</span>
        {m.fatalities > 0 && <span className="text-risk-text">⚠ 사망사고</span>}
      </p>
      <p className="text-fog-400">{m.prevention}</p>
    </div>
  );
}

function MeasuresJHA({ measures }) {
  return (
    <section className="flex flex-col gap-2">
      <h3 className="text-[13px] font-semibold text-fog-100">Grounded prevention measures</h3>
      <div className="flex flex-col gap-2">
        {measures.map((m) => <MeasureCard key={m.case_id} m={m} />)}
      </div>
    </section>
  );
}

function Measures4M({ measures }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-[13px] font-semibold text-fog-100">감소대책 (Reduction measures, by 4M)</h3>
      {BUCKET_ORDER.filter((b) => measures[b].length > 0).map((bucket) => (
        <div key={bucket} className="flex flex-col gap-2">
          <p className="text-[12px] font-semibold text-fog-300">{BUCKET_LABELS[bucket]}</p>
          {measures[bucket].map((m) => <MeasureCard key={m.case_id} m={m} />)}
        </div>
      ))}
    </section>
  );
}

export default function ReportPanel({ onClose }) {
  const [workProcesses, setWorkProcesses] = useState([]);
  const [workProcess, setWorkProcess] = useState("");
  const [tunnelType, setTunnelType] = useState("");
  const [format, setFormat] = useState("jha");
  const [status, setStatus] = useState("idle"); // idle | loading | ready | error
  const [data, setData] = useState(null);

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    fetchWorkProcesses()
      .then((wps) => {
        setWorkProcesses(wps);
        if (wps.length) setWorkProcess(wps[0]);
      })
      .catch(() => {});
  }, []);

  const onGenerate = async () => {
    if (!workProcess) return;
    setStatus("loading");
    try {
      const report = await generateReport({ workProcess, tunnelType, format });
      setData(report);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div
      onClick={onClose}
      className="report-print-root absolute inset-0 z-40 flex items-center justify-center bg-black/60 p-8 print:bg-white print:p-0"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="report-print-card flex h-[85vh] w-full max-w-[900px] flex-col overflow-hidden rounded-[18px] border border-ink-500 bg-ink-950 shadow-[0_20px_60px_rgba(0,0,0,0.5)] animate-fadeUp print:h-auto print:max-w-none print:border-none print:shadow-none"
      >
        <div className="flex items-center justify-between border-b-[0.5px] border-ink-800 px-6 py-4 print:hidden">
          <h2 className="flex items-center gap-2 text-[15px] font-semibold text-fog-100">
            <ReportIcon size={18} color={ACCENT} />
            Prevention Report
          </h2>
          <button onClick={onClose} className="rounded-md p-1.5 text-fog-600 hover:bg-ink-750">
            <CloseIcon />
          </button>
        </div>

        <div className="report-print-body flex-1 overflow-y-auto px-6 py-5">
          {/* Form */}
          <div className="mb-5 flex flex-wrap items-end gap-3 print:hidden">
            <Select label="Work process (작업프로세스)" value={workProcess} onChange={setWorkProcess}>
              {workProcesses.map((wp) => (
                <option key={wp} value={wp}>{wp}</option>
              ))}
            </Select>
            <Select label="Tunnel type (터널분류)" value={tunnelType} onChange={setTunnelType}>
              <option value="">All types</option>
              {TUNNEL_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </Select>
            <Select label="Format" value={format} onChange={setFormat}>
              <option value="jha">JHA (Job Hazard Analysis)</option>
              <option value="krisk">위험성평가 (4M)</option>
            </Select>
            <button
              onClick={onGenerate}
              disabled={!workProcess || status === "loading"}
              className="rounded-lg bg-accent px-4 py-2 text-[13px] font-medium text-ink-900 hover:bg-accent-bright disabled:opacity-40"
            >
              {status === "loading" ? "Generating…" : "Generate"}
            </button>
            {data && (
              <button
                onClick={() => window.print()}
                className="rounded-lg border border-ink-500 px-4 py-2 text-[13px] text-fog-300 hover:bg-ink-800"
              >
                Print / Export
              </button>
            )}
          </div>

          {status === "error" && <p className="text-[13px] text-danger">Couldn't generate the report — check that the backend is running.</p>}

          {data && (
            <div className="report-print-area flex flex-col gap-6">
              <div>
                <h1 className="text-[17px] font-semibold text-fog-50">
                  {data.work_process}
                  {data.tunnel_type && <span className="text-fog-500"> · {data.tunnel_type}</span>}
                </h1>
                <p className="text-[11.5px] text-fog-700">
                  {data.format === "jha" ? "Job Hazard Analysis format" : "위험성평가 (4M) format"} · generated {new Date().toLocaleString()}
                </p>
              </div>

              <RiskSummary summary={data.risk_summary} />

              {data.format === "jha" ? (
                <>
                  <CausesJHA causes={data.causes} available={data.causes_available} />
                  <MeasuresJHA measures={data.measures} />
                </>
              ) : (
                <>
                  <Causes4M causes={data.causes} available={data.causes_available} />
                  <Measures4M measures={data.measures} />
                </>
              )}

              <p className="border-t border-ink-800 pt-3 text-[11.5px] leading-relaxed text-fog-700">
                This report is a grounded reference compiled from {data.risk_summary.total_cases} historical case
                {data.risk_summary.total_cases === 1 ? "" : "s"} in the accident database — it is a planning input
                for a human safety planner, not a substitute for the formal 유해위험방지계획서 (Hazard Prevention
                Plan) or a real on-site incident investigation.
              </p>
            </div>
          )}

          {!data && status !== "loading" && status !== "error" && (
            <p className="text-[12.5px] text-fog-700">Select a work process and click Generate to build a reference report.</p>
          )}
        </div>
      </div>
    </div>
  );
}
