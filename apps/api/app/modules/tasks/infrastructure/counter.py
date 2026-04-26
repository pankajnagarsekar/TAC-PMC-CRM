"""Atomic counter implementation for task serial numbers."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


class AtomicCounter:
    """Thread-safe atomic counter for incrementing task serial numbers."""

    COLLECTION_NAME = "task_sr_no_counters"

    @staticmethod
    async def get_next_value(db: AsyncIOMotorDatabase, org_id: str, project_id: str) -> int:
        """
        Get the next sequential sr_no for a project within an organization.
        Uses MongoDB atomic find_one_and_update to ensure thread-safety.

        Args:
            db: Motor async database instance
            org_id: Organization ID for scoping
            project_id: Project ID for scoping

        Returns:
            The next sequential sr_no (starting from 1)
        """
        collection = db[AtomicCounter.COLLECTION_NAME]
        result = await collection.find_one_and_update(
            {"organisation_id": org_id, "project_id": project_id},
            {"$inc": {"sequence": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return result["sequence"]
