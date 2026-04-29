# PawPal+ architecture

This document matches the implementation in `app.py`, `pawpal_system.py`, and `pawpal_ai/`. Diagrams render on GitHub and in many Markdown viewers that support Mermaid.

## Major components

```mermaid
flowchart TB
    subgraph ui["UI layer"]
        ST["Streamlit app.py"]
    end
    subgraph core["Deterministic core"]
        OWN["Owner"]
        PET["Pet"]
        TS["Task"]
        SCH["Scheduler"]
    end
    subgraph ai["AI layer pawpal_ai"]
        CLI["LLMClient Groq"]
        IDX["KnowledgeIndex TF-IDF"]
        GR["guardrails check_user_input"]
        NL["nl_extract JSON tasks"]
        ORC["orchestrator + schedule facts"]
    end
    subgraph data["Local data"]
        MD["knowledge/*.md"]
    end
    ST --> OWN
    ST --> SCH
    ST --> CLI
    ST --> GR
    OWN --> PET
    PET --> TS
    SCH --> OWN
    CLI --> ORC
    CLI --> NL
    IDX --> MD
    ORC --> IDX
    ORC --> SCH
    ORC --> CLI
    NL --> CLI
```

## End-to-end data flow

### Ask PawPal (agent + RAG)

```mermaid
flowchart LR
    U["User question"]
    GR["Guardrails"]
    SCH["Scheduler facts"]
    IDX["Retrieve chunks"]
    LLM["Groq chat loop"]
    A["Answer markdown"]
    U --> GR
    GR -->|allowed| SCH
    GR -->|allowed| IDX
    SCH --> LLM
    IDX --> LLM
    LLM --> A
    GR -->|blocked| A
```

Blocked prompts short-circuit with a fixed safety message (no LLM call).

### Describe tasks with AI (NL extraction)

```mermaid
flowchart LR
    T["Paragraph text"]
    GR["Guardrails"]
    LLM["Groq JSON tasks"]
    MAP["apply_tasks_to_pets"]
    OWN["Owner / pets"]
    T --> GR
    GR -->|allowed| LLM
    LLM --> MAP
    MAP --> OWN
```

### Core scheduling (no LLM)

```mermaid
flowchart LR
    O["Owner + pets + tasks"]
    S["Scheduler.schedule_daily_plan"]
    P["Ordered pending tasks"]
    V["validate_schedule vs available minutes"]
    O --> S
    S --> P
    P --> V
```

## OO model (domain classes)

See [`class_diagram.mmd`](class_diagram.mmd) for `Owner`, `Pet`, `Task`, `Scheduler` relationships. Tasks live on each `Pet`; `Scheduler` reads pending tasks across pets and stores daily plan lists keyed by day label.

## Class diagram vs runtime AI

`class_diagram.mmd` focuses on **persistent domain objects**. Runtime AI pieces (`LLMClient`, `KnowledgeIndex`, orchestrator) are **stateless services** invoked from `app.py` and do not appear as fields on `Owner`/`Scheduler`.
