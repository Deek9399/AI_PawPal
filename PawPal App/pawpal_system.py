"""
PawPal+ System
A pet care scheduling application that helps owners plan daily tasks for their pets.
"""

from typing import Dict, List, Optional, Tuple
from datetime import date, datetime, timedelta, time
from enum import Enum


def resolve_day_for_availability(day: str) -> str:
    """
    Map logical day labels to keys used in Owner.available_hours.
    'today' -> current weekday name (lowercase), e.g. 'monday'.
    """
    if day.lower() == "today":
        return datetime.now().strftime("%A").lower()
    return day.lower()


class TaskFrequency(Enum):
    """Enumeration of possible task frequencies."""
    DAILY = "daily"
    TWICE_DAILY = "twice_daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    AS_NEEDED = "as_needed"


WEEKDAY_LABELS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day


def task_recurrence_label(task: "Task") -> str:
    """Human-readable recurrence for UI."""
    if task.frequency == TaskFrequency.DAILY:
        return "Every day"
    if task.frequency == TaskFrequency.TWICE_DAILY:
        return "Twice daily"
    if task.frequency == TaskFrequency.WEEKLY:
        wd = task.weekly_weekday if task.weekly_weekday is not None else 0
        return f"Every {WEEKDAY_LABELS[wd]}"
    if task.frequency == TaskFrequency.MONTHLY:
        d = task.monthly_day if task.monthly_day is not None else 1
        return f"Monthly (day {d})"
    return "As needed"


def task_occurs_on(task: "Task", d: date) -> bool:
    """Whether this task appears on calendar day d for scheduling previews."""
    wd = d.weekday()
    if task.frequency in (TaskFrequency.DAILY, TaskFrequency.TWICE_DAILY):
        return True
    if task.frequency == TaskFrequency.WEEKLY:
        target = task.weekly_weekday if task.weekly_weekday is not None else 0
        return wd == target
    if task.frequency == TaskFrequency.MONTHLY:
        want = task.monthly_day if task.monthly_day is not None else 1
        dim = _days_in_month(d.year, d.month)
        return d.day == min(want, dim)
    if task.frequency == TaskFrequency.AS_NEEDED:
        return False
    return False


def upcoming_task_occurrences(
    owner: "Owner",
    start: Optional[date] = None,
    *,
    days: int = 14,
) -> List[Dict[str, object]]:
    """
    Flatten tasks into dated rows for 'My Schedule' upcoming view.
    AS_NEEDED tasks appear once as a single flexible row (no specific date).
    """
    start = start or date.today()
    end = start + timedelta(days=days - 1)
    rows: List[Dict[str, object]] = []
    flexible: List[Dict[str, object]] = []

    for pet in owner.pets:
        for task in pet.get_tasks():
            if task.frequency == TaskFrequency.AS_NEEDED:
                flexible.append(
                    {
                        "date": None,
                        "date_label": "Flexible",
                        "pet": pet.name,
                        "task": task.description,
                        "minutes": task.duration,
                        "priority": task.priority,
                        "recurrence": task_recurrence_label(task),
                    }
                )
                continue
            d = start
            while d <= end:
                if task_occurs_on(task, d):
                    rows.append(
                        {
                            "date": d.isoformat(),
                            "date_label": d.strftime("%a %b %d"),
                            "pet": pet.name,
                            "task": task.description,
                            "minutes": task.duration,
                            "priority": task.priority,
                            "recurrence": task_recurrence_label(task),
                        }
                    )
                d += timedelta(days=1)

    rows.sort(key=lambda r: (r["date"] or "9999", -int(r["priority"])))  # type: ignore[arg-type]
    return rows + flexible


class Task:
    """Represents a single pet care activity."""

    def __init__(
        self,
        description: str,
        duration: int,
        frequency: TaskFrequency,
        priority: int = 3,
        *,
        weekly_weekday: Optional[int] = None,
        monthly_day: Optional[int] = None,
    ):
        """
        Initialize a Task.

        Args:
            description: Description of the task
            duration: Duration in minutes
            frequency: How often the task should be performed
            priority: Priority level (1-5, where 5 is highest)
            weekly_weekday: For WEEKLY — 0=Monday .. 6=Sunday
            monthly_day: For MONTHLY — day of month 1-31
        """
        self.description = description
        self.duration = duration
        self.frequency = frequency
        self.priority = priority
        self.weekly_weekday = weekly_weekday
        self.monthly_day = monthly_day
        self.completed = False
    
    def mark_completed(self) -> None:
        """Mark the task as completed."""
        self.completed = True
    
    def reset(self) -> None:
        """Reset the task to incomplete status."""
        self.completed = False
    
    def __str__(self) -> str:
        """String representation of the task."""
        status = "✓" if self.completed else "○"
        return f"{status} {self.description} ({self.duration}min, priority {self.priority})"


class Pet:
    """Represents a pet and manages its care tasks."""
    
    def __init__(self, name: str, pet_type: str, breed: str = "", age: int = 0, special_needs: List[str] = None):
        """
        Initialize a Pet.
        
        Args:
            name: Pet's name
            pet_type: Type of pet (e.g., "dog", "cat")
            breed: Breed of pet
            age: Age in years
            special_needs: List of special care needs
        """
        self.name = name
        self.pet_type = pet_type
        self.breed = breed
        self.age = age
        self.special_needs = special_needs or []
        self.tasks: List[Task] = []
    
    def add_task(self, task: Task) -> None:
        """Add a task to this pet's care routine."""
        self.tasks.append(task)
    
    def remove_task(self, task: Task) -> None:
        """Remove a task from this pet's care routine."""
        if task in self.tasks:
            self.tasks.remove(task)
    
    def get_tasks(self) -> List[Task]:
        """Get all tasks for this pet."""
        return self.tasks.copy()
    
    def get_pending_tasks(self) -> List[Task]:
        """Get tasks that are not yet completed."""
        return [task for task in self.tasks if not task.completed]
    
    def get_completed_tasks(self) -> List[Task]:
        """Get tasks that have been completed."""
        return [task for task in self.tasks if task.completed]
    
    def __str__(self) -> str:
        """String representation of the pet."""
        return f"{self.name} ({self.pet_type}, {self.age} years old)"


