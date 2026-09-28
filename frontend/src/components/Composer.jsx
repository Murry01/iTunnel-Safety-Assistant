import { useRef, useEffect } from "react";
import { AttachIcon, MicIcon, SendIcon, StopIcon } from "./Icons.jsx";

export default function Composer({ value, onChange, onSend, onStop, busy, maxWidth = "max-w-[780px]", withVoice = true, autoFocus = false }) {
  const ref = useRef(null);

  // Auto-grow textarea up to ~6 lines
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div
      className={`mx-auto flex w-full ${maxWidth} items-end gap-2 rounded-[22px] border border-ink-500 bg-ink-800 py-[9px] pl-4 pr-2.5 focus-within:border-ink-400`}
    >
      <button title="Attach files" className="flex-none rounded-lg p-[7px] text-fog-500 hover:bg-ink-700" tabIndex={-1}>
        <AttachIcon />
      </button>
      <textarea
        ref={ref}
        rows={1}
        value={value}
        autoFocus={autoFocus}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask iTunnel about tunnel safety, standards, incidents…"
        className="min-w-0 flex-1 resize-none self-center bg-transparent py-1 font-sans text-sm leading-relaxed text-fog-100 placeholder:text-fog-700"
      />
      {withVoice && (
        <button title="Voice input" className="flex-none rounded-lg p-[7px] text-fog-500 hover:bg-ink-700" tabIndex={-1}>
          <MicIcon />
        </button>
      )}
      <button
        title={busy ? "Stop generating" : "Send"}
        onClick={() => (busy ? onStop() : onSend())}
        disabled={!busy && !value.trim()}
        className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-accent text-ink-900 transition hover:bg-accent-bright disabled:cursor-default disabled:opacity-40"
      >
        {busy ? <StopIcon /> : <SendIcon />}
      </button>
    </div>
  );
}
