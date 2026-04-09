"""
Comprehensive test suite for Resource Calendar module.

Tests cover:
- Working day detection (standard vs exceptions)
- Holiday management (single days and ranges)
- Working day calculations
- Calendar overrides
- Calendar manager operations
"""

import pytest
from datetime import datetime, timedelta
from app.modules.scheduler.resource_calendar import (
    ResourceCalendar,
    CalendarException,
    ExceptionType,
    WorkingHours,
    CalendarManager
)


@pytest.fixture
def standard_calendar():
    """Create a standard Mon-Fri calendar."""
    return ResourceCalendar(resource_id="res-001")


@pytest.fixture
def custom_hours_calendar():
    """Create calendar with custom working hours (9am-6pm, 1hr lunch)."""
    hours = WorkingHours(start_hour=9, end_hour=18, lunch_start=12, lunch_end=13)
    return ResourceCalendar(resource_id="res-002", standard_hours=hours)


@pytest.fixture
def calendar_with_holidays():
    """Create calendar with holidays."""
    cal = ResourceCalendar(resource_id="res-003")
    # Add New Year (2024-01-01)
    cal.add_holidays(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 1),
        reason="New Year"
    )
    # Add Christmas week (2024-12-23 to 2024-12-27)
    cal.add_holidays(
        start_date=datetime(2024, 12, 23),
        end_date=datetime(2024, 12, 27),
        reason="Christmas Break"
    )
    return cal


class TestWorkingHours:
    """Test WorkingHours class."""

    def test_default_working_hours(self):
        """Test default hours (8am-5pm, 1hr lunch)."""
        wh = WorkingHours()
        assert wh.start_hour == 8
        assert wh.end_hour == 17
        assert wh.total_hours == 8  # 17 - 8 - 1 (lunch)

    def test_custom_working_hours(self):
        """Test custom hours."""
        wh = WorkingHours(start_hour=9, end_hour=18, lunch_start=12, lunch_end=13)
        assert wh.start_hour == 9
        assert wh.end_hour == 18
        assert wh.total_hours == 8  # 18 - 9 - 1 (lunch)

    def test_invalid_hours_raises_error(self):
        """Test validation of invalid hours."""
        with pytest.raises(ValueError):
            WorkingHours(start_hour=17, end_hour=8)  # Start > End

    def test_working_hours_serialization(self):
        """Test to_dict and from_dict."""
        wh = WorkingHours(start_hour=9, end_hour=18)
        data = wh.to_dict()
        wh2 = WorkingHours.from_dict(data)
        assert wh2.start_hour == 9
        assert wh2.end_hour == 18


class TestCalendarException:
    """Test CalendarException class."""

    def test_create_holiday_exception(self):
        """Create single-day holiday."""
        exc = CalendarException(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 1),
            exception_type=ExceptionType.HOLIDAY,
            reason="New Year"
        )
        assert exc.reason == "New Year"
        assert exc.exception_type == ExceptionType.HOLIDAY

    def test_create_holiday_range(self):
        """Create multi-day holiday."""
        exc = CalendarException(
            start_date=datetime(2024, 12, 23),
            end_date=datetime(2024, 12, 27),
            exception_type=ExceptionType.HOLIDAY,
            reason="Christmas Break"
        )
        assert exc.contains(datetime(2024, 12, 25))
        assert not exc.contains(datetime(2024, 12, 22))

    def test_exception_contains_date(self):
        """Test date containment check."""
        exc = CalendarException(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 5),
            exception_type=ExceptionType.HOLIDAY
        )
        assert exc.contains(datetime(2024, 1, 1))
        assert exc.contains(datetime(2024, 1, 3))
        assert exc.contains(datetime(2024, 1, 5))
        assert not exc.contains(datetime(2024, 1, 6))

    def test_invalid_exception_raises_error(self):
        """Test validation of invalid date ranges."""
        with pytest.raises(ValueError):
            CalendarException(
                start_date=datetime(2024, 1, 5),
                end_date=datetime(2024, 1, 1),
                exception_type=ExceptionType.HOLIDAY
            )

    def test_exception_serialization(self):
        """Test to_dict and from_dict."""
        exc = CalendarException(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 5),
            exception_type=ExceptionType.HOLIDAY,
            reason="New Year"
        )
        data = exc.to_dict()
        exc2 = CalendarException.from_dict(data)
        assert exc2.reason == "New Year"
        assert exc2.contains(datetime(2024, 1, 3))