class Owner:
    """Represents a pet owner who manages multiple pets."""
    
    def __init__(self, name: str, available_hours: Dict[str, Tuple[time, time]] = None, preferences: Dict = None):
        """
        Initialize an Owner.
        
        Args:
            name: Owner's name
            available_hours: Dict mapping day names to (start, end) time tuples
            preferences: Dict of owner preferences
        """
        self.name = name
        self.available_hours = available_hours or {}
        self.preferences = preferences or {}
        self.pets: List[Pet] = []
    
    def add_pet(self, pet: Pet) -> None:
        """Add a pet to the owner's care."""
        if pet not in self.pets:
            self.pets.append(pet)
    
    def remove_pet(self, pet: Pet) -> None:
        """Remove a pet from the owner's care."""
        if pet in self.pets:
            self.pets.remove(pet)
    
    def get_all_tasks(self) -> List[Task]:
        """Get all tasks across all pets owned by this owner."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_tasks())
        return all_tasks
    
    def get_tasks_by_pet(self, pet: Pet) -> List[Task]:
        """Get tasks for a specific pet."""
        if pet in self.pets:
            return pet.get_tasks()
        return []
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks across all pets."""
        return [task for task in self.get_all_tasks() if not task.completed]
    
    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks across all pets."""
        return [task for task in self.get_all_tasks() if task.completed]
    
    def get_availability(self) -> Dict[str, Tuple[time, time]]:
        """Return owner's available hours."""
        return self.available_hours
    
    def get_constraints(self) -> Dict:
        """Return owner's constraints and preferences."""
        return self.preferences
    
    def __str__(self) -> str:
        """String representation of the owner."""
        return f"{self.name} (owns {len(self.pets)} pet{'s' if len(self.pets) != 1 else ''})"


class Scheduler:
    """The brain that organizes and manages tasks across all pets."""
    
    def __init__(self, owner: Owner):
        """
        Initialize a Scheduler.
        
        Args:
            owner: The pet owner whose tasks to schedule
        """
        self.owner = owner
        self.daily_plans: Dict[str, List[Task]] = {}  # day -> list of tasks
    
    def get_all_tasks(self) -> List[Task]:
        """Retrieve all tasks across all pets."""
        return self.owner.get_all_tasks()
    
    def get_tasks_by_priority(self) -> List[Task]:
        """Get all tasks sorted by priority (highest first)."""
        tasks = self.get_all_tasks()
        return sorted(tasks, key=lambda t: t.priority, reverse=True)
    
    def get_tasks_by_pet(self, pet: Pet) -> List[Task]:
        """Get tasks for a specific pet."""
        return self.owner.get_tasks_by_pet(pet)
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks across all pets."""
        return self.owner.get_pending_tasks()
    
    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks across all pets."""
        return self.owner.get_completed_tasks()
    
    def schedule_daily_plan(self, day: str = "today") -> List[Task]:
        """
        Generate a daily schedule for the given day.
        
        Args:
            day: The day to schedule for (e.g., "monday", "today")
        
        Returns:
            List of tasks scheduled for the day
        """
        # Simple scheduling: get all pending tasks and sort by priority
        pending_tasks = self.get_pending_tasks()
        scheduled = sorted(pending_tasks, key=lambda t: t.priority, reverse=True)
        
        # Store the plan
        self.daily_plans[day] = scheduled
        return scheduled
    
    def get_daily_plan(self, day: str = "today") -> List[Task]:
        """Get the scheduled plan for a specific day."""
        return self.daily_plans.get(day, [])
    
    def mark_task_completed(self, task: Task) -> bool:
        """Mark a specific task as completed."""
        if task in self.get_all_tasks():
            task.mark_completed()
            return True
        return False
    
    def reset_task(self, task: Task) -> bool:
        """Reset a task to incomplete status."""
        if task in self.get_all_tasks():
            task.reset()
            return True
        return False
    
    def get_schedule_summary(self, day: str = "today") -> str:
        """Get a human-readable summary of the daily schedule."""
        plan = self.get_daily_plan(day)
        if not plan:
            return f"No tasks scheduled for {day}."
        
        summary = f"Daily Schedule for {day}:\n"
        for i, task in enumerate(plan, 1):
            summary += f"{i}. {task}\n"
        return summary
    
    def validate_schedule(self, day: str = "today") -> bool:
        """
        Validate that the schedule for the day is feasible.
        
        Basic validation: check for time conflicts (simplified).
        """
        plan = self.get_daily_plan(day)
        if not plan:
            return True
        
        # Simple validation: ensure no overlapping tasks (assuming sequential)
        total_time = sum(task.duration for task in plan)
        available_time = self._get_available_time_minutes(day)
        
        return total_time <= available_time
    
    def _get_available_time_minutes(self, day: str) -> int:
        """Get available time in minutes for the given day (matches weekday keys in available_hours)."""
        key = resolve_day_for_availability(day)
        for stored_day, window in self.owner.available_hours.items():
            if stored_day.lower() == key:
                start, end = window
                available_minutes = (
                    datetime.combine(datetime.today(), end)
                    - datetime.combine(datetime.today(), start)
                ).total_seconds() // 60
                return int(available_minutes)
        # Default 8 hours if no specific availability
        return 480
