from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pawpal_system import Scheduler

from pawpal_ai.client import LLMClient
from pawpal_ai.explain_plan import build_schedule_facts, format_context_chunks
from pawpal_ai.retrieval import KnowledgeIndex, RetrievedChunk
from pawpal_ai.trace import TraceLog

logger = logging.getLogger(__name__)

AGENT_SYSTEM = """You are PawPal+'s assistant for pet care scheduling.

Return ONLY a JSON object (no markdown fences), either:
1) {"tool_calls": [{"name": "get_schedule_facts", "arguments": {"day": "today"}}, {"name": "search_knowledge", "arguments": {"query": "..."}}]}
2) {"final_answer": "..."}

Tools:
- get_schedule_facts — arguments: day (e.g. "today")
- search_knowledge — arguments: query (string)

Use tools if you need the live schedule or more handbook text. Otherwise answer with final_answer.
Never diagnose or give medication dosing. Redirect medical emergencies to a veterinarian.

Your messages may include REFERENCE_EXCERPTS (RAG); ground tips in them when relevant."""

MAX_AGENT_STEPS = 4


def _parse_agent_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        text = m.group(0)
    return json.loads(text)


def _run_tools(
    tool_calls: List[Dict[str, Any]],
    scheduler: Scheduler,
    index: Optional[KnowledgeIndex],
    trace: TraceLog,
) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    for call in tool_calls:
        name = call.get("name")
        args = call.get("arguments") or {}
        trace.add("tool", f"tool:{name}", args=args)
        if name == "get_schedule_facts":
            day = str(args.get("day", "today"))
            facts = build_schedule_facts(scheduler, day)
            results.append({"tool": name, "output": json.dumps(facts)})
        elif name == "search_knowledge":
            q = str(args.get("query", ""))
            if index:
                ch = index.search(q, top_k=4)
                trace.add("retrieval", "search_knowledge", query=q, chunk_ids=[c.source_id for c in ch])
                results.append({"tool": name, "output": format_context_chunks(ch)})
            else:
                results.append({"tool": name, "output": "(knowledge index unavailable)"})
        else:
            results.append({"tool": str(name), "output": "unknown tool"})
    return results


def run_agentic_assistant(
    client: LLMClient,
    scheduler: Scheduler,
    index: Optional[KnowledgeIndex],
    user_message: str,
    day: str = "today",
    trace: Optional[TraceLog] = None,
) -> Tuple[str, TraceLog]:
    """
    RAG seeds the first turn; model may request tools; execution feeds back until final_answer.
    """
    tr = trace or TraceLog()
    seed_chunks: List[RetrievedChunk] = index.search(user_message, top_k=4) if index else []
    tr.add("retrieval", "seed_rag", chunk_ids=[c.source_id for c in seed_chunks])
    seed_ctx = format_context_chunks(seed_chunks)

    conversation = f"""REFERENCE_EXCERPTS (RAG — use in your answer):
{seed_ctx}

USER_QUESTION:
{user_message}

Default day for get_schedule_facts if needed: {day}
"""

    last_raw = ""
    for _ in range(MAX_AGENT_STEPS):
        raw = client.chat(AGENT_SYSTEM, conversation, temperature=0.35)
        last_raw = raw
        try:
            data = _parse_agent_json(raw)
        except json.JSONDecodeError:
            tr.add("agent", "parse_error", raw_preview=raw[:500])
            return raw, tr

        if "final_answer" in data and data["final_answer"]:
            tr.add("agent", "final_answer")
            return str(data["final_answer"]), tr

        calls = data.get("tool_calls") or []
        if not calls:
            tr.add("agent", "no_final_no_tools")
            return raw, tr

        outs = _run_tools(calls, scheduler, index, tr)
        conversation = conversation + "\nTOOL_RESULTS:\n" + json.dumps(outs) + "\nNow respond with {\"final_answer\": \"...\"} using tool outputs and references."

    tr.add("agent", "max_steps")
    return last_raw, tr


def assistant_answer_simple(
    client: LLMClient,
    scheduler: Scheduler,
    index: Optional[KnowledgeIndex],
    user_message: str,
    trace: TraceLog,
) -> str:
    """Single-shot RAG Q&A fallback."""
    chunks = index.search(user_message, top_k=4) if index else []
    trace.add("retrieval", "simple_rag", chunk_ids=[c.source_id for c in chunks])
    facts = build_schedule_facts(scheduler, "today")
    ctx = format_context_chunks(chunks)
    system = """Answer using REFERENCE_EXCERPTS and SCHEDULE_FACTS. Do not invent tasks.
No veterinary diagnosis or dosing."""
    user = f"{ctx}\n\nSCHEDULE_FACTS:\n{json.dumps(facts, indent=2)}\n\nQuestion:\n{user_message}"
    return client.chat(system, user, temperature=0.4)