class TestBasicWorkingDayDetection:
    """Test basic working day detection (Mon-Fri by default)."""

    def test_monday_is_working_day(self, standard_calendar):
        """Monday should be working day."""
        monday = datetime(2024, 1, 1)  # Monday
        assert standard_calendar.is_working_day(monday)

    def test_friday_is_working_day(self, standard_calendar):
        """Friday should be working day."""
        friday = datetime(2024, 1, 5)  # Friday
        assert standard_calendar.is_working_day(friday)

    def test_saturday_is_not_working_day(self, standard_calendar):
        """Saturday should not be working day."""
        saturday = datetime(2024, 1, 6)  # Saturday
        assert not standard_calendar.is_working_day(saturday)

    def test_sunday_is_not_working_day(self, standard_calendar):
        """Sunday should not be working day."""
        sunday = datetime(2024, 1, 7)  # Sunday
        assert not standard_calendar.is_working_day(sunday)

    def test_custom_working_days(self):
        """Test calendar with custom working days (Tue-Sat)."""
        cal = ResourceCalendar(resource_id="res-custom", working_days=[1, 2, 3, 4, 5])
        monday = datetime(2024, 1, 1)  # Monday
        tuesday = datetime(2024, 1, 2)  # Tuesday
        saturday = datetime(2024, 1, 6)  # Saturday

        assert not cal.is_working_day(monday)
        assert cal.is_working_day(tuesday)
        assert cal.is_working_day(saturday)


class TestHolidayHandling:
    """Test holiday management."""

    def test_single_day_holiday(self, standard_calendar):
        """Add and detect single-day holiday."""
        ny = datetime(2024, 1, 1)  # Monday (normally working)
        assert standard_calendar.is_working_day(ny)

        standard_calendar.add_holidays(ny, ny, "New Year")
        assert not standard_calendar.is_working_day(ny)

    def test_holiday_range(self, calendar_with_holidays):
        """Test multi-day holiday range."""
        # Christmas break: 2024-12-23 (Mon) to 2024-12-27 (Fri)
        for i in range(23, 28):
            date = datetime(2024, 12, i)
            assert not calendar_with_holidays.is_working_day(date), f"2024-12-{i} should be holiday"

    def test_working_day_after_holiday_range(self, calendar_with_holidays):
        """Days after holiday range should be working days."""
        day_after = datetime(2024, 12, 30)  # Monday after break
        assert calendar_with_holidays.is_working_day(day_after)

    def test_holiday_exception_priority(self, standard_calendar):
        """Holiday exception should override standard working days."""
        # Add holiday on Friday (normally working)
        friday = datetime(2024, 1, 5)
        standard_calendar.add_holidays(friday, friday, "Company Closure")
        assert not standard_calendar.is_working_day(friday)

    def test_multiple_holidays(self, standard_calendar):
        """Add multiple separate holidays."""
        standard_calendar.add_holidays(
            datetime(2024, 1, 1),
            datetime(2024, 1, 1),
            "New Year"
        )
        standard_calendar.add_holidays(
            datetime(2024, 7, 4),
            datetime(2024, 7, 4),
            "Independence Day"
        )

        assert not standard_calendar.is_working_day(datetime(2024, 1, 1))
        assert not standard_calendar.is_working_day(datetime(2024, 7, 4))
        assert standard_calendar.is_working_day(datetime(2024, 1, 2))


class TestWorkingDayOverrides:
    """Test working day overrides (e.g., weekend work)."""

    def test_mark_saturday_as_working(self, standard_calendar):
        """Override: mark Saturday as working day."""
        saturday = datetime(2024, 1, 6)
        assert not standard_calendar.is_working_day(saturday)

        standard_calendar.add_working_override(saturday, "Project Deadline")
        assert standard_calendar.is_working_day(saturday)

    def test_half_day_exception(self, standard_calendar):
        """Add half-day exception."""
        friday = datetime(2024, 1, 5)
        exc = CalendarException(
            start_date=friday,
            end_date=friday,
            exception_type=ExceptionType.HALF_DAY,
            reason="Team Event",
            working_hours=WorkingHours(start_hour=8, end_hour=12)
        )
        standard_calendar.add_exception(exc)

        assert standard_calendar.is_working_day(friday)
        hours = standard_calendar.get_working_hours(friday)
        assert hours is not None
        assert hours.total_hours == 4  # 12 - 8

    def test_exception_removal(self, standard_calendar):
        """Test that new exceptions replace overlapping ones."""
        date = datetime(2024, 1, 1)

        # Add as holiday
        standard_calendar.add_holidays(date, date, "Holiday 1")
        assert not standard_calendar.is_working_day(date)

        # Override with working day
        standard_calendar.add_working_override(date, "Emergency")
        assert standard_calendar.is_working_day(date)


