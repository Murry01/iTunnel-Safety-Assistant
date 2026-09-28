import { DocIcon, PlusIcon } from "./Icons.jsx";

export default function TopBar({ docsPanelOpen, onToggleDocs, onNewChat }) {
  return (
    <header className="flex items-center justify-end border-b-[0.5px] border-ink-800 px-[22px] py-3.5">
      <div className="flex items-center gap-1.5">
        <button
          title="Knowledge base"
          onClick={onToggleDocs}
          className={`flex items-center gap-1.5 rounded-full border border-ink-500 px-3 py-[7px] text-[12.5px] text-fog-300 hover:bg-ink-700 ${
            docsPanelOpen ? "bg-accent-wash" : ""
          }`}
        >
          <DocIcon size={14} sw={1.6} lines={false} />
          <span>Sources</span>
        </button>
        <button title="New chat" onClick={onNewChat} className="rounded-lg p-2 text-fog-400 hover:bg-ink-750">
          <PlusIcon />
        </button>
      </div>
    </header>
  );
}
