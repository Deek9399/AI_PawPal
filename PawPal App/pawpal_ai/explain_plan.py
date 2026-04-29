from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from pawpal_system import Scheduler, resolve_day_for_availability

from pawpal_ai.client import LLMClient
from pawpal_ai.retrieval import KnowledgeIndex, RetrievedChunk

logger = logging.getLogger(__name__)


def build_schedule_facts(scheduler: Scheduler, day: str = "today") -> Dict[str, Any]:
    plan = scheduler.get_daily_plan(day)
    total_min = sum(t.duration for t in plan)
    avail = scheduler._get_available_time_minutes(day)  # noqa: SLF001 intentional
    valid = scheduler.validate_schedule(day)
    key = resolve_day_for_availability(day)
    pet_for = _pet_for_tasks(scheduler, plan)
    items = []
    for i, t in enumerate(plan, 1):
        items.append(
            {
                "order": i,
                "description": t.description,
                "duration_minutes": t.duration,
                "priority": t.priority,
                "completed": t.completed,
                "pet": pet_for.get(t, "unknown"),
            }
        )
    return {
        "day_label": day,
        "availability_key": key,
        "total_scheduled_minutes": total_min,
        "available_minutes": avail,
        "validate_schedule": valid,
        "tasks": items,
    }


def _pet_for_tasks(scheduler: Scheduler, plan: list) -> Dict[Any, str]:
    out: Dict[Any, str] = {}
    for pet in scheduler.owner.pets:
        for t in plan:
            if t in pet.tasks:
                out[t] = pet.name
    return out


def format_context_chunks(chunks: List[RetrievedChunk]) -> str:
    if not chunks:
        return "(no retrieved reference text)"
    parts = []
    for c in chunks:
        parts.append(f"[{c.source_id}]\n{c.text}")
    return "\n\n".join(parts)


def explain_plan_rag(
    client: LLMClient,
    scheduler: Scheduler,
    day: str,
    index: Optional[KnowledgeIndex],
    query: str = "pet care routine scheduling tips",
) -> str:
    """Generate explanation; retrieval chunks are passed into the same LLM call (RAG)."""
    facts = build_schedule_facts(scheduler, day)
    chunks: List[RetrievedChunk] = []
    if index is not None:
        chunks = index.search(query, top_k=4)
    ctx = format_context_chunks(chunks)
    system = """You are PawPal+'s planning assistant. Explain the schedule using ONLY the JSON facts
and the reference excerpts. If the schedule is invalid (total time > available), say so clearly.
Do not invent tasks. Do not give veterinary medical advice. Keep the answer concise and structured."""
    user = f"""Reference excerpts (RAG context; use for general scheduling/care context only):
{ctx}

Schedule facts (authoritative; do not contradict):
{json.dumps(facts, indent=2)}

Write a short explanation: ordering rationale (priority), time budget, and any conflict warning.
Cite which reference section informed general tips (by source id) when relevant.
"""
    return client.chat(system, user, temperature=0.4)
