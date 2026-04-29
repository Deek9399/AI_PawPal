from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Tuple

from pawpal_system import Owner, Pet, Task, TaskFrequency

from pawpal_ai.client import LLMClient

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """You are a structured extraction assistant for PawPal+, a pet care planner.
Given the owner's natural language, output ONLY valid JSON (no markdown fences) with this shape:
{
  "tasks": [
    {
      "pet_name": "string (must match an existing pet name if specified)",
      "description": "string",
      "duration_minutes": positive integer,
      "frequency": "daily" | "twice_daily" | "weekly" | "monthly" | "as_needed",
      "priority": integer 1-5 (5 highest)
    }
  ]
}
If nothing actionable is present, use {"tasks": []}.
Do not include commentary."""

FREQ_MAP = {
    "daily": TaskFrequency.DAILY,
    "twice_daily": TaskFrequency.TWICE_DAILY,
    "weekly": TaskFrequency.WEEKLY,
    "monthly": TaskFrequency.MONTHLY,
    "as_needed": TaskFrequency.AS_NEEDED,
}


def _parse_json_loose(text: str) -> Dict[str, Any]:
    """Parse model output; handles markdown fences and nested JSON better than a greedy regex."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I | re.M)
    text = re.sub(r"\s*```\s*$", "", text, flags=re.M)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start < 0:
        raise json.JSONDecodeError("No JSON object found", text, 0)

    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                chunk = text[start : i + 1]
                return json.loads(chunk)

    raise json.JSONDecodeError("Unbalanced braces in JSON", text, start)


def _coerce_duration(item: Dict[str, Any]) -> int:
    v = item.get("duration_minutes")
    if v is None:
        v = item.get("duration") or item.get("minutes")
    if v is None:
        return 0
    return int(round(float(v)))


def _normalize_frequency(fr: str) -> str:
    fr = (fr or "daily").strip().lower().replace(" ", "_").replace("-", "_")
    synonyms = {
        "every_day": "daily",
        "once_daily": "daily",
        "everyday": "daily",
        "bidaily": "twice_daily",
        "2x_daily": "twice_daily",
        "twice_a_day": "twice_daily",
    }
    return synonyms.get(fr, fr)


def extract_tasks_nl(client: LLMClient, owner: Owner, user_text: str) -> Tuple[Dict[str, Any], str]:
    """Returns (parsed dict, raw model text)."""
    pet_names = ", ".join(p.name for p in owner.pets) or "(no pets yet — use pet_name in tasks anyway for later)"
    user = f"""Owner name: {owner.name}
Known pets: {pet_names}

Owner request:
{user_text}
"""
    try:
        raw = client.chat(
            EXTRACT_SYSTEM,
            user,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.info("JSON mode not used (%s); retrying default completion.", e)
        raw = client.chat(EXTRACT_SYSTEM, user, temperature=0.2)
    try:
        data = _parse_json_loose(raw)
    except json.JSONDecodeError as e:
        logger.exception("extract JSON parse failed")
        raise ValueError(
            f"Could not parse structured response from model: {e}\n\nRaw (first 800 chars):\n{raw[:800]}"
        ) from e
    if data.get("tasks") is None:
        data["tasks"] = []
    if "tasks" not in data:
        data["tasks"] = []
    return data, raw


def apply_tasks_to_pets(owner: Owner, data: Dict[str, Any]) -> Tuple[int, List[str]]:
    """
    Create Task objects on matching pets. Returns (count added, error messages).
    """
    errors: List[str] = []
    added = 0
    name_to_pet: Dict[str, Pet] = {p.name.lower(): p for p in owner.pets}
    for item in data.get("tasks", []):
        if not isinstance(item, dict):
            errors.append(f"Skip non-object task: {item!r}")
            continue
        try:
            pname = str(item.get("pet_name", "") or item.get("pet", "")).strip()
            desc = str(
                item.get("description", "") or item.get("task", "") or item.get("name", "")
            ).strip()
            dur = _coerce_duration(item)
            pr = int(round(float(item.get("priority", 3))))
            fr = _normalize_frequency(str(item.get("frequency", "daily")))
        except (TypeError, ValueError) as e:
            errors.append(f"Invalid task fields: {e}")
            continue
        if not desc or dur < 1:
            errors.append(f"Skip invalid task (need description + duration): {item}")
            continue
        pr = max(1, min(5, pr))
        if fr not in FREQ_MAP:
            fr = "daily"
        pet = name_to_pet.get(pname.lower()) if pname else None
        if not pet and owner.pets:
            pet = owner.pets[0]
            errors.append(f"Pet '{pname}' not found; attached task to {pet.name}.")
        elif not pet:
            errors.append("Add a pet before applying tasks from text.")
            continue
        freq_e = FREQ_MAP[fr]
        kw: Dict[str, Any] = {}
        if freq_e == TaskFrequency.WEEKLY and item.get("weekly_weekday") is not None:
            kw["weekly_weekday"] = max(0, min(6, int(item["weekly_weekday"])))
        if freq_e == TaskFrequency.MONTHLY and item.get("monthly_day") is not None:
            kw["monthly_day"] = max(1, min(31, int(item["monthly_day"])))
        task = Task(desc, dur, freq_e, pr, **kw)
        pet.add_task(task)
        added += 1
    return added, errors
