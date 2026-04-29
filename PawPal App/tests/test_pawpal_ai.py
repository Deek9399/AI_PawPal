"""Tests for PawPal+ AI helpers (no live API)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pawpal_system import Owner, Pet, Scheduler, Task, TaskFrequency

from pawpal_ai.client import LLMClient
from pawpal_ai.config import LLMSettings
from pawpal_ai.explain_plan import build_schedule_facts
from pawpal_ai.guardrails import check_user_input
from pawpal_ai.nl_extract import _parse_json_loose, apply_tasks_to_pets
from pawpal_ai.orchestrator import run_agentic_assistant
from pawpal_ai.retrieval import KnowledgeIndex
from pawpal_ai.diagnostics_checks import run_all_checks


@pytest.fixture
def owner_with_pet():
    o = Owner("A")
    p = Pet("Mochi", "cat")
    o.add_pet(p)
    return o


def test_guardrail_blocks_diagnosis():
    r = check_user_input("diagnose my cat's skin rash")
    assert not r.allowed
    assert "cannot" in r.user_message.lower() or "veterinar" in r.user_message.lower()


def test_guardrail_allows_scheduling():
    r = check_user_input("How do I fit two walks in one hour?")
    assert r.allowed


def test_parse_json_loose_strips_markdown_fence():
    raw = 'Here you go:\n```json\n{"tasks": [{"pet_name": "Mochi", "description": "Walk", "duration_minutes": 10, "frequency": "daily", "priority": 4}]}\n```'
    data = _parse_json_loose(raw)
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["description"] == "Walk"


def test_apply_tasks_valid(owner_with_pet):
    data = {
        "tasks": [
            {
                "pet_name": "Mochi",
                "description": "Walk",
                "duration_minutes": 15,
                "frequency": "daily",
                "priority": 4,
            }
        ]
    }
    n, errs = apply_tasks_to_pets(owner_with_pet, data)
    assert n == 1
    assert len(owner_with_pet.pets[0].tasks) == 1


def test_build_schedule_facts(owner_with_pet):
    owner_with_pet.pets[0].add_task(Task("x", 10, TaskFrequency.DAILY, 5))
    sch = Scheduler(owner_with_pet)
    sch.schedule_daily_plan("today")
    facts = build_schedule_facts(sch, "today")
    assert facts["validate_schedule"] is True
    assert len(facts["tasks"]) == 1
    assert facts["tasks"][0]["description"] == "x"


def test_knowledge_index_search():
    root = Path(__file__).resolve().parent.parent / "knowledge"
    idx = KnowledgeIndex(root)
    idx.load()
    hits = idx.search("routine scheduling", top_k=2)
    assert isinstance(hits, list)


@patch.object(LLMClient, "chat")
def test_agentic_final_answer(mock_chat, owner_with_pet):
    owner_with_pet.pets[0].add_task(Task("feed", 5, TaskFrequency.DAILY, 5))
    sch = Scheduler(owner_with_pet)
    sch.schedule_daily_plan("today")
    mock_chat.return_value = json.dumps(
        {"final_answer": "Your schedule lists feed first by priority."}
    )
    cl = LLMClient(LLMSettings(api_key="x", base_url="https://api.groq.com/openai/v1", model="m"))
    from pawpal_ai.trace import TraceLog

    text, tr = run_agentic_assistant(
        cl, sch, None, "What is on my plan?", trace=TraceLog()
    )
    assert "feed" in text.lower() or "schedule" in text.lower()
    mock_chat.assert_called()


@patch.object(LLMClient, "chat")
def test_agentic_tool_round(mock_chat, owner_with_pet):
    owner_with_pet.pets[0].add_task(Task("walk", 20, TaskFrequency.DAILY, 4))
    sch = Scheduler(owner_with_pet)
    sch.schedule_daily_plan("today")
    mock_chat.side_effect = [
        json.dumps(
            {
                "tool_calls": [
                    {"name": "get_schedule_facts", "arguments": {"day": "today"}}
                ]
            }
        ),
        json.dumps(
            {
                "final_answer": "You have a walk task scheduled; details from facts."
            }
        ),
    ]
    cl = LLMClient(LLMSettings(api_key="x", base_url="https://api.groq.com/openai/v1", model="m"))
    from pawpal_ai.trace import TraceLog

    text, tr = run_agentic_assistant(
        cl, sch, None, "List my schedule", trace=TraceLog()
    )
    assert mock_chat.call_count == 2
    assert "walk" in text.lower() or "schedule" in text.lower()


def test_diagnostics_all_pass():
    results = run_all_checks()
    assert all(r.passed for r in results), [r for r in results if not r.passed]
