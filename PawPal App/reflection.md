# PawPal+ Project Reflection

## 1. System Design

**a. Initial design (matches `pawpal_system.py`)**

The core app uses four main types:

1. **Owner** — Stores the owner’s name, **available hours** per weekday (`available_hours`), optional preferences, and a list **`pets: List[Pet]`**. Methods such as `get_availability()` / `get_constraints()` expose scheduling inputs; `get_all_tasks()` aggregates tasks from every pet.

2. **Pet** — Stores identity fields (name, species/type, breed, age) and **`tasks: List[Task]`**. Tasks are added with `add_task()` so each pet owns its care activities explicitly.

3. **Task** — Describes one activity: description, duration (minutes), **frequency** (`TaskFrequency`: daily, weekly with weekday, monthly with day, etc.), priority (1–5), completion flag. Tasks do **not** embed a `Pet` reference; ownership is “task lives on this pet’s list.”

4. **Scheduler** — Holds an **`Owner`**, maintains **`daily_plans`** (day label → ordered list of `Task` references), **`schedule_daily_plan`** (sort pending tasks by priority), **`validate_schedule`** (total duration vs. owner availability for that day), and helpers to mark tasks complete.

**Key relationships:** An **Owner** has many **Pets**; each **Pet** has many **Tasks**. **Scheduler** reads pending tasks across pets and writes ordered daily plans—there is no separate “DailyPlan” class in the codebase.

**b. Design evolution**

The starter emphasized **multi-pet households** and **explicit task lists per pet**, which avoids ambiguity when the same description could apply to multiple animals (the UI and NL layer resolve **which pet** when adding tasks). The **Scheduler** centralizes “today’s ordering” and validation without duplicating task storage.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

My scheduler considers the following constraints:
- **Time availability**: Owner's available hours per day (e.g., 9 AM–6 PM on weekdays)
- **Task priority**: 1–5 scale where 5 is critical (feeding, medication) and 1 is optional
- **Task duration**: Prevents scheduling tasks that exceed available time
- **Task frequency**: Distinguishes daily vs. weekly tasks to avoid scheduling mistakes

I prioritized **time and priority** as most critical because a pet owner won't skip feeding a dog, and if tasks exceed available time, the schedule must warn them. Task frequency came next because daily recurrence is essential to the app's core value. Owner preferences are currently a placeholder but could influence future iterations.

**b. Tradeoffs**

**Tradeoff**: My scheduler sorts tasks by priority alone and doesn't optimize time allocation (e.g., spacing high-energy walks away from meal times).

**Why it's reasonable**: For a first iteration, this keeps the logic simple and transparent. A pet owner can *see* why tasks are ordered (priority 5 first) and manually adjust if needed. A more complex optimization would require heuristics and machine learning, which would be harder to debug and verify. This approach aligns with the principle of "make it work first, optimize later."

---

## 3. AI Collaboration

**a. How you used AI**

I used Copilot in several key moments:

1. **Design brainstorming**: Asked Copilot "What are the 4 main classes for a pet scheduler?" and got Owner, Pet, Task, plus an orchestrator-style class—which I aligned with **`Scheduler`** in the starter.

2. **Code generation**: Used "Generate class stubs for Task, Pet, Owner" to scaffold the basic structure quickly, then hand-edited to add my own validation logic.

3. **Test writing**: Asked "Draft tests for task priority sorting and schedule validation," which gave me a template I modified to fit my system.

4. **UI integration**: Asked "How to use st.session_state to persist objects in Streamlit," which explained the pattern clearly with examples.

5. **Documentation**: Used "Add docstrings to methods" and "Generate a Features list" to polish the README.

**Most helpful prompts**:
- "What's the most important edge case to test for a scheduler?" (led to conflict detection tests)
- "Why is my schedule validation failing?" (helped me debug time calculations)
- "How do I sort tasks by priority in Python?" (simple example made it clear)

**Less helpful**:
- Very open-ended prompts like "Build a pet scheduler" (too vague, led to rambling suggestions)
- Asking for full implementations without context (Copilot generated overly complex code I had to simplify)

**b. Judgment and verification**

**One moment I rejected AI advice**: 

Copilot suggested storing scheduled tasks as a dict mapping time→task (e.g., `{9:00: [task1, task2]}`). This seemed efficient, but I realized:
1. Time representation gets messy (time objects vs. strings)
2. The codebase already uses a **sorted list of `Task` references** per day (`Scheduler.daily_plans`), which matches “priority order” without slotting every task to a clock time
3. The dict didn’t add value for a first version

I stuck with the simpler approach aligned with the starter’s `Scheduler` model.

**How I evaluated**:
- I ran the suggested code mentally: "Would this cause confusion later?"
- I checked existing code: "Does this pattern match what I've already built?"
- I defaulted to simplicity: "Can I understand this six months from now?"

This taught me that **AI is a suggestion engine, not truth**. I had to play "lead architect" and say "no thanks" when something didn't fit my vision.

---

## 4. Testing and Verification

**a. What you tested**

**Core scheduler & model (`tests/test_pawpal.py`):** task completion, pet task lists, priority ordering, recurrence handling, `validate_schedule()` when total minutes exceed availability (and success when within budget), plan generation, etc.

**AI layer (`tests/test_pawpal_ai.py`):**  
- **Guardrails**: e.g. block `"diagnose my cat's skin rash"`, allow `"How do I fit two walks in one hour?"`  
- **NL extraction**: JSON parsing with markdown fences; `apply_tasks_to_pets` attaches tasks to the right pet  
- **Schedule facts** for prompts (`build_schedule_facts`)  
- **KnowledgeIndex.search** loads `knowledge/` without network  
- **Orchestrator**: `run_agentic_assistant` with **mocked** `LLMClient.chat` so CI needs no API key  

