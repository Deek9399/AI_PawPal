"""Sample household and tasks to demonstrate My Schedule and recurring events."""

from __future__ import annotations

from pawpal_system import Owner, Pet, Task, TaskFrequency


def apply_demo_seed(owner: Owner) -> None:
    """
    Load mock pets and tasks (daily, weekly, monthly, as-needed) for UI demos.
    Replaces nothing by itself—caller should use an empty owner or clear pets first.
    """
    owner.name = "Alex"
    owner.pets.clear()

    mochi = Pet("Mochi", "dog", "Shiba", 3)
    whiskers = Pet("Whiskers", "cat", "Domestic", 5)
    owner.add_pet(mochi)
    owner.add_pet(whiskers)

    mochi.add_task(Task("Morning walk", 25, TaskFrequency.DAILY, 4))
    mochi.add_task(
        Task(
            "Grooming & nail trim",
            40,
            TaskFrequency.WEEKLY,
            3,
            weekly_weekday=2,
        )
    )

    whiskers.add_task(Task("Feeding", 10, TaskFrequency.TWICE_DAILY, 5))
    whiskers.add_task(
        Task(
            "Vet wellness visit",
            45,
            TaskFrequency.MONTHLY,
            5,
            monthly_day=15,
        )
    )
    whiskers.add_task(Task("Brush coat", 15, TaskFrequency.AS_NEEDED, 2))
