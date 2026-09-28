# -*- coding: utf-8 -*-
"""
orchestrator.py — the agentic loop.

Streams events so the UI can show tool activity live:
  ("status", text)              — progress updates
  ("tool_call", name, args)     — a tool is being invoked
  ("tool_result", name, count)  — a tool returned
  ("delta", text)               — a chunk of the final answer
  ("done", full_answer)         — the loop finished
"""
import json

from . import bilingual, config
from .tools import display_chart, explain_term, get_statistics, query_graph, search_cases

TOOLS = {
    "search_cases": search_cases,
    "query_graph": query_graph,
    "get_statistics": get_statistics,
    "explain_term": explain_term,
    "display_chart": display_chart,
}
TOOL_SCHEMAS = [t.SCHEMA for t in TOOLS.values()]

SYSTEM_PROMPT = """You are the Tunnel Safety Agent (터널사고 예방 도우미),
an expert on 310 real tunnel construction accident cases from Korea.

TOOL ROUTING RULES:
- Counts, rates, rankings, "how many", "top N", "most common" -> get_statistics (SQL).
  NEVER estimate numbers from search results.
- Complete category lists, cause-chain patterns, multi-hop relations -> query_graph.
- Similar cases, what happened, prevention measures, narratives -> search_cases
  (Korean query; a translated Korean query is provided for English questions).
- Term definitions or translations -> explain_term.
- Chart/graph/visualization requests (차트, 그래프, 히스토그램) -> get the data
  with other tools first, then display_chart. Never say you cannot draw charts.
- Complex questions often need SEVERAL tools: e.g. statistics first, then
  search_cases to retrieve prevention measures for the top categories.

ANSWER RULES:
- Respond in the SAME LANGUAGE as the user's question (Korean or English).
- Cite supporting cases inline by case_id, e.g. (TA-0042). Only cite case_ids
  that actually appeared in tool results.
- Ground prevention advice in the retrieved 재발방지대책 of real cases; you may
  organize and synthesize, but do not invent measures with no basis.
- Korean category values (물체에 맞음, 해체작업...) should be kept in Korean with
  an English gloss when answering in English, e.g. "struck-by (물체에 맞음)".
- Be concise and practical. Safety managers are your audience.
- NEVER tell the user data/cases/a cause chain "doesn't exist" or "isn't
  available" based on a single empty or zero-row tool result — that almost
  always means the query was too narrow or slightly wrong, not that the
  underlying data is missing. Retry with a broader, simpler, or differently
  structured query (or a different tool) at least once before concluding
  anything is unavailable. Only state something is unavailable after a
  retry also comes back empty."""


def _execute(name: str, args: dict):
    try:
        return TOOLS[name].run(**args)
    except Exception as e:
        return [{"error": f"{name} failed: {e}"}]


def generate_follow_ups(question: str, answer: str, lang: str) -> list[str]:
    """Suggest up to 3 short follow-up questions a safety manager might ask
    next, in the same language as the conversation. Cheap best-effort call
    (gpt-4o-mini) — returns [] on any failure rather than breaking the turn."""
    if not answer or answer.startswith("⚠️"):
        return []
    client = config.openai_client()
    lang_name = "Korean" if lang == "ko" else "English"
    try:
        resp = client.chat.completions.create(
            model=config.TRANSLATE_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You suggest short, natural follow-up questions for a tunnel "
                        "construction accident-prevention assistant. Given the question "
                        "just asked and the answer given, propose exactly 3 follow-up "
                        f"questions in {lang_name} that a safety manager would plausibly "
                        "ask next — e.g. drilling into a specific cause, asking for "
                        "similar cases, or asking what preventive action to take. "
                        "Each one must be a single, complete, self-contained question "
                        "ending in '?', under 100 characters. Never copy or paraphrase "
                        "sentence fragments from the answer text itself — write new "
                        "questions, not summaries. Respond with strict JSON of the form "
                        '{"questions": ["...", "...", "..."]}, nothing else.'
                    ),
                },
                {"role": "user", "content": f"Question: {question}\n\nAnswer: {answer[:1500]}"},
            ],
            temperature=0.5,
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        questions = data.get("questions", [])
        cleaned = [
            q.strip()
            for q in questions
            if isinstance(q, str) and q.strip().endswith(("?", "？")) and len(q.strip()) <= 150
        ]
        return cleaned[:3]
    except Exception:
        return []


def run_agent(question: str, history: list[dict] | None = None, *, observer=None,
              tool_executor=None):
    """Generator yielding UI events. `history` = prior chat turns
    [{'role': 'user'|'assistant', 'content': str}, ...]."""
    observe = observer or (lambda kind, payload: None)
    execute = tool_executor or _execute
    client = config.openai_client()
    lang = bilingual.detect_language(question)

    user_content = question
    if lang == "en":
        yield ("status", "Translating query for Korean retrieval…")
        try:
            ko_query = bilingual.to_korean_query(question)
            user_content = (
                f"{question}\n\n"
                f"[Korean retrieval query for search_cases: {ko_query}]"
            )
            yield ("status", f"Korean query: {ko_query}")
        except Exception as e:
            observe("translation_error", {"error_type": type(e).__name__})
            yield ("status", f"Translation skipped ({e})")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history or []:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_content})

    answer_parts: list[str] = []
    for _round in range(config.MAX_TOOL_ROUNDS):
        stream = client.chat.completions.create(
            model=config.AGENT_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0.2,
            stream=True,
            **({"stream_options": {"include_usage": True}} if observer else {}),
        )

        tool_calls: dict[int, dict] = {}
        content_started = False
        finish_reason = None
        for chunk in stream:
            if observer and getattr(chunk, "usage", None):
                observe("usage", {"model": chunk.model, **chunk.usage.model_dump()})
            delta = chunk.choices[0].delta if chunk.choices else None
            if chunk.choices:
                finish_reason = getattr(chunk.choices[0], "finish_reason", None) or finish_reason
            if delta is None:
                continue
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    slot = tool_calls.setdefault(
                        tc.index, {"id": "", "name": "", "arguments": ""}
                    )
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["arguments"] += tc.function.arguments
            elif delta.content:
                content_started = True
                answer_parts.append(delta.content)
                yield ("delta", delta.content)

        if not tool_calls:
            observe("completion", {"reason": "final_answer" if finish_reason == "stop" else (finish_reason or "stream_incomplete"), "rounds": _round + 1})
            break  # model produced the final answer

        # register the assistant tool-call message, then execute each tool
        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": c["arguments"]},
                    }
                    for c in tool_calls.values()
                ],
            }
        )
        for c in tool_calls.values():
            try:
                args = json.loads(c["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}
            yield ("tool_call", c["name"], args)
            result = execute(c["name"], args)
            if c["name"] == "display_chart" and "error" not in result[0]:
                yield ("chart", args)
            yield ("tool_result", c["name"], len(result))
            tool_content = json.dumps(result, ensure_ascii=False)[:8000]
            observe("evidence", {"tool": c["name"], "args": args,
                                 "result": result, "model_content": tool_content,
                                 "round": _round + 1})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": c["id"],
                    "content": tool_content,
                }
            )
        if content_started:
            # model mixed prose with tool calls; keep prose, continue the loop
            answer_parts.append("\n")

    else:
        observe("completion", {"reason": "round_limit", "rounds": config.MAX_TOOL_ROUNDS})

    yield ("done", "".join(answer_parts))
