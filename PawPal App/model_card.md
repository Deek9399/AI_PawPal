# PawPal+ — Model & reflection card

**AI collaboration**, **biases and limitations**, **misuse**, and **testing** (with narrative detail in [`reflection.md`](reflection.md)).

---

## Base project

This work extends the **Codepath AI Engineering Module 2 PawPal starter** (multi-pet household, `Owner` / `Pet` / `Task` / `Scheduler`, Streamlit UI). PawPal+ adds optional **Groq** LLM calls, **TF‑IDF RAG** over local `knowledge/*.md`, **guardrails**, **natural-language task extraction**, and an **agentic Ask PawPal** loop grounded on schedule facts + retrieval.

---

## Models and APIs

| Item | Value |
|------|--------|
| **Primary API** | Groq OpenAI-compatible chat completions (`OPENAI_BASE_URL`, `OPENAI_MODEL` / `GROQ_*` aliases) |
| **Typical model** | e.g. `llama-3.1-8b-instant` (configurable via `.env`) |
| **Deterministic core** | No ML: Python scheduling, validation, sorting |

Secrets stay in **`.env`** (not committed); see `.env.example`.

---

## AI collaboration

**How AI tools were used:** brainstorming class boundaries aligned with the starter, drafting **pytest** scaffolding for scheduler validation and guardrails, Streamlit `session_state` patterns, and docstring/README polish.

**What worked:** Targeted prompts (“edge cases for schedule validation,” “mock `LLMClient.chat` for agent tests”) produced usable templates after tightening assertions to match real types.

**What was rejected:** Suggestions to store tasks as **time-of-day → task** dictionaries conflicted with the starter’s **`Scheduler.daily_plans`** (ordered lists) and pet-owned task lists—those ideas were dropped in favor of the existing architecture.

**Verification:** Every AI-suggested structure was checked against invariants (tasks on pets, ordered plans, guardrails before LLM). **Pytest** and manual runs with a real API key validated behavior.

---

## Biases, limitations, and fairness

- **RAG scope:** Answers reflect only `knowledge/*.md`; outdated or narrow text becomes retrieval “truth.”
- **Retrieval:** TF‑IDF favors lexical overlap; unusual phrasing may retrieve weak context.
- **Language & culture:** UI and handbook are **English-first**; care norms may not generalize.
- **Medical boundary:** Guardrails are **heuristic** (regex/rules), not clinical moderation—edge phrasing may slip through or over-block.
- **Scheduling:** Priority-based ordering only—not a clinical or energy optimizer.

---

## Misuse and mitigations

**Risks:** Treating the app as veterinary advice; probing diagnosis/dosing; API key exposure on a shared machine.

**Mitigations:** Disclaimers, **guardrails** before LLM paths, schedule-grounded answers when possible, **tests** on block/allow behavior, **logging** on failures, keys via **`.env`** only.

---

## Testing — approach and results

| Layer | What we ran |
|-------|-------------|
| **Core** | `tests/test_pawpal.py` — tasks, recurrence, `schedule_daily_plan`, `validate_schedule`, etc. |
| **AI helpers** | `tests/test_pawpal_ai.py` — guardrails, JSON extraction / `_parse_json_loose`, retrieval smoke, **mocked** orchestrator (no network in CI) |

**Result (automated):** `python -m pytest` — **19 of 19** tests passing (see README testing section for snapshot).

**Human review:** Manual walkthrough of Household, My Schedule, and Ask PawPal with demo data and a valid key; guardrail refusals spot-checked.

**Reliability note:** Mocked tests stay stable; **live** LLM outputs still vary run-to-run—CI green does not guarantee identical demo wording.

---

## Summary takeaway

**AI accelerates implementation and tests; it does not replace architectural choices.** PawPal+ keeps deterministic scheduling explicit, isolates AI in `pawpal_ai/`, and tests boundaries the codebase owns (validation, guardrails, parsing) while mocking the network.
