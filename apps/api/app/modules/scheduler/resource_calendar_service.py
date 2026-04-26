"""
Resource Calendar Service

Manages resource calendars for scheduling calculations.
Integrates with the scheduler to account for working days and holidays.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.modules.scheduler.resource_calendar import ResourceCalendar, CalendarManager, CalendarException, ExceptionType
from app.modules.shared.domain.exceptions import ValidationError

logger = logging.getLogger(__name__)


class ResourceCalendarService:
    """
    Service layer for resource calendar management.
    Handles CRUD operations and integration with scheduler.
    """

    def __init__(self, db):
        """Initialize with MongoDB database."""
        self.db = db
        self.collection = db["resource_calendars"]
        self.manager = CalendarManager()

    async def get_calendar(self, resource_id: str, organisation_id: str) -> Optional[ResourceCalendar]:
        """
        Retrieve calendar for a resource.
        Returns None if not found.
        """
        doc = await self.collection.find_one({
            "resource_id": resource_id,
            "organisation_id": organisation_id
        })

        if not doc:
            return None

        return ResourceCalendar.from_dict(doc.get("calendar_data", {}))

    async def get_or_create_calendar(
        self,
        resource_id: str,
        organisation_id: str
    ) -> ResourceCalendar:
        """
        Get existing calendar or create default one.
        Default: Mon-Fri, 8am-5pm.
        """
        existing = await self.get_calendar(resource_id, organisation_id)
        if existing:
            return existing

        calendar = ResourceCalendar(resource_id=resource_id)
        await self.save_calendar(resource_id, organisation_id, calendar)
        return calendar

    async def save_calendar(
        self,
        resource_id: str,
        organisation_id: str,
        calendar: ResourceCalendar
    ) -> Dict:
        """Save/update resource calendar."""
        doc = {
            "resource_id": resource_id,
            "organisation_id": organisation_id,
            "calendar_data": calendar.to_dict(),
            "updated_at": datetime.utcnow()
        }

        result = await self.collection.update_one(
            {"resource_id": resource_id, "organisation_id": organisation_id},
            {"$set": doc},
            upsert=True
        )

        logger.info(f"Saved calendar for {resource_id} (org: {organisation_id})")
        return doc

    async def add_holiday(
        self,
        resource_id: str,
        organisation_id: str,
        start_date: datetime,
        end_date: datetime,
        reason: str = "Holiday"
    ) -> ResourceCalendar:
        """Add holiday period to calendar."""
        calendar = await self.get_or_create_calendar(resource_id, organisation_id)
        calendar.add_holidays(start_date, end_date, reason)
        await self.save_calendar(resource_id, organisation_id, calendar)
        return calendar

    async def add_working_override(
        self,
        resource_id: str,
        organisation_id: str,
        date: datetime,
        reason: str = "Working Day"
    ) -> ResourceCalendar:
        """Mark a weekend day as working."""
        calendar = await self.get_or_create_calendar(resource_id, organisation_id)
        calendar.add_working_override(date, reason)
        await self.save_calendar(resource_id, organisation_id, calendar)
        return calendar

    async def bulk_load_calendars(
        self,
        resource_ids: List[str],
        organisation_id: str
    ) -> Dict[str, ResourceCalendar]:
        """Load multiple calendars efficiently."""
        docs = await self.collection.find({
            "resource_id": {"$in": resource_ids},
            "organisation_id": organisation_id
        }).to_list(None)

        calendars = {}
        for doc in docs:
            calendar = ResourceCalendar.from_dict(doc.get("calendar_data", {}))
            calendars[doc["resource_id"]] = calendar

        # Create default calendars for missing resources
        for resource_id in resource_ids:
            if resource_id not in calendars:
                calendars[resource_id] = await self.get_or_create_calendar(
                    resource_id,
                    organisation_id
                )

        return calendars

    def get_calendar_for_scheduling(
        self,
        resource_calendars: Dict[str, ResourceCalendar],
        resource_id: Optional[str]
    ) -> Optional[ResourceCalendar]:
        """
        Get calendar for a specific resource during scheduling.
        Returns None if no specific resource assigned.
        """
        if not resource_id:
            return None
        return resource_calendars.get(resource_id)

    @staticmethod
    def apply_calendar_to_duration(
        calendar: Optional[ResourceCalendar],
        start_date: datetime,
        duration_days: int
    ) -> datetime:
        """
        Calculate end date accounting for working days.
        If no calendar, treats all days as working days.
        """
        if not calendar:
            # Standard behavior: assume all days work (for backward compatibility)
            from datetime import timedelta
            return start_date + timedelta(days=duration_days - 1)

        return calendar.add_working_days(start_date, duration_days)

    @staticmethod
    def get_working_days_between(
        calendar: Optional[ResourceCalendar],
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """
        Calculate working days between dates.
        If no calendar, treats all days as working days.
        """
        if not calendar:
            # Standard behavior
            from datetime import timedelta
            delta = (end_date - start_date).days + 1
            return max(0, delta)

        return calendar.working_days_between(start_date, end_date, inclusive_end=True)
