import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { TunnelLogo, ChevronIcon, WarningIcon, CopyIcon, CheckIcon, RegenIcon, ThumbIcon, DocIcon, ACCENT } from "./Icons.jsx";

function ActionButton({ title, onClick, activeState, children }) {
  return (
    <button
      title={title}
      onClick={onClick}
      className={`rounded-md p-1.5 hover:bg-ink-750 hover:text-fog-300 ${activeState ? "text-accent" : "text-fog-600"}`}
    >
      {children}
    </button>
  );
}

export function UserMessage({ text }) {
  return (
    <div className="flex justify-end animate-fadeUp">
      <div className="max-w-[74%] whitespace-pre-line rounded-2xl bg-accent-bubble px-4 py-[11px] text-[14.5px] leading-[1.55] text-fog-50">
        {text}
      </div>
    </div>
  );
}

export function AssistantMessage({ msg, defaultTraceOpen = false, onRegenerate, onFollowUp }) {
  const [traceOpen, setTraceOpen] = useState(defaultTraceOpen);
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState(null);

  const hasTrace = msg.steps && msg.steps.length > 0;
  const hasSources = msg.sources && msg.sources.length > 0;
  const hasFollowUps = onFollowUp && msg.followUps && msg.followUps.length > 0;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(msg.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="flex gap-3 animate-fadeUp">
      <div className="mt-0.5 flex h-[26px] w-[26px] flex-none items-center justify-center rounded-lg bg-accent-deep">
        <TunnelLogo size={14} feet={false} sw={2.4} />
      </div>

      <div className="flex min-w-0 flex-1 flex-col gap-3">
        {hasTrace && (
          <div className="overflow-hidden rounded-xl border border-ink-600 bg-ink-850">
            <button
              onClick={() => setTraceOpen((v) => !v)}
              className="flex w-full items-center justify-between px-3.5 py-2.5 text-fog-350"
            >
              <span className="text-[12.5px] font-medium">Agent reasoning · {msg.steps.length} steps</span>
              <ChevronIcon open={traceOpen} />
            </button>
            {traceOpen && (
              <div className="flex flex-col gap-[9px] px-3.5 pb-3 pt-0.5">
                {msg.steps.map((step, i) => (
                  <div key={i} className="flex items-start gap-[9px]">
                    <span className="mt-1.5 h-[5px] w-[5px] flex-none rounded-full bg-fog-600" />
                    <span className="text-[12.5px] leading-normal text-fog-400">{step}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {msg.riskLevel && (
          <div className="flex items-center gap-[9px] rounded-[10px] bg-risk-bg px-3.5 py-2.5">
            <WarningIcon />
            <span className="text-[12.5px] font-semibold text-risk-text">{msg.riskLevel}</span>
          </div>
        )}

        {msg.error ? (
          <div className="rounded-[10px] border border-danger/30 bg-danger/10 px-3.5 py-2.5 text-[13px] text-danger">
            {msg.text}
          </div>
        ) : (
          <div className="md">
            <ReactMarkdown>{msg.text}</ReactMarkdown>
          </div>
        )}

        {hasSources && (
          <div className="flex gap-2.5 overflow-x-auto pb-0.5">
            {msg.sources.map((src, i) => (
              <div
                key={i}
                className="flex w-[230px] flex-none cursor-default flex-col gap-[5px] rounded-[10px] border border-ink-600 bg-ink-850 px-3 py-[11px] transition hover:border-ink-400"
              >
                <div className="flex items-center gap-1.5">
                  <DocIcon size={12} color={ACCENT} sw={1.8} lines={false} />
                  <span className="truncate text-[11.5px] font-semibold text-fog-300">{src.doc}</span>
                </div>
                {src.section && <div className="font-mono text-[10.5px] text-fog-600">{src.section}</div>}
                <div className="line-clamp-2 text-[11.5px] leading-snug text-fog-500">{src.snippet}</div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-0.5 flex items-center gap-0.5">
          <ActionButton title={copied ? "Copied!" : "Copy"} onClick={copy} activeState={copied}>
            {copied ? <CheckIcon /> : <CopyIcon />}
          </ActionButton>
          {onRegenerate && (
            <ActionButton title="Regenerate" onClick={onRegenerate}>
              <RegenIcon />
            </ActionButton>
          )}
          <ActionButton title="Good response" onClick={() => setVote(vote === "up" ? null : "up")} activeState={vote === "up"}>
            <ThumbIcon />
          </ActionButton>
          <ActionButton title="Poor response" onClick={() => setVote(vote === "down" ? null : "down")} activeState={vote === "down"}>
            <ThumbIcon down />
          </ActionButton>
        </div>

        {hasFollowUps && (
          <div className="flex flex-wrap gap-2">
            {msg.followUps.map((q, i) => (
              <button
                key={i}
                onClick={() => onFollowUp(q)}
                className="rounded-full border border-ink-600 bg-ink-850 px-3.5 py-[7px] text-left text-[12.5px] text-fog-350 transition hover:border-ink-400 hover:text-fog-100"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function ThinkingIndicator() {
  return (
    <div className="flex gap-3 animate-fadeUp">
      <div className="mt-0.5 flex h-[26px] w-[26px] flex-none items-center justify-center rounded-lg bg-accent-deep">
        <TunnelLogo size={14} feet={false} sw={2.4} />
      </div>
      <div className="flex items-center gap-[5px] pt-2">
        {[0, 1, 2].map((d) => (
          <span
            key={d}
            className="h-1.5 w-1.5 rounded-full bg-fog-500 animate-pulseDot"
            style={{ animationDelay: `${d * 0.2}s` }}
          />
        ))}
        <span className="ml-2 text-[12.5px] text-fog-600">Retrieving from knowledge base…</span>
      </div>
    </div>
  );
}
