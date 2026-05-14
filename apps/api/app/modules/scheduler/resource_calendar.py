"""
Resource Calendar Module

Manages individual work calendars per resource with support for:
- Custom working hours (default: Mon-Fri, 8hrs/day)
- Holidays (single days or ranges)
- Availability overrides (exceptions)
- Working day calculations with non-working period skipping
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum


class ExceptionType(str, Enum):
    """Exception types for calendar overrides."""
    HOLIDAY = "holiday"          # Non-working day
    WORKING = "working"          # Working day (overrides weekend)
    HALF_DAY = "half_day"       # Half working day (4 hours)
    UNAVAILABLE = "unavailable"  # Partially available (custom hours)


class WorkingHours:
    """Represents working hours for a single day."""

    def __init__(self, start_hour: int = 8, end_hour: int = 17, lunch_start: int = 12, lunch_end: int = 13):
        """
        Initialize working hours.

        Args:
            start_hour: Start time (0-23, default 8 = 8am)
            end_hour: End time (0-23, default 17 = 5pm)
            lunch_start: Lunch start (default 12 = noon)
            lunch_end: Lunch end (default 13 = 1pm)
        """
        if not (0 <= start_hour < 24):
            raise ValueError(f"Invalid start_hour: {start_hour}")
        if not (0 <= end_hour < 24):
            raise ValueError(f"Invalid end_hour: {end_hour}")
        if start_hour >= end_hour:
            raise ValueError(f"start_hour ({start_hour}) must be < end_hour ({end_hour})")

        self.start_hour = start_hour
        self.end_hour = end_hour
        self.lunch_start = lunch_start
        self.lunch_end = lunch_end

    @property
    def total_hours(self) -> float:
        """Calculate total working hours (excluding lunch)."""
        work_hours = self.end_hour - self.start_hour
        # Only subtract lunch if it falls within working hours
        if self.lunch_start >= self.start_hour and self.lunch_end <= self.end_hour:
            lunch_hours = self.lunch_end - self.lunch_start
            return max(0, work_hours - lunch_hours)
        return max(0, work_hours)

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "lunch_start": self.lunch_start,
            "lunch_end": self.lunch_end,
            "total_hours": self.total_hours
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkingHours":
        """Deserialize from dictionary."""
        return cls(
            start_hour=data.get("start_hour", 8),
            end_hour=data.get("end_hour", 17),
            lunch_start=data.get("lunch_start", 12),
            lunch_end=data.get("lunch_end", 13)
        )


class CalendarException:
    """Represents a calendar exception (holiday, override, etc.)."""

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        exception_type: ExceptionType,
        reason: Optional[str] = None,
        working_hours: Optional[WorkingHours] = None
    ):
        """
        Initialize calendar exception.

        Args:
            start_date: Exception start date (inclusive)
            end_date: Exception end date (inclusive)
            exception_type: Type of exception (holiday, working, half_day, etc.)
            reason: Reason for exception (e.g., "Public Holiday", "Training")
            working_hours: Custom working hours (for UNAVAILABLE type)
        """
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        if start_date > end_date:
            raise ValueError(f"start_date ({start_date}) must be <= end_date ({end_date})")

        self.start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        self.end_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)
        self.exception_type = exception_type
        self.reason = reason or ""
        self.working_hours = working_hours or WorkingHours()

    def contains(self, date: datetime) -> bool:
        """Check if exception contains date."""
        normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)
        return self.start_date <= normalized <= self.end_date

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "exception_type": self.exception_type.value,
            "reason": self.reason,
            "working_hours": self.working_hours.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CalendarException":
        """Deserialize from dictionary."""
        wh = None
        if data.get("working_hours"):
            wh = WorkingHours.from_dict(data["working_hours"])

        return cls(
            start_date=data["start_date"],
            end_date=data["end_date"],
            exception_type=ExceptionType(data["exception_type"]),
            reason=data.get("reason"),
            working_hours=wh
        )


class ResourceCalendar:
    """
    Manages work calendar for a single resource.

    Features:
    - Standard working week (configurable)
    - Holiday management
    - Availability exceptions
    - Working day calculations
    """

    def __init__(
        self,
        resource_id: str,
        working_days: Optional[List[int]] = None,
        standard_hours: Optional[WorkingHours] = None,
        exceptions: Optional[List[CalendarException]] = None
    ):
        """
        Initialize resource calendar.

        Args:
            resource_id: Unique resource identifier
            working_days: List of working day indices (0=Mon, 6=Sun). Default: [0-4] (Mon-Fri)
            standard_hours: Standard working hours. Default: 8am-5pm (Mon-Fri)
            exceptions: List of calendar exceptions (holidays, overrides)
        """
        self.resource_id = resource_id
        self.working_days = working_days or [0, 1, 2, 3, 4]  # Mon-Fri
        self.standard_hours = standard_hours or WorkingHours()
        self.exceptions: List[CalendarException] = exceptions or []

    def is_working_day(self, date: datetime) -> bool:
        """
        Check if date is a working day.

        Priority:
        1. WORKING/HALF_DAY/UNAVAILABLE exceptions (highest priority - override holidays)
        2. HOLIDAY exceptions
        3. Standard working days
        """
        normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Check for WORKING overrides first (highest priority)
        for exc in self.exceptions:
            if exc.contains(normalized):
                if exc.exception_type == ExceptionType.WORKING:
                    return True
                elif exc.exception_type in [ExceptionType.HALF_DAY, ExceptionType.UNAVAILABLE]:
                    return True  # Partial working days still count as working days

        # Check for HOLIDAY exceptions
        for exc in self.exceptions:
            if exc.contains(normalized):
                if exc.exception_type == ExceptionType.HOLIDAY:
                    return False

        # Check standard working days (0=Monday, 6=Sunday)
        return normalized.weekday() in self.working_days

    def get_working_hours(self, date: datetime) -> Optional[WorkingHours]:
        """
        Get working hours for a specific date.
        Returns None if not a working day.
        """
        normalized = date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Check exceptions first
        for exc in self.exceptions:
            if exc.contains(normalized):
                if exc.exception_type == ExceptionType.HOLIDAY:
                    return None
                elif exc.exception_type in [ExceptionType.HALF_DAY, ExceptionType.UNAVAILABLE]:
                    return exc.working_hours

        # Return standard hours if working day
        if self.is_working_day(normalized):
            return self.standard_hours

        return None

    def add_exception(self, exception: CalendarException) -> None:
        """Add calendar exception."""
        # Remove overlapping exceptions of same type
        self.exceptions = [
            e for e in self.exceptions
            if not (e.exception_type == exception.exception_type
                    and e.start_date <= exception.end_date
                    and e.end_date >= exception.start_date)
        ]
        self.exceptions.append(exception)

    def add_holidays(self, start_date: datetime, end_date: datetime, reason: str = "Holiday") -> None:
        """Add holiday exception (range or single day)."""
        exc = CalendarException(
            start_date=start_date,
            end_date=end_date,
            exception_type=ExceptionType.HOLIDAY,
            reason=reason
        )
        self.add_exception(exc)

    def add_working_override(self, date: datetime, reason: str = "Working Day") -> None:
        """Mark a weekend day as working."""
        exc = CalendarException(
            start_date=date,
            end_date=date,
            exception_type=ExceptionType.WORKING,
            reason=reason
        )
        self.add_exception(exc)

    def next_working_day(self, from_date: datetime, offset_days: int = 1) -> datetime:
        """
        Find the next working day from given date.

        Args:
            from_date: Starting date
            offset_days: Number of working days to advance (can be negative)

        Returns:
            Next working day (or previous if offset_days < 0)
        """
        current = from_date.replace(hour=0, minute=0, second=0, microsecond=0)

        if offset_days >= 0:
            step = timedelta(days=1)
            while offset_days > 0:
                current += step
                if self.is_working_day(current):
                    offset_days -= 1
        else:
            step = timedelta(days=-1)
            while offset_days < 0:
                current += step
                if self.is_working_day(current):
                    offset_days += 1

        return current

    def working_days_between(self, start_date: datetime, end_date: datetime, inclusive_end: bool = True) -> int:
        """
        Calculate working days between two dates.

        Args:
            start_date: Start date
            end_date: End date
            inclusive_end: Include end_date in count (default: True)

        Returns:
            Number of working days
        """
        start = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

        if start > end:
            return 0

        count = 0
        current = start
        final_date = end if inclusive_end else end - timedelta(days=1)

        while current <= final_date:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)

        return count

    def add_working_days(self, start_date: datetime, num_days: int) -> datetime:
        """
        Add working days to a start date (skip non-working days).

        Args:
            start_date: Starting date
            num_days: Number of working days to add (can be negative)

        Returns:
            End date after adding working days
        """
        if num_days == 0:
            return start_date

        if num_days < 0:
            return self.next_working_day(start_date, num_days)

        current = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        working_days_added = 0

        while working_days_added < num_days:
            current += timedelta(days=1)
            if self.is_working_day(current):
                working_days_added += 1

        return current

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            "resource_id": self.resource_id,
            "working_days": self.working_days,
            "standard_hours": self.standard_hours.to_dict(),
            "exceptions": [e.to_dict() for e in self.exceptions]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ResourceCalendar":
        """Deserialize from dictionary."""
        # Handle flat project calendar structure or nested resource structure
        if "shift_start" in data:
            # Flat structure (ProjectCalendarDTO)
            def _parse_hour(t_str):
                try:
                    if not t_str:
                        return 8
                    return int(str(t_str).split(":")[0])
                except (ValueError, IndexError, AttributeError):
                    return 8

            wh = WorkingHours(
                start_hour=_parse_hour(data.get("shift_start", "08:00")),
                end_hour=_parse_hour(data.get("shift_end", "17:00")),
                lunch_start=_parse_hour(data.get("lunch_start", "13:00")),
                lunch_end=_parse_hour(data.get("lunch_end", "14:00"))
            )
        else:
            # Nested structure (ResourceCalendar)
            wh = WorkingHours.from_dict(data.get("standard_hours", {}))

        exceptions = [CalendarException.from_dict(e) for e in data.get("exceptions", [])]

        return cls(
            resource_id=data.get("resource_id") or data.get("project_id") or "default",
            working_days=data.get("working_days", [0, 1, 2, 3, 4, 5]),
            standard_hours=wh,
            exceptions=exceptions
        )


class CalendarManager:
    """
    Manages multiple resource calendars.
    Caches calendars and provides bulk operations.
    """

    def __init__(self):
        """Initialize calendar manager."""
        self._calendars: Dict[str, ResourceCalendar] = {}

    def get_or_create(
        self,
        resource_id: str,
        working_days: Optional[List[int]] = None,
        standard_hours: Optional[WorkingHours] = None
    ) -> ResourceCalendar:
        """Get existing calendar or create new one."""
        if resource_id not in self._calendars:
            self._calendars[resource_id] = ResourceCalendar(
                resource_id=resource_id,
                working_days=working_days,
                standard_hours=standard_hours
            )
        return self._calendars[resource_id]

    def register(self, calendar: ResourceCalendar) -> None:
        """Register a resource calendar."""
        self._calendars[calendar.resource_id] = calendar

    def get(self, resource_id: str) -> Optional[ResourceCalendar]:
        """Get calendar by resource ID."""
        return self._calendars.get(resource_id)

    def list_all(self) -> List[ResourceCalendar]:
        """List all registered calendars."""
        return list(self._calendars.values())

    def to_dict(self) -> Dict:
        """Serialize all calendars."""
        return {
            resource_id: cal.to_dict()
            for resource_id, cal in self._calendars.items()
        }
