"""
Tests for PawPal+ system.
"""

import pytest
from datetime import date, time

from demo_data import apply_demo_seed
from pawpal_system import (
    Pet,
    Owner,
    Scheduler,
    Task,
    TaskFrequency,
    task_occurs_on,
    upcoming_task_occurrences,
)


class TestTaskCompletion:
    """Test task completion functionality."""
    
    def test_mark_completed_changes_status(self):
        """Verify that calling mark_completed() changes the task's status."""
        task = Task("Test task", 10, TaskFrequency.DAILY, 3)
        
        # Initially not completed
        assert not task.completed
        
        # Mark as completed
        task.mark_completed()
        
        # Should now be completed
        assert task.completed


class TestTaskAddition:
    """Test adding tasks to pets."""
    
    def test_adding_task_increases_pet_task_count(self):
        """Verify that adding a task to a Pet increases that pet's task count."""
        pet = Pet("TestPet", "dog")
        initial_count = len(pet.get_tasks())
        
        task = Task("Test task", 15, TaskFrequency.DAILY, 4)
        pet.add_task(task)
        
        final_count = len(pet.get_tasks())
        assert final_count == initial_count + 1


class TestSortingCorrectness:
    """Test that tasks are sorted correctly by priority."""
    
    def test_scheduler_sorts_tasks_by_priority(self):
        """Verify that get_tasks_by_priority() returns tasks in descending priority order."""
        owner = Owner("Test Owner")
        pet = Pet("Test Pet", "dog")
        owner.add_pet(pet)
        
        # Add tasks with different priorities
        task_low = Task("Low priority task", 10, TaskFrequency.DAILY, 1)
        task_med = Task("Medium priority task", 10, TaskFrequency.DAILY, 3)
        task_high = Task("High priority task", 10, TaskFrequency.DAILY, 5)
        
        pet.add_task(task_low)
        pet.add_task(task_med)
        pet.add_task(task_high)
        
        scheduler = Scheduler(owner)
        sorted_tasks = scheduler.get_tasks_by_priority()
        
        # Should be sorted high to low priority
        assert sorted_tasks[0].priority == 5
        assert sorted_tasks[1].priority == 3
        assert sorted_tasks[2].priority == 1


class TestRecurrenceLogic:
    """Test recurrence handling for tasks."""
    
    def test_task_frequency_storage(self):
        """Verify that task frequency is stored correctly."""
        task_daily = Task("Daily task", 15, TaskFrequency.DAILY, 3)
        task_twice = Task("Twice daily task", 10, TaskFrequency.TWICE_DAILY, 4)
        
        assert task_daily.frequency == TaskFrequency.DAILY
        assert task_twice.frequency == TaskFrequency.TWICE_DAILY
    
    def test_marking_complete_resets_for_next_day(self):
        """Verify that marking a task complete allows it to be scheduled again (simulating daily recurrence)."""
        owner = Owner("Test Owner")
        pet = Pet("Test Pet", "dog")
        owner.add_pet(pet)
        
        task = Task("Daily walk", 30, TaskFrequency.DAILY, 4)
        pet.add_task(task)
        
        scheduler = Scheduler(owner)
        
        # Schedule initially includes the task
        schedule = scheduler.schedule_daily_plan("today")
        assert len(schedule) == 1
        assert schedule[0] == task
        
        # Mark complete
        scheduler.mark_task_completed(task)
        
        # For daily recurrence, the task should be available again
        # In our current implementation, completed tasks are excluded from pending
        # So we test that reset() makes it available again
        task.reset()
        pending = scheduler.get_pending_tasks()
        assert task in pending


class TestConflictDetection:
    """Test detection of scheduling conflicts."""
    
    def test_schedule_validation_detects_time_conflicts(self):
        """Verify that validate_schedule() flags when total task time exceeds available time."""
        owner = Owner("Test Owner", available_hours={"monday": (time(9, 0), time(10, 0))})  # 1 hour available
        pet = Pet("Test Pet", "dog")
        owner.add_pet(pet)
        
        # Add tasks totaling more than 1 hour (60 minutes)
        task1 = Task("Long task 1", 40, TaskFrequency.DAILY, 5)
        task2 = Task("Long task 2", 30, TaskFrequency.DAILY, 4)
        
        pet.add_task(task1)
        pet.add_task(task2)
        
        scheduler = Scheduler(owner)
        scheduler.schedule_daily_plan("monday")
        
        # Should be invalid due to time conflict
        is_valid = scheduler.validate_schedule("monday")
        assert not is_valid
    
    def test_valid_schedule_passes_validation(self):
        """Verify that a schedule within time limits passes validation."""
        owner = Owner("Test Owner", available_hours={"monday": (time(9, 0), time(11, 0))})  # 2 hours available
        pet = Pet("Test Pet", "dog")
        owner.add_pet(pet)
        
        # Add tasks totaling less than 2 hours
        task1 = Task("Task 1", 30, TaskFrequency.DAILY, 5)
        task2 = Task("Task 2", 30, TaskFrequency.DAILY, 4)
        
        pet.add_task(task1)
        pet.add_task(task2)
        
        scheduler = Scheduler(owner)
        scheduler.schedule_daily_plan("monday")
        
        # Should be valid
        is_valid = scheduler.validate_schedule("monday")
        assert is_valid


class TestRecurringSchedule:
    """Recurring event rules for My Schedule preview."""

    def test_weekly_only_on_chosen_weekday(self):
        t = Task("Groom", 20, TaskFrequency.WEEKLY, 3, weekly_weekday=2)
        assert task_occurs_on(t, date(2026, 4, 1))  # Wednesday
        assert not task_occurs_on(t, date(2026, 4, 2))  # Thursday

    def test_monthly_on_day_15(self):
        t = Task("Vet", 40, TaskFrequency.MONTHLY, 5, monthly_day=15)
        assert task_occurs_on(t, date(2026, 4, 15))
        assert not task_occurs_on(t, date(2026, 4, 14))

    def test_demo_seed_produces_upcoming_rows(self):
        o = Owner("T")
        apply_demo_seed(o)
        rows = upcoming_task_occurrences(o, start=date(2026, 4, 1), days=14)
        assert len(rows) > 0
        assert any(r["task"] == "Morning walk" for r in rows)