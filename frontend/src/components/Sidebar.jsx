import { useState } from "react";
import {
  TunnelLogo,
  PanelIcon,
  PlusIcon,
  SearchIcon,
  DocIcon,
  GraphIcon,
  ReportIcon,
  SunIcon,
  MoonIcon,
  DotsIcon,
  TrashIcon,
  ACCENT,
} from "./Icons.jsx";

function DeleteConfirm({ title, onCancel, onConfirm }) {
  return (
    <div onClick={onCancel} className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-[340px] max-w-[90%] rounded-[14px] border border-ink-500 bg-ink-800 p-4 shadow-[0_20px_60px_rgba(0,0,0,0.5)] animate-fadeUp"
      >
        <p className="text-[13.5px] text-fog-200">
          Delete <span className="font-medium text-fog-50">{title}</span>? This can't be undone.
        </p>
        <div className="mt-3.5 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-lg border border-ink-500 px-3 py-1.5 text-[12.5px] text-fog-300 hover:bg-ink-700"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="rounded-lg bg-danger px-3 py-1.5 text-[12.5px] font-medium text-fog-50 hover:opacity-90"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar({
  collapsed,
  onToggleCollapsed,
  conversations,
  activeChatId,
  onSelectChat,
  onNewChat,
  onOpenSearch,
  onDeleteChat,
  docsPanelOpen,
  onToggleDocs,
  causalPanelOpen,
  onToggleCausal,
  reportPanelOpen,
  onToggleReport,
  backendOnline,
  theme,
  onToggleTheme,
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null); // {id, title} | null
  const labels = !collapsed;

  return (
    <aside
      className={`${collapsed ? "w-[72px] min-w-[72px]" : "w-[272px] min-w-[272px]"} flex flex-col overflow-hidden border-r-[0.5px] border-ink-800 bg-ink-950 transition-all duration-200 print:hidden`}
    >
      {/* Header */}
      <div
        className={`flex items-center pb-3.5 pt-[18px] ${collapsed ? "flex-col gap-2 px-0" : "justify-between px-4"}`}
      >
        <div className="flex min-w-0 items-center gap-2.5">
          <TunnelLogo />
          {labels && <span className="whitespace-nowrap text-base font-semibold tracking-tight text-fog-50">iTunnel</span>}
        </div>
        <button
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={onToggleCollapsed}
          className="flex rounded-lg p-1.5 text-fog-500 hover:bg-ink-750"
        >
          <PanelIcon />
        </button>
      </div>

      {/* Primary actions */}
      <div className="flex flex-col gap-0.5 px-3">
        <button
          onClick={onNewChat}
          className="flex items-center gap-2.5 rounded-[10px] bg-accent-wash px-3 py-2.5 text-left text-[13.5px] font-medium text-fog-100 hover:bg-accent-washHover"
        >
          <PlusIcon color={ACCENT} />
          {labels && <span>New chat</span>}
        </button>

        <button
          onClick={onOpenSearch}
          className="flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-left text-[13.5px] text-fog-350 hover:bg-ink-800"
        >
          <SearchIcon />
          {labels && <span>Search chats</span>}
        </button>

        <button
          onClick={onToggleDocs}
          className={`flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-left text-[13.5px] text-fog-350 hover:bg-ink-800 ${docsPanelOpen ? "bg-accent-wash" : ""}`}
        >
          <DocIcon />
          {labels && <span>Knowledge base</span>}
        </button>

        <button
          onClick={onToggleCausal}
          className={`flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-left text-[13.5px] text-fog-350 hover:bg-ink-800 ${causalPanelOpen ? "bg-accent-wash" : ""}`}
        >
          <GraphIcon />
          {labels && <span>Causal Analysis</span>}
        </button>

        <button
          onClick={onToggleReport}
          className={`flex items-center gap-2.5 rounded-[10px] px-3 py-2.5 text-left text-[13.5px] text-fog-350 hover:bg-ink-800 ${reportPanelOpen ? "bg-accent-wash" : ""}`}
        >
          <ReportIcon />
          {labels && <span>Prevention Report</span>}
        </button>
      </div>

      {labels && (
        <div className="mt-[18px] px-5 text-[11px] font-semibold uppercase tracking-wider text-fog-700">Recent</div>
      )}

      {/* Conversation list */}
      <nav className="flex flex-1 flex-col gap-px overflow-y-auto px-3 pb-3 pt-2">
        {conversations.map((conv) => {
          const active = conv.id === activeChatId;
          return (
            <div
              key={conv.id}
              className={`group flex w-full items-center gap-1 rounded-lg pl-2.5 pr-1 py-[5px] text-[13px] ${
                active ? "bg-accent-wash text-fog-50" : "text-fog-350 hover:bg-ink-800"
              }`}
            >
              <button
                title={conv.title}
                onClick={() => onSelectChat(conv.id)}
                className="flex min-w-0 flex-1 items-center gap-2 py-[4px] text-left"
              >
                {conv.alert && <span className="h-1.5 w-1.5 flex-none rounded-full bg-risk-dot" />}
                {labels && <span className="truncate">{conv.title}</span>}
              </button>
              {labels && onDeleteChat && (
                <button
                  title="Delete chat"
                  onClick={(e) => {
                    e.stopPropagation();
                    setPendingDelete({ id: conv.id, title: conv.title });
                  }}
                  className="flex-none rounded-md p-1.5 text-fog-600 opacity-0 hover:bg-ink-700 hover:text-danger group-hover:opacity-100"
                >
                  <TrashIcon />
                </button>
              )}
            </div>
          );
        })}
      </nav>

      {/* Theme toggle */}
      <div className="px-3 pt-2">
        <button
          onClick={onToggleTheme}
          title={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left text-[12.5px] text-fog-400 hover:bg-ink-800"
        >
          {theme === "dark" ? <SunIcon size={15} /> : <MoonIcon size={15} />}
          {labels && <span>{theme === "dark" ? "Light theme" : "Dark theme"}</span>}
        </button>
      </div>

      {/* Profile */}
      <div className="relative border-t-[0.5px] border-ink-800 p-3">
        <button
          onClick={(e) => {
            e.stopPropagation();
            setProfileOpen((v) => !v);
          }}
          className="flex w-full items-center gap-2.5 rounded-lg p-1.5 hover:bg-ink-800"
        >
          <div className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-accent text-xs font-semibold text-ink-900">
            MA
          </div>
          {labels && (
            <>
              <span className="flex-1 truncate text-left text-[13px] text-fog-300">Muritala Adebayo</span>
              <span
                title={backendOnline ? "Backend connected" : "Backend offline — demo mode"}
                className={`h-2 w-2 flex-none rounded-full ${backendOnline ? "bg-emerald-400" : "bg-fog-800"}`}
              />
              <DotsIcon />
            </>
          )}
        </button>

        {profileOpen && (
          <div
            onClick={(e) => e.stopPropagation()}
            className="absolute bottom-14 left-3 z-20 flex w-[200px] flex-col gap-0.5 rounded-[10px] border border-ink-500 bg-ink-750 p-1.5 shadow-[0_8px_24px_rgba(0,0,0,0.4)]"
          >
            {["Account settings", "Safety preferences", "Help & documentation"].map((item) => (
              <div key={item} className="cursor-pointer rounded-md px-2.5 py-2 text-[12.5px] text-fog-300 hover:bg-ink-650">
                {item}
              </div>
            ))}
            <div className="mx-0.5 my-1 h-px bg-ink-500" />
            <div className="cursor-pointer rounded-md px-2.5 py-2 text-[12.5px] text-danger hover:bg-ink-650">Sign out</div>
          </div>
        )}
      </div>

      {pendingDelete && (
        <DeleteConfirm
          title={pendingDelete.title}
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            onDeleteChat(pendingDelete.id);
            setPendingDelete(null);
          }}
        />
      )}
    </aside>
  );
}
