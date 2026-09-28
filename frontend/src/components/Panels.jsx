import { TunnelLogo, CloseIcon, SearchIcon, ChatLineIcon, DocIcon, ACCENT } from "./Icons.jsx";
import Composer from "./Composer.jsx";
import { SUGGESTIONS } from "../data/demo.js";

/* ── Welcome / empty state ── */

export function WelcomeScreen({ composerText, setComposerText, onSend, onStop, busy }) {
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-[26px] p-5">
      <div className="flex flex-col items-center gap-3.5 animate-fadeUp">
        <TunnelLogo size={42} sw={1.8} />
        <h1 className="text-center text-[26px] font-semibold tracking-tight text-fog-100">
          {greeting}, Muritala — what's the plan?
        </h1>
      </div>
      <Composer
        value={composerText}
        onChange={setComposerText}
        onSend={onSend}
        onStop={onStop}
        busy={busy}
        maxWidth="max-w-[680px]"
        withVoice={false}
        autoFocus
      />
      <div className="flex max-w-[680px] flex-wrap justify-center gap-2.5">
        {SUGGESTIONS.map((label) => (
          <button
            key={label}
            onClick={() => setComposerText(label)}
            className="rounded-[14px] border border-ink-600 bg-ink-800 px-3.5 py-[9px] text-[12.5px] text-fog-350 hover:bg-ink-700"
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Knowledge base panel ── */

const TAG_STYLES = {
  critical: "text-risk-text bg-risk-bg",
  spec: "text-accent-tagText bg-accent-tagBg",
  incident: "text-fog-350 bg-ink-500/60",
};

export function KnowledgePanel({ documents, onClose }) {
  return (
    <aside className="flex w-[300px] min-w-[300px] flex-col border-l border-ink-600/50 bg-ink-950">
      <div className="flex items-center justify-between px-[18px] pb-3 pt-4">
        <h2 className="text-[13.5px] font-semibold text-fog-100">Knowledge base</h2>
        <button onClick={onClose} className="rounded-md p-1 text-fog-600 hover:bg-ink-750">
          <CloseIcon />
        </button>
      </div>
      <p className="px-[18px] pb-3 text-[11.5px] text-fog-700">Indexed documents grounding this assistant's answers.</p>
      <div className="flex flex-1 flex-col gap-[7px] overflow-y-auto px-3 pb-4">
        {documents.map((doc) => (
          <div key={doc.name} className="flex flex-col gap-1.5 rounded-[10px] border border-ink-600 bg-ink-850 px-3 py-[11px]">
            <div className="flex items-start gap-2">
              <span className="mt-px flex">
                <DocIcon size={14} color={ACCENT} lines={false} />
              </span>
              <span className="text-[12.5px] font-medium leading-snug text-fog-300">{doc.name}</span>
            </div>
            <div className="flex items-center gap-1.5 pl-[22px]">
              <span
                className={`rounded-md px-[7px] py-0.5 text-[10px] font-semibold tracking-wide ${TAG_STYLES[doc.color] || TAG_STYLES.incident}`}
              >
                {doc.tag}
              </span>
              <span className="text-[10.5px] text-fog-800">{doc.meta}</span>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

/* ── Search modal ── */

export function SearchModal({ query, setQuery, results, onSelect, onClose }) {
  return (
    <div
      onClick={onClose}
      className="absolute inset-0 z-40 flex items-start justify-center bg-black/50 pt-[90px]"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[560px] max-w-[90%] overflow-hidden rounded-[14px] border border-ink-500 bg-ink-800 shadow-[0_20px_60px_rgba(0,0,0,0.5)] animate-fadeUp"
      >
        <div className="flex items-center gap-2.5 border-b border-ink-600 px-4 py-3.5 text-fog-500">
          <SearchIcon />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && onClose()}
            placeholder="Search chats…"
            autoFocus
            className="min-w-0 flex-1 bg-transparent font-sans text-[14.5px] text-fog-100 placeholder:text-fog-700"
          />
        </div>
        <div className="max-h-[340px] overflow-y-auto p-2">
          {results.length === 0 ? (
            <div className="px-3 py-4 text-center text-[13px] text-fog-600">No chats match "{query}"</div>
          ) : (
            results.map((r) => (
              <button
                key={r.id}
                onClick={() => onSelect(r.id)}
                className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-[13px] text-fog-300 hover:bg-ink-650"
              >
                <ChatLineIcon />
                <span className="truncate">{r.title}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