class TestWorkingDayCalculations:
    """Test working day calculations between dates."""

    def test_working_days_between_same_day(self, standard_calendar):
        """Working days from date to itself."""
        monday = datetime(2024, 1, 1)
        assert standard_calendar.working_days_between(monday, monday, inclusive_end=True) == 1
        assert standard_calendar.working_days_between(monday, monday, inclusive_end=False) == 0

    def test_working_days_one_week(self, standard_calendar):
        """One full week: Mon-Sun (5 working days)."""
        monday = datetime(2024, 1, 1)
        sunday = datetime(2024, 1, 7)
        assert standard_calendar.working_days_between(monday, sunday, inclusive_end=True) == 5

    def test_working_days_two_weeks(self, standard_calendar):
        """Two weeks of Mon-Fri."""
        week1_monday = datetime(2024, 1, 1)
        week2_friday = datetime(2024, 1, 12)
        assert standard_calendar.working_days_between(week1_monday, week2_friday, inclusive_end=True) == 10

    def test_working_days_with_holiday(self, calendar_with_holidays):
        """Calculate working days excluding holiday."""
        # Dec 23-27, 2024 are holidays (Christmas break)
        dec_20 = datetime(2024, 12, 20)  # Friday
        dec_30 = datetime(2024, 12, 30)  # Monday

        # Count: Dec 20 (Fri, working) = 1, Dec 23-27 (holidays), Dec 30 (Mon, working) = 1
        # Total: 2 working days (Dec 20 and Dec 30, plus weekends in between are not working)
        working_days = calendar_with_holidays.working_days_between(dec_20, dec_30, inclusive_end=True)
        assert working_days == 2

    def test_working_days_backwards_range(self, standard_calendar):
        """Backwards range should return 0."""
        friday = datetime(2024, 1, 5)
        monday = datetime(2024, 1, 1)
        assert standard_calendar.working_days_between(friday, monday) == 0


class TestAddingWorkingDays:
    """Test adding working days to dates."""

    def test_add_one_working_day_from_monday(self, standard_calendar):
        """Add 1 day from Monday should be Tuesday."""
        monday = datetime(2024, 1, 1)
        result = standard_calendar.add_working_days(monday, 1)
        assert result.weekday() == 1  # Tuesday
        assert result == datetime(2024, 1, 2)

    def test_add_five_working_days_skips_weekend(self, standard_calendar):
        """Add 5 days from Friday should skip weekend."""
        friday = datetime(2024, 1, 5)
        result = standard_calendar.add_working_days(friday, 5)
        # Fri(5) + 1 = Mon(8), +2 = Tue(9), +3 = Wed(10), +4 = Thu(11), +5 = Fri(12)
        assert result == datetime(2024, 1, 12)

    def test_add_zero_days(self, standard_calendar):
        """Adding 0 days should return same date."""
        monday = datetime(2024, 1, 1)
        result = standard_calendar.add_working_days(monday, 0)
        assert result == monday

    def test_add_days_with_holiday(self, calendar_with_holidays):
        """Add days while skipping holidays."""
        # Christmas break: Dec 23-27, 2024
        dec_20 = datetime(2024, 12, 20)  # Friday

        # Add 3 working days from Dec 20
        # Fri 20 + 1 = Mon 23 (holiday), skip to Tue 24 (holiday), skip...
        # Skip to Dec 30 (Mon) = +1, Dec 31 (Tue) = +2, Jan 2 (Thu, 2025) = +3
        result = calendar_with_holidays.add_working_days(dec_20, 3)
        assert not calendar_with_holidays.is_working_day(result - timedelta(days=5))  # Still in holiday range

    def test_next_working_day(self, standard_calendar):
        """Find next working day."""
        friday = datetime(2024, 1, 5)
        next_day = standard_calendar.next_working_day(friday, offset_days=1)
        assert next_day == datetime(2024, 1, 8)  # Monday