Running `python -m pytest` executes the full suite (core + AI helpers).

**Why these matter:** Scheduler tests protect deterministic behavior; AI tests lock in guardrail behavior, parsing, and orchestration wiring so refactors don’t silently break safety or JSON paths.

**b. Confidence**

**How reliability is measured:** (1) **`python -m pytest`** — 19 tests, core + AI helpers with mocked LLM; (2) **logging** in the app and `pawpal_ai` on API/parse failures; (3) **manual review** of Ask PawPal and guardrails with real keys. We do not expose model confidence scores; guardrails + tests + logs are the quality signals.

**Confidence level**: High for deterministic and mocked paths; live LLM quality depends on prompt and schedule context—see the **Reliability snapshot** in `README.md`.

**What I'd test next** (if more time):
- Negative durations and invalid priorities (input validation hardening)
- Very large numbers of pets/tasks (performance testing)
- Concurrent schedule generation (if adding multi-user support)
- Realistic scenarios: a busy Monday with 10+ tasks, back-to-back appointments
- Reset and recurrence over multiple days (multi-day scheduling)

---

## 5. Reflection

**a. What went well**

I'm most satisfied with **the Scheduler class**. It cleanly orchestrates across multiple pets, provides clear sorting/filtering methods, and the `validate_schedule()` method actually *prevents bad schedules*. When I saw it flag an overscheduled day and show a warning to the user, I realized the system was doing its job.

Second, the **test coverage**. Having **pytest** cover both the scheduler and the AI helpers (guardrails, retrieval, mocked agent) gave me confidence to change the Streamlit UI without breaking logic or safety paths.

**b. What you would improve**

1. **Scheduler algorithm**: Currently just sorts by priority. A real version would:
   - Space tasks throughout the day (don't cluster all high-priority tasks at 8 AM)
   - Respect preferred time windows ("dog walk should be morning/evening")
   - Handle multi-day scheduling for weekly tasks

2. **Data persistence**: Everything disappears on app refresh. Should save Owner/Pet/Task data to a database or JSON file.

3. **UI polish**: The Streamlit tables work, but a custom dashboard with timeline visualization would be much clearer.

4. **Error handling**: Currently minimal. Should handle edge cases like negative durations, conflicting pet care needs, etc.

**c. Key takeaway**

**The most important lesson**: **AI is a coding partner, not a replacement for architectural thinking.**

Copilot excels at completing code patterns, generating docstrings, and explaining library APIs. But it doesn't understand *your* constraints, your user's needs, or why you chose one design over another. 

As a beginner, I had to:
1. **Define the problem myself** (don't let AI suggest random features)
2. **Make intentional tradeoffs** (simple sorting > complex optimization, for now)
3. **Verify every suggestion** (run it mentally, check it fits, test it)
4. **Keep the architecture clean** (say no to complexity that doesn't matter yet)

Once I stopped asking "What should I build?" and started asking "Is this Copilot suggestion aligned with my design?", the whole process became smoother. 

**The lead architect role matters.** Even a beginner can be one—you just have to ask better questions and trust your judgment when something feels off.

---

## 6. Limitations, misuse, reliability surprises, and AI collaboration

**Limitations and biases**

- **Coverage:** RAG only sees what is in `knowledge/*.md`; gaps or outdated text become “truth” for the model. TF‑IDF favors lexical overlap, so unusual wording may retrieve weak context.
- **Language & norms:** The UI and prompts are English-first; care assumptions in the handbook may not fit every culture or species-specific nuance.
- **Medical boundary:** Guardrails are **heuristic** (pattern-based), not clinical moderation—creative phrasing could slip through, or benign questions could be blocked.
- **Scheduling:** The core engine prioritizes by priority score only—it does not optimize energy, travel, or medication interactions; validation is time-budget aware but not a clinical planner.
- **Session model:** Data lives in Streamlit session state—no multi-user enforcement or persistent audit log.

**Misuse and prevention**

- **Yes, it could be misused**—e.g. treating Ask PawPal as a vet substitute, probing for diagnosis/dosing language, or using NL extraction to flood tasks as harassment if shared-hostile contexts existed; API keys on a compromised machine could be abused for unrelated calls.
- **Mitigations in place:** Clear **“not veterinary advice”** copy, **guardrails** before LLM calls, **schedule-grounded** answering where possible, **logging** of failures, **tests** on guardrail allow/block behavior, and **no keys in the repo** (`.env` / local config). **Future hardening:** API rate limits, stricter moderation tier for medical-adjacent content, and saving audit trails if the app ever becomes multi-tenant.

**What surprised me when testing reliability**

- **Mocks vs reality:** The suite **passed with mocked LLM** responses, but live Groq answers still varied run-to-run on the same prompt—reliability in CI did not fully predict demo-night variability.
- **JSON creativity:** Models sometimes returned valid intent wrapped in extra prose or fences; I expected occasional failures, but the variety of “almost JSON” shapes was what kept `_parse_json_loose` and tests valuable.

**Collaboration with AI — one helpful idea, one bad idea**

- **Helpful:** Asking for **pytest cases for schedule validation and conflict detection** produced a solid skeleton fast; I tightened assertions to match `Scheduler`’s actual objects and caught real bugs.
- **Flawed:** Copilot suggested modeling the day as a **time-of-day → list of tasks** dict. That fought the starter’s **ordered `daily_plans` list** and would have complicated recurrence and validation; keeping tasks on each `Pet` and letting `Scheduler` sort was the right fit.

---
