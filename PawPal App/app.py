from __future__ import annotations

import html
import logging
from pathlib import Path

import pandas as pd
import streamlit as st
from datetime import time

from demo_data import apply_demo_seed
from pawpal_system import (
    Owner,
    Pet,
    Task,
    Scheduler,
    TaskFrequency,
    WEEKDAY_LABELS,
    task_recurrence_label,
    upcoming_task_occurrences,
)

from pawpal_ai.client import LLMClient
from pawpal_ai.config import LLMSettings, get_llm_settings
from pawpal_ai.explain_plan import build_schedule_facts
from pawpal_ai.guardrails import check_user_input
from pawpal_ai.nl_extract import apply_tasks_to_pets, extract_tasks_nl
from pawpal_ai.orchestrator import run_agentic_assistant
from pawpal_ai.retrieval import KnowledgeIndex
from pawpal_ai.trace import TraceLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pawpal.app")

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
# Paired schedule tables share one height so the row looks even.
_PAIR_TABLE_HEIGHT = 300
_FULL_CAL_HEIGHT = 340


def _inject_css() -> None:
    st.markdown(
        """
        <style>
            .pp-hero h1 {
                font-size: 1.85rem;
                font-weight: 700;
                letter-spacing: -0.03em;
                margin: 0 0 0.35rem 0;
                color: #4c1d95;
                display: inline-block;
                padding: 0.35rem 1rem 0.4rem 1rem;
                background: linear-gradient(135deg, #ede9fe 0%, #faf5ff 100%);
                border: 1px solid #c4b5fd;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(91, 33, 182, 0.12);
            }
            .pp-hero p { color: #64748b; font-size: 1rem; margin: 0; line-height: 1.5; }
            .pp-hero-stack {
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 100%;
                margin: 0 auto 0.75rem auto;
                box-sizing: border-box;
            }
            .pp-hero-stack .pp-hero { text-align: center; max-width: 40rem; }
            .pp-hero-side {
                background: linear-gradient(145deg, #faf5ff 0%, #f8fafc 100%);
                border: 1px solid #e9d5ff;
                border-radius: 12px;
                padding: 1rem 1.25rem 1.15rem 1.25rem;
                margin-top: 1rem;
                max-width: 28rem;
                width: 100%;
                text-align: center;
                box-sizing: border-box;
            }
            .pp-hero-stack .pp-hero-side ul {
                margin: 0.65rem 0 0 0;
                padding-left: 0;
                list-style-position: inside;
                color: #4c1d95;
                font-size: 0.9rem;
                line-height: 1.75;
            }
            .pp-hero-stack .pp-hero-side li { margin-bottom: 0.35rem; }
            .pp-empty { text-align: center; padding: 2rem 1rem; background: #ffffff; border: 1px solid #e9d5ff; border-radius: 12px; }
            .pp-hello {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                text-align: center;
                padding: 1rem 1.1rem 1.1rem 1.1rem;
                margin: 0 0 0.35rem 0;
                min-height: 7.25rem;
                background: linear-gradient(145deg, #faf5ff 0%, #ede9fe 100%);
                border: 1px solid #c4b5fd;
                border-radius: 10px;
                font-size: 1.2rem;
                font-weight: 600;
                color: #4c1d95;
                letter-spacing: -0.02em;
            }
            .pp-hello--in-card {
                border: none;
                border-radius: 10px;
                background: linear-gradient(145deg, #faf5ff 0%, #f3e8ff 100%);
                margin-bottom: 0.25rem;
            }
            .pp-hello-line {
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 0.45rem;
                flex-wrap: wrap;
            }
            .pp-hello-hint {
                font-size: 0.82rem;
                font-weight: 500;
                color: #6d28d9;
                line-height: 1.4;
                max-width: 16rem;
            }
            .pp-hero-safety-inline {
                font-size: 0.8rem;
                color: #64748b;
                margin: 0.35rem 0 0.75rem 0;
                text-align: center;
                max-width: 36rem;
                margin-left: auto;
                margin-right: auto;
            }
            /* Welcome card only: low-emphasis Change name */
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.pp-hello--in-card)
                button[kind="secondary"] {
                background: transparent !important;
                border: none !important;
                box-shadow: none !important;
                color: #6d28d9 !important;
                font-weight: 500 !important;
                text-decoration: underline;
                text-underline-offset: 3px;
                padding: 0.15rem 0.25rem !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.pp-hello--in-card)
                button[kind="secondary"]:hover {
                color: #5b21b6 !important;
                background: #f5f3ff !important;
            }
            .pp-section-head {
                margin-bottom: 0.85rem;
                padding: 0.65rem 0.85rem 0.75rem 0.85rem;
                background: linear-gradient(145deg, #faf5ff 0%, #ffffff 70%);
                border: 1px solid #e9d5ff;
                border-radius: 12px;
                border-left: 4px solid #7c3aed;
                box-shadow: 0 1px 4px rgba(91, 33, 182, 0.07);
            }
            .pp-kicker {
                display: inline-block;
                font-size: 0.68rem;
                font-weight: 700;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                color: #5b21b6;
                background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
                padding: 0.3rem 0.7rem;
                border-radius: 8px;
                border: 1px solid #a78bfa;
                box-shadow: 0 1px 2px rgba(91, 33, 182, 0.1);
            }
            .pp-sub { color: #64748b; font-size: 0.95rem; margin: 0.45rem 0 0 0; line-height: 1.45; max-width: 42rem; }
            .pp-card-title {
                font-size: 1rem;
                font-weight: 700;
                color: #4c1d95;
                margin: 0 0 0.85rem 0;
                padding: 0.5rem 0.65rem 0.5rem 0.75rem;
                background: linear-gradient(90deg, #f5f3ff 0%, #faf5ff 45%, rgba(250, 245, 255, 0.35) 100%);
                border-left: 4px solid #7c3aed;
                border-radius: 0 10px 10px 0;
                letter-spacing: -0.02em;
                box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
            }
            div[data-testid="stSidebarContent"] { padding-top: 1rem; }
            div[data-testid="stSidebarContent"] h1,
            div[data-testid="stSidebarContent"] h2,
            div[data-testid="stSidebarContent"] h3 {
                font-size: 1.15rem !important;
                font-weight: 700 !important;
                color: #4c1d95 !important;
                padding: 0.45rem 0.55rem 0.45rem 0.65rem !important;
                margin: 0 0 0.25rem 0 !important;
                background: linear-gradient(90deg, #ede9fe 0%, #faf5ff 90%) !important;
                border-left: 4px solid #7c3aed !important;
                border-radius: 0 8px 8px 0 !important;
                letter-spacing: -0.02em !important;
            }
            div[data-testid="stDataFrame"] {
                border: 1px solid #e9d5ff !important;
                border-radius: 10px !important;
                overflow: hidden !important;
                box-shadow: 0 1px 3px rgba(91, 33, 182, 0.08) !important;
            }
            div[data-testid="stDataFrame"] [data-testid="stTable"] {
                font-size: 0.88rem;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: #ffffff !important;
                border-radius: 12px !important;
                border: 1px solid #e9d5ff !important;
                padding: 1rem 1.15rem 1.15rem 1.15rem !important;
                box-shadow: 0 1px 3px rgba(91, 33, 182, 0.06) !important;
            }
            button[kind="primary"] { border-radius: 8px; }
            section.main a { color: #6d28d9; }
            section.main hr {
                border-color: #ede9fe !important;
                opacity: 1 !important;
            }
            div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
                background-color: #7c3aed !important;
            }
            /* st.success (default light green) → purple */
            div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {
                background-color: #ede9fe !important;
                background-image: none !important;
                border: 1px solid #c4b5fd !important;
                color: #5b21b6 !important;
            }
            div[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) a {
                color: #6d28d9 !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_header(kicker: str, subtitle: str = "") -> None:
    sub = f'<p class="pp-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="pp-section-head"><span class="pp-kicker">{kicker}</span>{sub}</div>',
        unsafe_allow_html=True,
    )


def _df(
    df: pd.DataFrame,
    *,
    height: int | None = None,
    column_config: dict | None = None,
) -> None:
    kw: dict = {"hide_index": True, "use_container_width": True}
    if height is not None:
        kw["height"] = height
    if column_config:
        kw["column_config"] = column_config
    st.dataframe(df, **kw)


def _pet_name_for_task(owner: Owner, task: Task) -> str:
    for p in owner.pets:
        if task in p.tasks:
            return p.name
    return "?"


def _init_state() -> None:
    if "owner" not in st.session_state:
        o = Owner("Jordan")
        for d in (
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ):
            o.available_hours[d] = (time(7, 0), time(21, 0))
        st.session_state.owner = o
    if "scheduler" not in st.session_state:
        st.session_state.scheduler = Scheduler(st.session_state.owner)
    if "knowledge_index" not in st.session_state:
        idx = KnowledgeIndex(KNOWLEDGE_DIR)
        idx.load()
        st.session_state.knowledge_index = idx
    if "assistant_q" not in st.session_state:
        st.session_state.assistant_q = ""
    if "assistant_a" not in st.session_state:
        st.session_state.assistant_a = ""
    if "last_plan_valid" not in st.session_state:
        st.session_state.last_plan_valid = None
    if "owner_name_saved_once" not in st.session_state:
        st.session_state.owner_name_saved_once = False
    if not st.session_state.get("demo_seed_applied"):
        apply_demo_seed(st.session_state.owner)
        st.session_state.scheduler = Scheduler(st.session_state.owner)
        st.session_state.demo_seed_applied = True


def _client_from_sidebar() -> LLMClient:
    s = get_llm_settings()
    base = st.session_state.get("ov_base") or s.base_url
    model = st.session_state.get("ov_model") or s.model
    key = st.session_state.get("ov_key")
    if key:
        return LLMClient(LLMSettings(api_key=key, base_url=base, model=model))
    return LLMClient()


def render_sidebar() -> None:
    st.sidebar.markdown("### PawPal+")
    st.sidebar.caption("Settings")

    st.sidebar.markdown("**AI connection**")
    st.sidebar.caption("Credentials load from `.env`. Override below for this session only.")
    st.sidebar.text_input("API key override", type="password", key="ov_key", placeholder="Paste key…")

    c = _client_from_sidebar()
    if c.available():
        st.sidebar.success("Connected")
    else:
        st.sidebar.warning("Add API key")

    with st.sidebar.expander("Advanced", expanded=False):
        s = get_llm_settings()
        st.text_input("Base URL", value=s.base_url, key="ov_base")
        st.text_input("Model", value=s.model, key="ov_model")

    with st.sidebar.expander("Demo", expanded=False):
        st.caption("Reload sample pets, tasks, and recurring events.")
        if st.button("Reload sample household", key="btn_demo_reload"):
            apply_demo_seed(st.session_state.owner)
            st.session_state.scheduler = Scheduler(st.session_state.owner)
            st.session_state.last_plan_valid = None
            st.session_state.demo_seed_applied = True
            st.rerun()


def render_hero() -> None:
    st.markdown(
        '<div class="pp-hero-stack">'
        '<div class="pp-hero"><h1>PawPal+</h1>'
        "<p>Plan today’s pet care in minutes—prioritized tasks, realistic time, optional AI help.</p></div>"
        '<div class="pp-hero-side"><strong style="color:#4c1d95;font-size:0.85rem;">What you can do</strong>'
        "<ul><li>Shape your household and recurring care</li>"
        "<li>Build a realistic daily plan from priorities</li>"
        "<li>Ask for scheduling tips grounded in your plan</li></ul></div>"
        "</div>",
        unsafe_allow_html=True,
    )
    with st.expander("Safety", expanded=False):
        st.caption(
            "PawPal+ does not replace a veterinarian. AI answers use Groq; prompts leave your device "
            "per their terms. For emergencies or medical decisions, contact a licensed vet."
        )
    st.markdown(
        '<p class="pp-hero-safety-inline">'
        "AI uses Groq and is not medical advice—expand <strong>Safety</strong> above for details."
        "</p>",
        unsafe_allow_html=True,
    )


def tab_household() -> None:
    section_header(
        "Household",
        "Who you’re caring for, recurring tasks, and AI-assisted task capture.",
    )

    # Same-height pair: profile (or greeting after save) + add pet
    c_prof, c_addpet = st.columns(2, gap="large")
    with c_prof:
        owner_nm = st.session_state.owner.name.strip()
        profile_saved = st.session_state.get("owner_name_saved_once") and bool(owner_nm)
        if not profile_saved:
            with st.container(border=True):
                st.markdown('<p class="pp-card-title">Your profile</p>', unsafe_allow_html=True)
                n = st.text_input("Your name", value=st.session_state.owner.name, key="owner_name_ui")
                if st.button("Save name", key="save_owner"):
                    st.session_state.owner.name = n
                    st.session_state.owner_name_saved_once = True
                    st.rerun()
        else:
            with st.container(border=True):
                st.markdown('<p class="pp-card-title">Welcome</p>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="pp-hello pp-hello--in-card">'
                    f'<span class="pp-hello-line">👋 Hello, {html.escape(owner_nm)}!</span>'
                    f'<span class="pp-hello-hint">Add pets using the form on the right.</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if st.button("Change name", key="owner_change_name", type="secondary"):
                    st.session_state.owner_name_saved_once = False
                    st.rerun()

    with c_addpet:
        with st.container(border=True):
            st.markdown('<p class="pp-card-title">Add a pet</p>', unsafe_allow_html=True)
            ap1, ap2, ap3 = st.columns([2, 2, 1])
            with ap1:
                pn = st.text_input("Pet name", value="Mochi", key="addpn")
            with ap2:
                sp = st.selectbox("Species", ["dog", "cat", "other"], key="addsp")
            with ap3:
                ag = st.number_input("Age (years)", 0, 30, 2, key="addag")
            add_pet = st.button("Add pet", type="primary", key="btn_add_pet")

    if add_pet:
        st.session_state.owner.add_pet(Pet(pn, sp, "", ag))
        st.rerun()

    if not st.session_state.owner.pets:
        st.markdown(
            '<div class="pp-empty"><strong>No pets yet</strong><br/>'
            "<span style='color:#64748b'>Add a companion in the card above, or load the sample household under Settings → Demo.</span></div>",
            unsafe_allow_html=True,
        )
        return

    st.divider()
    st.caption("Pets & tasks — everything below is for your current household.")

    with st.container(border=True):
        st.markdown('<p class="pp-card-title">Your pets</p>', unsafe_allow_html=True)
        pet_rows = [
            {"Name": p.name, "Species": p.pet_type, "Tasks": len(p.get_tasks())}
            for p in st.session_state.owner.pets
        ]
        _df(
            pd.DataFrame(pet_rows),
            column_config={
                "Name": st.column_config.TextColumn("Pet name", width="medium"),
                "Species": st.column_config.TextColumn("Species", width="small"),
                "Tasks": st.column_config.NumberColumn(
                    "# Tasks",
                    help="How many care tasks are on this pet’s list",
                    format="%d",
                    width="small",
                ),
            },
        )

    with st.container(border=True):
        st.markdown('<p class="pp-card-title">Quick add task</p>', unsafe_allow_html=True)
        pet_names = [p.name for p in st.session_state.owner.pets]
        spn = st.selectbox("For pet", pet_names, key="taskpet")
        pet = next(p for p in st.session_state.owner.pets if p.name == spn)
        t1, t2, t3 = st.columns(3)
        with t1:
            td = st.text_input("What to do", "Morning walk", key="tdesc")
        with t2:
            du = st.number_input("Minutes", 1, 240, 20, key="tdu")
        with t3:
            pr = st.selectbox(
                "Priority", [1, 2, 3, 4, 5], index=2, key="tpr", help="5 = most important"
            )
        fo = st.selectbox("How often", [f.value for f in TaskFrequency], key="tfo")
        wd_ix = 0
        mo_day = 15
        if fo == "weekly":
            wd_ix = st.selectbox(
                "Repeats on",
                list(range(7)),
                format_func=lambda i: WEEKDAY_LABELS[i],
                key="t_wd",
            )
        if fo == "monthly":
            mo_day = st.number_input("Day of month", 1, 31, 15, key="t_md")
        if st.button("Add task", key="btn_add_task"):
            tf = TaskFrequency(fo)
            kw = {}
            if tf == TaskFrequency.WEEKLY:
                kw["weekly_weekday"] = wd_ix
            if tf == TaskFrequency.MONTHLY:
                kw["monthly_day"] = mo_day
            pet.add_task(Task(td, du, tf, pr, **kw))
            st.rerun()

    with st.container(border=True):
        st.markdown('<p class="pp-card-title">Describe tasks with AI</p>', unsafe_allow_html=True)
        st.caption("Turn a short paragraph into tasks—we’ll match pets and validate details.")
        raw_nl = st.text_area(
            "Describe your routine",
            placeholder="Example: For Mochi I need a 20-minute morning walk and feeding twice daily—both top priority.",
            height=110,
            key="nlin",
            label_visibility="collapsed",
        )
        if st.button("Turn text into tasks", type="primary", key="btn_nl"):
            gr = check_user_input(raw_nl)
            if not gr.allowed:
                st.error(gr.user_message)
                return
            try:
                cl = _client_from_sidebar()
                if not cl.available():
                    st.error("Add your Groq API key in Settings or `.env` to use this.")
                    return
                data, _raw = extract_tasks_nl(cl, st.session_state.owner, raw_nl)
                added, errs = apply_tasks_to_pets(st.session_state.owner, data)
                for e in errs:
                    st.warning(e)
                st.success(f"Added {added} task(s).")
                st.rerun()
            except Exception as e:
                st.error(str(e))
                logger.exception("extract failed")


def tab_my_schedule() -> None:
    sch: Scheduler = st.session_state.scheduler
    all_t = sch.owner.get_all_tasks()
    upcoming = upcoming_task_occurrences(sch.owner, days=14)
    plan = sch.get_daily_plan("today")
    facts = build_schedule_facts(sch, "today") if plan else None

    section_header(
        "My schedule",
        "See recurring events on the calendar, build today’s plan, and log what you finished.",
    )

    # Full row: wide calendar (single tall block)
    with st.container(border=True):
        st.markdown('<p class="pp-card-title">Next 14 days</p>', unsafe_allow_html=True)
        st.caption("Recurring tasks expanded by date.")
        if upcoming:
            disp = [
                {
                    "When": r["date_label"],
                    "Pet": r["pet"],
                    "Task": r["task"],
                    "Min": r["minutes"],
                    "Pri": r["priority"],
                    "Repeats": r["recurrence"],
                }
                for r in upcoming
            ]
            _df(
                pd.DataFrame(disp),
                height=_FULL_CAL_HEIGHT,
                column_config={
                    "Min": st.column_config.NumberColumn("Min", format="%d"),
                    "Pri": st.column_config.NumberColumn("Pri", format="%d"),
                },
            )
        elif all_t:
            st.info("No dated occurrences in range—check recurring types under Household.")
        else:
            st.caption("Add tasks under **Household** to populate this calendar.")

    # Full row: plan controls (metrics + build — no checklist here)
    with st.container(border=True):
        st.markdown('<p class="pp-card-title">Today’s snapshot</p>', unsafe_allow_html=True)
        st.caption("Metrics reflect your latest built plan for today.")
        if st.session_state.last_plan_valid is False:
            st.warning(
                "Today’s tasks need more minutes than you have available—trim durations or priorities in Household."
            )
        if facts:
            ok = facts["validate_schedule"]
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Time planned", f"{facts['total_scheduled_minutes']} min")
            with m2:
                st.metric("Time available", f"{facts['available_minutes']} min")
            with m3:
                st.metric("Status", "On track" if ok else "Over budget")
        else:
            st.caption("Use **Build today’s plan** once you have tasks—metrics appear here.")
        if st.button("Build today’s plan", type="primary", key="gens"):
            sch.schedule_daily_plan("today")
            ok = sch.validate_schedule("today")
            st.session_state.last_plan_valid = ok
            st.rerun()

    # Full row: checklist (grows with tasks; not squeezed beside calendar)
    with st.container(border=True):
        st.markdown('<p class="pp-card-title">Today’s checklist</p>', unsafe_allow_html=True)
        if not plan:
            st.caption(
                "Build **today’s plan** in Today’s snapshot. Your ordered tasks will show here as checkboxes."
            )
        else:
            st.caption("Check off tasks as you finish them. Uncheck to mark a task not done again.")
            for i, task in enumerate(plan, start=1):
                pet = _pet_name_for_task(sch.owner, task)
                label = f"{i}. {pet} — {task.description} ({task.duration} min, P{task.priority})"
                wid = f"today_check_{id(task)}"
                checked = st.checkbox(label, value=task.completed, key=wid)
                if checked != task.completed:
                    if checked:
                        sch.mark_task_completed(task)
                    else:
                        sch.reset_task(task)
                    if wid in st.session_state:
                        del st.session_state[wid]
                    st.rerun()

    with st.container(border=True):
        st.markdown('<p class="pp-card-title">All tasks</p>', unsafe_allow_html=True)
        if all_t:
            rows = [
                {
                    "Pet": next((p.name for p in sch.owner.pets if t in p.tasks), "?"),
                    "Task": t.description,
                    "Minutes": t.duration,
                    "Priority": t.priority,
                    "Recurrence": task_recurrence_label(t),
                    "Done": "Yes" if t.completed else "No",
                }
                for t in all_t
            ]
            _df(
                pd.DataFrame(rows),
                height=_PAIR_TABLE_HEIGHT,
                column_config={
                    "Minutes": st.column_config.NumberColumn("Minutes", format="%d"),
                    "Priority": st.column_config.NumberColumn("Priority", format="%d"),
                },
            )
        else:
            st.info("No tasks yet—add some under **Household**.")


def tab_ask_pawpal() -> None:
    section_header(
        "Ask PawPal",
        "Scheduling tips grounded in your plan and local care notes—not medical advice.",
    )

    if st.session_state.get("assistant_a"):
        with st.container(border=True):
            st.markdown('<p class="pp-card-title">Conversation</p>', unsafe_allow_html=True)
            with st.chat_message("user"):
                st.write(st.session_state.assistant_q)
            with st.chat_message("assistant"):
                st.markdown(st.session_state.assistant_a)

    with st.container(border=True):
        st.markdown('<p class="pp-card-title">Your question</p>', unsafe_allow_html=True)
        use_agent = st.checkbox(
            "Let PawPal use your plan and retrieved tips",
            value=True,
            help="Uses your schedule and the knowledge index for a fuller answer.",
        )
        q = st.text_input(
            "Your question",
            placeholder="How should I prioritize if I only have an hour?",
            key="asq",
            label_visibility="collapsed",
        )
        ask = st.button("Get suggestions", type="primary", key="askbtn")

        if ask:
            gr = check_user_input(q)
            tr = TraceLog()
            tr.add("guardrail", "input_check", allowed=gr.allowed, reason=gr.reason)
            if not gr.allowed:
                st.session_state.assistant_q = q
                st.session_state.assistant_a = gr.user_message
                st.rerun()
            cl = _client_from_sidebar()
            if not cl.available():
                st.error("Add your API key in Settings or `.env`.")
                return
            idx = st.session_state.knowledge_index
            try:
                if use_agent:
                    ans, _tr2 = run_agentic_assistant(
                        cl,
                        st.session_state.scheduler,
                        idx,
                        q,
                        day="today",
                        trace=tr,
                    )
                else:
                    from pawpal_ai.orchestrator import assistant_answer_simple

                    ans = assistant_answer_simple(
                        cl, st.session_state.scheduler, idx, q, tr
                    )
                st.session_state.assistant_q = q
                st.session_state.assistant_a = ans
                st.rerun()
            except Exception as e:
                st.error(str(e))
                logger.exception("assistant")


def main() -> None:
    _inject_css()
    _init_state()
    render_sidebar()
    render_hero()

    t1, t2, t3 = st.tabs(["Household", "My Schedule", "Ask PawPal"])
    with t1:
        tab_household()
    with t2:
        tab_my_schedule()
    with t3:
        tab_ask_pawpal()


main()
