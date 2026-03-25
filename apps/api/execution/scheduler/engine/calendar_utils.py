"""
Calendar utilities for CPM working-day arithmetic.
All date math in the engine goes through this module.

Key rules (Constitution §13 + Goa 6-day week standard):
    - Work week: Mon-Sat by default (ISO weekdays 1-6)
    - Sunday always excluded from Goa construction schedules
    - Holidays: specific dates excluded even on work_days
    - Duration unit: integer working days (no fractional days in MVP)
    - All inputs/outputs: Python date objects (no datetime, no timezones in engine)
"""
from datetime import date, timedelta
from typing import List, Set
from .interfaces import EngineCalendar, ResourceCalendar


# =============================================================================
# Internal helpers
# =============================================================================

def _holiday_set(calendar: EngineCalendar) -> Set[date]:
    """Convert holiday list to a frozenset for O(1) lookup."""
    return set(calendar.holidays)


def _resource_holiday_set(rc: ResourceCalendar) -> Set[date]:
    return set(rc.holidays)


# =============================================================================
# Core predicates
# =============================================================================

def is_work_day(d: date, calendar: EngineCalendar) -> bool:
    """
    Returns True if `d` is a working day per the given calendar.
    A day is working if:
        1. Its ISO weekday is in calendar.work_days, AND
        2. It is not in calendar.holidays
    """
    if d.isoweekday() not in calendar.work_days:
        return False
    if d in _holiday_set(calendar):
        return False
    return True


def is_work_day_resource(d: date, resource_calendar: ResourceCalendar) -> bool:
    """
    Same check for a resource-level calendar override.
    Used by resource leveling when a resource has a non-standard schedule.
    """
    if d.isoweekday() not in resource_calendar.work_days:
        return False
    if d in _resource_holiday_set(resource_calendar):
        return False
    return True


# =============================================================================
# Navigation
# =============================================================================

def next_work_day(d: date, calendar: EngineCalendar) -> date:
    """
    Returns the first working day AFTER `d` (exclusive of `d` itself).
    Used to compute successor's Early Start after predecessor's Early Finish.
    """
    current = d + timedelta(days=1)
    while not is_work_day(current, calendar):
        current += timedelta(days=1)
    return current


def prev_work_day(d: date, calendar: EngineCalendar) -> date:
    """
    Returns the last working day BEFORE `d` (exclusive of `d` itself).
    Used in backward pass: Late Finish of predecessor = day before successor's Late Start.
    """
    current = d - timedelta(days=1)
    while not is_work_day(current, calendar):
        current -= timedelta(days=1)
    return current


def first_work_day_on_or_after(d: date, calendar: EngineCalendar) -> date:
    """
    Returns `d` if it's a work day, else the next work day after `d`.
    Used to snap constraint dates and project start to valid working days.
    """
    current = d
    while not is_work_day(current, calendar):
        current += timedelta(days=1)
    return current


def last_work_day_on_or_before(d: date, calendar: EngineCalendar) -> date:
    """
    Returns `d` if it's a work day, else the previous work day before `d`.
    Used for ALAP and FNLT constraint snapping.
    """
    current = d
    while not is_work_day(current, calendar):
        current -= timedelta(days=1)
    return current


# =============================================================================
# Duration arithmetic
# =============================================================================

def add_work_days(start: date, duration: int, calendar: EngineCalendar) -> date:
    """
    Computes the finish date when starting on `start` for `duration` working days.
    The start date itself counts as day 1.

    Examples (Mon-Sat calendar, no holidays):
        add_work_days(Mon Mar 30, 1) → Mon Mar 30  (same day for 1-day task)
        add_work_days(Mon Mar 30, 5) → Fri Apr 3   (Mon-Fri)
        add_work_days(Mon Mar 30, 6) → Sat Apr 4   (Mon-Sat)
        add_work_days(Mon Mar 30, 7) → Mon Apr 6   (skips Sun Apr 5)

    For milestones: duration=0 → start itself is both start and finish.
    """
    if duration <= 0:
        return start

    # Ensure start is a work day (engine should have validated this already)
    current = first_work_day_on_or_after(start, calendar)

    work_days_counted = 0
    while True:
        if is_work_day(current, calendar):
            work_days_counted += 1
            if work_days_counted == duration:
                return current
        current += timedelta(days=1)


def subtract_work_days(finish: date, duration: int, calendar: EngineCalendar) -> date:
    """
    Computes the start date when a task finishes on `finish` and has `duration` working days.
    The finish date itself counts as the last day.
    Used in backward pass to compute Late Start from Late Finish.

    Examples (Mon-Sat calendar):
        subtract_work_days(Fri Apr 3, 5) → Mon Mar 30   (Fri backwards 5 days = Mon)
        subtract_work_days(Sat Apr 4, 6) → Mon Mar 30   (Sat backwards 6 days = Mon)
    """
    if duration <= 0:
        return finish

    current = last_work_day_on_or_before(finish, calendar)
    work_days_counted = 0
    while True:
        if is_work_day(current, calendar):
            work_days_counted += 1
            if work_days_counted == duration:
                return current
        current -= timedelta(days=1)


def count_work_days(start: date, finish: date, calendar: EngineCalendar) -> int:
    """
    Counts the number of working days from `start` to `finish` INCLUSIVE.
    Returns 0 if finish < start (or if both are the same non-work day).

    Used for:
        - Slack calculations (convert date difference to working days)
        - Duration verification after constraint application
    """
    if finish < start:
        return 0
    count = 0
    current = start
    while current <= finish:
        if is_work_day(current, calendar):
            count += 1
        current += timedelta(days=1)
    return count


def work_days_between_exclusive(finish_of_pred: date, start_of_succ: date, calendar: EngineCalendar) -> int:
    """
    Counts working days BETWEEN two dates (exclusive of both endpoints).
    Used for lag calculations.
    """
    if start_of_succ <= finish_of_pred + timedelta(days=1):
        return 0
    return count_work_days(
        finish_of_pred + timedelta(days=1),
        start_of_succ - timedelta(days=1),
        calendar,
    )


def add_work_days_offset(d: date, lag_days: int, calendar: EngineCalendar) -> date:
    """
    Applies a signed working-day offset to date `d`.
    lag_days > 0 → moves forward (lag)
    lag_days < 0 → moves backward (lead)
    lag_days = 0 → returns `d` unchanged

    Used by dependency calculators when applying lag/lead to computed dates.
    """
    if lag_days == 0:
        return d
    if lag_days > 0:
        # Move forward lag_days working days from d (d itself = day 0)
        current = d
        moved = 0
        while moved < lag_days:
            current += timedelta(days=1)
            if is_work_day(current, calendar):
                moved += 1
        return current
    else:
        # Move backward
        abs_lag = abs(lag_days)
        current = d
        moved = 0
        while moved < abs_lag:
            current -= timedelta(days=1)
            if is_work_day(current, calendar):
                moved += 1
        return current
