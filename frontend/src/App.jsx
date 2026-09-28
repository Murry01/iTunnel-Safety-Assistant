import { useState, useRef, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar.jsx";
import TopBar from "./components/TopBar.jsx";
import Composer from "./components/Composer.jsx";
import { UserMessage, AssistantMessage, ThinkingIndicator } from "./components/MessageBubble.jsx";
import { WelcomeScreen, KnowledgePanel, SearchModal } from "./components/Panels.jsx";
import CausalGraph from "./components/CausalGraph.jsx";
import CausalPanel from "./components/CausalPanel.jsx";
import ReportPanel from "./components/ReportPanel.jsx";
import ChartView from "./components/ChartView.jsx";
import {
  checkHealth,
  fetchDocuments,
  listConversations,
  loadMessages,
  deleteConversationRequest,
  fetchCases,
  streamChat,
  demoReply,
} from "./api.js";
import { DEMO_DOCS, MODES } from "./data/demo.js";

function getInitialTheme() {
  const saved = localStorage.getItem("theme");
  return saved === "light" ? "light" : "dark"; // default dark — no surprise appearance change
}

export default function App() {
  const [theme, setTheme] = useState(getInitialTheme);
  const [conversations, setConversations] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [docsPanelOpen, setDocsPanelOpen] = useState(false);
  const [causalPanelOpen, setCausalPanelOpen] = useState(false);
  const [reportPanelOpen, setReportPanelOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const mode = MODES[1]; // Deep Reasoning — fixed; no UI selector (backend doesn't act on it yet)
  const [composerText, setComposerText] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [thinking, setThinking] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [documents, setDocuments] = useState(DEMO_DOCS);

  // live streaming preview for the in-flight turn
  const [liveTrace, setLiveTrace] = useState([]);
  const [liveText, setLiveText] = useState("");
  const [liveCharts, setLiveCharts] = useState([]);

  const scrollRef = useRef(null);
  const abortRef = useRef(null);

  const active = conversations.find((c) => c.id === activeChatId) || null;

  const appendMessage = useCallback((chatId, message) => {
    setConversations((cs) => cs.map((c) => (c.id === chatId ? { ...c, messages: [...(c.messages || []), message] } : c)));
  }, []);

  const selectChat = useCallback(
    async (id) => {
      setSearchOpen(false);
      setActiveChatId(id);
      const existing = conversations.find((c) => c.id === id);
      if (existing && existing.messages) return; // already hydrated this session

      try {
        const raw = await loadMessages(id);
        const messages = raw.map((m) => ({
          role: m.role,
          text: m.content,
          caseIds: m.case_ids || [],
          charts: m.charts || [],
          sources: undefined,
          steps: undefined,
          riskLevel: null,
        }));
        setConversations((cs) => cs.map((c) => (c.id === id ? { ...c, messages } : c)));

        // progressively fill in citation cards (a second round trip per
        // cited message, not blocking the messages from rendering first)
        messages.forEach((m, i) => {
          if (m.role !== "assistant" || !m.caseIds.length) return;
          fetchCases(m.caseIds)
            .then((cases) => {
              const sources = cases.map((c) => ({
                doc: `${c.case_id} · ${c.accident_type}`,
                section: c.work_process,
                snippet: c.narrative,
              }));
              setConversations((cs) =>
                cs.map((c) => {
                  if (c.id !== id) return c;
                  const msgs = [...c.messages];
                  msgs[i] = { ...msgs[i], sources };
                  return { ...c, messages: msgs };
                })
              );
            })
            .catch(() => {});
        });
      } catch {
        setConversations((cs) => cs.map((c) => (c.id === id ? { ...c, messages: c.messages || [] } : c)));
      }
    },
    [conversations]
  );

  /* Backend health, conversation history, and knowledge base on load */
  useEffect(() => {
    (async () => {
      const online = await checkHealth();
      setBackendOnline(online);
      if (!online) return;

      try {
        const convos = await listConversations();
        const mapped = convos.map((c) => ({ id: c.id, title: c.title, alert: false }));
        setConversations(mapped);
        // Deliberately not auto-selecting the most recent conversation here —
        // every fresh page load (new tab, new browser, refresh) should land
        // on the empty "what's the plan?" screen, same as ChatGPT/Claude/
        // Gemini. History is still fully available in the sidebar for the
        // user to click into; nothing about persistence changes.
      } catch {
        /* stay on empty state */
      }
      try {
        const docs = await fetchDocuments();
        if (Array.isArray(docs) && docs.length) setDocuments(docs);
      } catch {
        /* keep demo docs */
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Auto-scroll on new messages */
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [activeChatId, active?.messages?.length, thinking, liveText, liveTrace.length]);

  /* Theme: toggle the .light class on <html> and persist the choice */
  useEffect(() => {
    document.documentElement.classList.toggle("light", theme === "light");
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  const newChat = () => {
    setActiveChatId(null);
    setComposerText("");
  };

  const deleteChat = async (id) => {
    try {
      await deleteConversationRequest(id);
    } catch {
      /* best effort — still remove locally */
    }
    setConversations((cs) => cs.filter((c) => c.id !== id));
    if (activeChatId === id) setActiveChatId(null);
  };

  const stopGeneration = () => {
    abortRef.current?.abort();
  };

  const runAssistant = useCallback(
    async (chatId, userText, history) => {
      setThinking(true);
      setLiveTrace([]);
      setLiveText("");
      setLiveCharts([]);

      if (!backendOnline) {
        const reply = await demoReply(mode.id);
        appendMessage(chatId, { role: "assistant", ...reply });
        setThinking(false);
        return;
      }

      const trace = [];
      const charts = [];
      let finalText = "";
      let caseIds = [];
      let followUps = [];
      let resolvedChatId = chatId;

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(
          { message: userText, mode: mode.id, conversationId: chatId, history },
          (event) => {
            if (event.type === "conversation" && !chatId) {
              resolvedChatId = event.conversation_id;
              chatId = resolvedChatId;
              setActiveChatId(resolvedChatId);
              setConversations((cs) => [
                { id: resolvedChatId, title: event.title || userText, alert: false, messages: [{ role: "user", text: userText }] },
                ...cs,
              ]);
            } else if (event.type === "status") {
              trace.push(event.text);
              setLiveTrace([...trace]);
            } else if (event.type === "tool_call") {
              trace.push(`Using ${event.name}…`);
              setLiveTrace([...trace]);
            } else if (event.type === "tool_result") {
              trace.push(`${event.name} returned ${event.count} result(s)`);
              setLiveTrace([...trace]);
            } else if (event.type === "chart") {
              charts.push(event.spec);
              setLiveCharts([...charts]);
            } else if (event.type === "delta") {
              finalText += event.text;
              setLiveText((t) => t + event.text);
            } else if (event.type === "error") {
              finalText += `\n\n⚠️ ${event.text}`;
              setLiveText((t) => t + `\n\n⚠️ ${event.text}`);
            } else if (event.type === "done") {
              finalText = event.answer || finalText;
              caseIds = event.case_ids || [];
            } else if (event.type === "follow_ups") {
              followUps = event.questions || [];
            }
          },
          controller.signal
        );
      } catch (err) {
        abortRef.current = null;
        if (err.name === "AbortError") {
          finalText = finalText || "_Generation stopped._";
        } else {
          appendMessage(resolvedChatId, {
            role: "assistant",
            text: `Couldn't get a response from the backend: ${err.message}. Check that the server is running, then try again.`,
            error: true,
            steps: [],
            sources: [],
          });
          setThinking(false);
          setLiveTrace([]);
          setLiveText("");
          setLiveCharts([]);
          return;
        }
      }
      abortRef.current = null;

      let sources = [];
      if (caseIds.length) {
        try {
          const cases = await fetchCases(caseIds);
          sources = cases.map((c) => ({
            doc: `${c.case_id} · ${c.accident_type}`,
            section: c.work_process,
            snippet: c.narrative,
          }));
        } catch {
          /* show the answer without citation cards */
        }
      }

      appendMessage(resolvedChatId, {
        role: "assistant",
        text: finalText,
        steps: trace,
        sources,
        caseIds,
        charts,
        followUps,
        riskLevel: null,
      });

      setThinking(false);
      setLiveTrace([]);
      setLiveText("");
      setLiveCharts([]);

      try {
        const convos = await listConversations();
        setConversations((cs) => {
          const withMessages = new Map(cs.map((c) => [c.id, c.messages]));
          return convos.map((c) => ({ id: c.id, title: c.title, alert: false, messages: withMessages.get(c.id) }));
        });
      } catch {
        /* sidebar just won't reorder until next successful refresh */
      }
    },
    [backendOnline, mode, appendMessage]
  );

  const sendMessage = (overrideText) => {
    const text = (overrideText ?? composerText).trim();
    if (!text || thinking) return;
    if (overrideText === undefined) setComposerText("");

    const chatId = activeChatId;
    let history = [];

    if (chatId) {
      history = (active ? active.messages : []).slice(-6).map((m) => ({ role: m.role, content: m.text }));
      appendMessage(chatId, { role: "user", text });
    }

    runAssistant(chatId, text, history);
  };

  const regenerate = (chatId) => {
    const conv = conversations.find((c) => c.id === chatId);
    if (!conv || thinking) return;
    const lastUserIdx = [...conv.messages].map((m) => m.role).lastIndexOf("user");
    if (lastUserIdx === -1) return;
    const userText = conv.messages[lastUserIdx].text;
    const trimmed = conv.messages.slice(0, lastUserIdx + 1);
    const history = trimmed.slice(0, -1).map((m) => ({ role: m.role, content: m.text }));
    setConversations((cs) => cs.map((c) => (c.id === chatId ? { ...c, messages: trimmed } : c)));
    runAssistant(chatId, userText, history);
  };

  const searchResults = conversations.filter((c) => c.title.toLowerCase().includes(searchQuery.toLowerCase()));

  const lastCitedCaseIds = active?.messages
    ? [...active.messages].reverse().find((m) => m.role === "assistant" && m.caseIds && m.caseIds.length > 0)?.caseIds || []
    : [];

  const toggleDocs = () => {
    setDocsPanelOpen((v) => !v);
    setCausalPanelOpen(false);
    setReportPanelOpen(false);
  };
  const toggleCausal = () => {
    setCausalPanelOpen((v) => !v);
    setDocsPanelOpen(false);
    setReportPanelOpen(false);
  };
  const toggleReport = () => {
    setReportPanelOpen((v) => !v);
    setDocsPanelOpen(false);
    setCausalPanelOpen(false);
  };

  return (
    <div className="relative flex h-screen w-full overflow-hidden bg-ink-900 font-sans text-fog-50 print:block print:h-auto print:overflow-visible">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapsed={() => setSidebarCollapsed((v) => !v)}
        conversations={conversations}
        activeChatId={activeChatId}
        onSelectChat={selectChat}
        onNewChat={newChat}
        onOpenSearch={() => {
          setSearchOpen(true);
          setSearchQuery("");
        }}
        onDeleteChat={deleteChat}
        docsPanelOpen={docsPanelOpen}
        onToggleDocs={toggleDocs}
        causalPanelOpen={causalPanelOpen}
        onToggleCausal={toggleCausal}
        reportPanelOpen={reportPanelOpen}
        onToggleReport={toggleReport}
        backendOnline={backendOnline}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main className="relative flex min-w-0 flex-1 flex-col print:hidden">
        <TopBar docsPanelOpen={docsPanelOpen} onToggleDocs={toggleDocs} onNewChat={newChat} />

        {active ? (
          <>
            <div ref={scrollRef} className="flex-1 overflow-y-auto pb-2.5 pt-7">
              <div className="mx-auto flex max-w-[780px] flex-col gap-[30px] px-6">
                {(active.messages || []).map((msg, i) =>
                  msg.role === "user" ? (
                    <UserMessage key={i} text={msg.text} />
                  ) : (
                    <div key={i} className="flex flex-col gap-3">
                      <AssistantMessage
                        msg={msg}
                        defaultTraceOpen={false}
                        onRegenerate={i === active.messages.length - 1 ? () => regenerate(active.id) : null}
                        onFollowUp={i === active.messages.length - 1 ? (q) => sendMessage(q) : null}
                      />
                      {msg.caseIds && msg.caseIds.length > 0 && (
                        <div className="pl-[38px]">
                          <CausalGraph caseIds={msg.caseIds} theme={theme} />
                        </div>
                      )}
                      {(msg.charts || []).map((spec, ci) => (
                        <div key={ci} className="pl-[38px]">
                          <ChartView spec={spec} theme={theme} />
                        </div>
                      ))}
                    </div>
                  )
                )}

                {thinking && (
                  <>
                    {liveTrace.length === 0 && liveText === "" ? (
                      <ThinkingIndicator />
                    ) : (
                      <AssistantMessage msg={{ text: liveText, steps: liveTrace, sources: [], riskLevel: null }} defaultTraceOpen />
                    )}
                    {liveCharts.map((spec, ci) => (
                      <div key={ci} className="pl-[38px]">
                        <ChartView spec={spec} theme={theme} />
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>

            <div className="px-6 pb-5 pt-3.5">
              <Composer value={composerText} onChange={setComposerText} onSend={sendMessage} onStop={stopGeneration} busy={thinking} />
              <p className="mt-[9px] text-center text-[11px] text-fog-800">
                Tunnel Safety Agent can make mistakes. Verify safety-critical outputs against source documents.
              </p>
            </div>
          </>
        ) : (
          <WelcomeScreen
            composerText={composerText}
            setComposerText={setComposerText}
            onSend={sendMessage}
            onStop={stopGeneration}
            busy={thinking}
          />
        )}
      </main>

      {docsPanelOpen && <KnowledgePanel documents={documents} onClose={() => setDocsPanelOpen(false)} />}
      {causalPanelOpen && <CausalPanel caseIds={lastCitedCaseIds} theme={theme} onClose={() => setCausalPanelOpen(false)} />}
      {reportPanelOpen && <ReportPanel onClose={() => setReportPanelOpen(false)} />}

      {searchOpen && (
        <SearchModal
          query={searchQuery}
          setQuery={setSearchQuery}
          results={searchResults}
          onSelect={selectChat}
          onClose={() => setSearchOpen(false)}
        />
      )}
    </div>
  );
}
