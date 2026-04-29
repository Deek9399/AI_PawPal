# How PawPal+ makes decisions

## What is deterministic (not a guess)

- **Task ordering** for the day: pending tasks are sorted by **priority** (5 highest first).
- **Feasibility**: the app compares **sum of task durations** to the owner’s **available time window** for the calendar day that “today” maps to. The schedule data lives in `pawpal_system.Scheduler` and `Owner.available_hours`.
- **Guardrails**: pattern-based rules block obvious **diagnosis / dosing / emergency** prompts before they are sent to the language model.

## What comes from the AI (Groq)

- **Plain-language task extraction** turns a paragraph into JSON tasks, which are then **validated** and attached to pets.
- **Ask PawPal** sends **retrieved handbook chunks** and **schedule facts** (`build_schedule_facts`) in the agent prompt (RAG + grounded facts). The orchestrator may request **tool results** (schedule JSON, extra retrieval) in an agentic loop. **My Schedule** uses the same schedule facts for metrics (no separate “explain” tab in the UI).
- **Third party**: prompts and facts are sent to **Groq** per their terms. Free tier has **rate limits**; the app surfaces rate-limit errors in the UI.

## What this app is not

- **Not veterinary advice.** For medical questions, emergencies, or medication dosing, use a licensed veterinarian.

## Failure modes

- If the model returns non-JSON for extraction, the UI shows a parse error.
- If total task time exceeds available minutes, **My Schedule → Today’s snapshot** shows a conflict warning; the checklist and task list still reflect the built plan for transparency.
