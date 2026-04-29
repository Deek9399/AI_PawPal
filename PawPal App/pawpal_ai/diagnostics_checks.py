from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Callable, List

from pawpal_system import Owner, Pet, Scheduler, Task, TaskFrequency

from pawpal_ai.guardrails import check_user_input


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def check_scheduler_conflict_fixture() -> CheckResult:
    owner = Owner("Diag Owner", available_hours={"monday": (time(9, 0), time(10, 0))})
    pet = Pet("T", "dog")
    owner.add_pet(pet)
    pet.add_task(Task("a", 40, TaskFrequency.DAILY, 5))
    pet.add_task(Task("b", 30, TaskFrequency.DAILY, 4))
    sch = Scheduler(owner)
    sch.schedule_daily_plan("monday")
    ok = sch.validate_schedule("monday")
    return CheckResult(
        name="schedule_conflict_detected",
        passed=not ok,
        detail="Fixture with 70 min tasks and 60 min availability should fail validation.",
    )


def check_scheduler_valid_fixture() -> CheckResult:
    owner = Owner("Diag Owner", available_hours={"monday": (time(9, 0), time(11, 0))})
    pet = Pet("T", "dog")
    owner.add_pet(pet)
    pet.add_task(Task("a", 30, TaskFrequency.DAILY, 5))
    pet.add_task(Task("b", 30, TaskFrequency.DAILY, 4))
    sch = Scheduler(owner)
    sch.schedule_daily_plan("monday")
    ok = sch.validate_schedule("monday")
    return CheckResult(
        name="schedule_valid_passes",
        passed=ok,
        detail="60 min tasks in 120 min window should validate.",
    )


def check_guardrail_diagnosis() -> CheckResult:
    r = check_user_input("Can you diagnose my dog's cough?")
    return CheckResult(
        name="guardrail_diagnosis",
        passed=not r.allowed,
        detail="Diagnosis-style prompt should be blocked.",
    )


def check_guardrail_ok() -> CheckResult:
    r = check_user_input("How should I order tasks when I only have one hour?")
    return CheckResult(
        name="guardrail_safe_question",
        passed=r.allowed,
        detail="Scheduling question should be allowed.",
    )


def check_today_availability_resolution() -> CheckResult:
    """Ensure 'today' maps to weekday for availability lookup."""
    from pawpal_system import resolve_day_for_availability

    key = resolve_day_for_availability("today")
    passed = key in [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    return CheckResult(
        name="today_maps_to_weekday",
        passed=passed,
        detail=f"resolve_day_for_availability('today') -> {key}",
    )


ALL_CHECKS: List[Callable[[], CheckResult]] = [
    check_today_availability_resolution,
    check_scheduler_conflict_fixture,
    check_scheduler_valid_fixture,
    check_guardrail_diagnosis,
    check_guardrail_ok,
]


def run_all_checks() -> List[CheckResult]:
    return [fn() for fn in ALL_CHECKS]