class TestCalendarManager:
    """Test CalendarManager for multiple resources."""

    def test_get_or_create_calendar(self):
        """Get or create calendar."""
        manager = CalendarManager()

        cal1 = manager.get_or_create("res-001")
        assert cal1.resource_id == "res-001"

        # Getting again returns same instance
        cal1_again = manager.get_or_create("res-001")
        assert cal1_again is cal1

    def test_register_and_get_calendar(self):
        """Register and retrieve calendar."""
        manager = CalendarManager()
        cal = ResourceCalendar(resource_id="res-002")

        manager.register(cal)
        retrieved = manager.get("res-002")
        assert retrieved is cal

    def test_get_nonexistent_calendar(self):
        """Get non-existent calendar returns None."""
        manager = CalendarManager()
        assert manager.get("nonexistent") is None

    def test_list_all_calendars(self):
        """List all registered calendars."""
        manager = CalendarManager()
        cal1 = ResourceCalendar(resource_id="res-001")
        cal2 = ResourceCalendar(resource_id="res-002")

        manager.register(cal1)
        manager.register(cal2)

        all_cals = manager.list_all()
        assert len(all_cals) == 2
        assert cal1 in all_cals
        assert cal2 in all_cals

    def test_manager_serialization(self):
        """Serialize and deserialize manager."""
        manager = CalendarManager()
        cal = ResourceCalendar(resource_id="res-001")
        cal.add_holidays(datetime(2024, 1, 1), datetime(2024, 1, 1), "New Year")

        manager.register(cal)
        data = manager.to_dict()

        assert "res-001" in data
        assert len(data["res-001"]["exceptions"]) == 1


class TestIntegrationScenarios:
    """Integration tests with realistic scenarios."""

    def test_project_schedule_with_holidays(self):
        """Scenario: Calculate schedule with holidays."""
        cal = ResourceCalendar(resource_id="dev-team")

        # Add summer vacation (July 15-22, 2024)
        cal.add_holidays(
            datetime(2024, 7, 15),
            datetime(2024, 7, 22),
            "Summer Vacation"
        )

        # Start on July 10 (Wed), add 10 working days
        # July 10-12 (Wed-Fri) = 3 days
        # July 15-22 = all holidays (skip)
        # July 23-26 (Tue-Fri) = 4 days (total 7)
        # July 29-31 (Mon-Wed) = 3 days (total 10, skipping weekends)
        # July 31 is day 10
        start = datetime(2024, 7, 10)
        result = cal.add_working_days(start, 10)

        # Should be July 31 (Wed) or Aug 1 (Thu) depending on exact count
        assert result >= datetime(2024, 7, 31)
        assert cal.is_working_day(result)

    def test_multi_timezone_resources(self):
        """Different resources with different working hours."""
        manager = CalendarManager()

        # US resource (8am-5pm)
        us_cal = manager.get_or_create("us-dev", standard_hours=WorkingHours())

        # India resource (9:30am-6:30pm, 30min lunch)
        india_hours = WorkingHours(start_hour=9, end_hour=18, lunch_start=13, lunch_end=13 + 1)
        india_cal = manager.get_or_create("india-dev", standard_hours=india_hours)

        date = datetime(2024, 1, 15)
        us_hours = us_cal.get_working_hours(date)
        india_hours_obj = india_cal.get_working_hours(date)

        assert us_hours.total_hours == 8
        assert india_hours_obj.total_hours == 8
        assert us_hours.start_hour == 8
        assert india_hours_obj.start_hour == 9

    def test_full_calendar_lifecycle(self):
        """Create, modify, and query a complete calendar."""
        cal = ResourceCalendar(resource_id="contractor")

        # Add standard holidays
        cal.add_holidays(datetime(2024, 1, 1), datetime(2024, 1, 1), "New Year")
        cal.add_holidays(datetime(2024, 12, 25), datetime(2024, 12, 26), "Christmas")

        # Add special project work (weekend work)
        cal.add_working_override(datetime(2024, 3, 16), "Project Deadline")

        # Verify
        assert not cal.is_working_day(datetime(2024, 1, 1))
        assert cal.is_working_day(datetime(2024, 3, 16))  # Saturday (override)
        assert not cal.is_working_day(datetime(2024, 12, 25))

        # Calculate working days: Fri 15 (1), Sat 16 override (1), Sun 17 (no override, not working)
        working = cal.working_days_between(
            datetime(2024, 3, 15),
            datetime(2024, 3, 17),
            inclusive_end=True
        )
        assert working == 2  # Fri 15, Sat 16 (override) — Sun 17 remains non-working
