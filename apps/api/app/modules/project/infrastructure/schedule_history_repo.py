"""
Schedule History Repository
Stores immutable snapshots of schedule states for undo/redo functionality.
"""
from typing import Optional, List, Dict, Any
from pymongo import ASCENDING, DESCENDING
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
from bson import ObjectId
from app.modules.shared.infrastructure.base_repository import BaseRepository


class ScheduleHistoryEntry(BaseModel):
    """Pydantic model for schedule history entries."""
    model_config = {"arbitrary_types_allowed": True, "populate_by_name": True}

    id: Optional[str] = Field(None, alias="_id")
    project_id: str
    organisation_id: str
    stack_position: int  # monotonic per project, not renumbered on prune
    is_current: bool  # True for exactly one entry per project (HEAD pointer)
    change_type: str  # "SAVE_SCHEDULE" | "BULK_UPDATE" | "DELETE_TASK" | "RESTORE"
    summary: str  # human-readable label
    tasks_snapshot: List[Dict[str, Any]]  # full task array at this point
    data_checksum: str  # SHA-256 for deduplication
    captured_by: str  # user_id
    captured_at: Optional[Dict[str, Any]] = None
    created_at: Optional[Dict[str, Any]] = None
    updated_at: Optional[Dict[str, Any]] = None


class ScheduleHistoryRepository(BaseRepository[ScheduleHistoryEntry]):
    """Repository for schedule history with stack-aware queries."""

    def __init__(self, db: AsyncIOMotorDatabase):
        super().__init__(db, "schedule_history", ScheduleHistoryEntry)

    async def ensure_indexes(self):
        """Create necessary indexes for stack-based queries."""
        # Compound unique index: (project_id, organisation_id, stack_position)
        await self.collection.create_index(
            [
                ("project_id", ASCENDING),
                ("organisation_id", ASCENDING),
                ("stack_position", ASCENDING)
            ],
            unique=True,
            name="idx_stack_position"
        )

        # Fast HEAD pointer lookup
        await self.collection.create_index(
            [
                ("project_id", ASCENDING),
                ("organisation_id", ASCENDING),
                ("is_current", ASCENDING)
            ],
            name="idx_current_pointer"
        )

        # Deduplication guard
        await self.collection.create_index(
            [
                ("project_id", ASCENDING),
                ("organisation_id", ASCENDING),
                ("data_checksum", ASCENDING)
            ],
            name="idx_checksum"
        )

    async def get_current(
        self, project_id: str, org_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get the current HEAD entry (is_current=True)."""
        return await self.find_one({
            "project_id": project_id,
            "organisation_id": org_id,
            "is_current": True,
        })

    async def get_entry_before(
        self, project_id: str, org_id: str, position: int
    ) -> Optional[Dict[str, Any]]:
        """Get the closest entry with stack_position < position."""
        return await self.find_one(
            {
                "project_id": project_id,
                "organisation_id": org_id,
                "stack_position": {"$lt": position}
            },
            sort=[("stack_position", DESCENDING)]
        )

    async def get_entry_after(
        self, project_id: str, org_id: str, position: int
    ) -> Optional[Dict[str, Any]]:
        """Get the closest entry with stack_position > position."""
        return await self.find_one(
            {
                "project_id": project_id,
                "organisation_id": org_id,
                "stack_position": {"$gt": position}
            },
            sort=[("stack_position", ASCENDING)]
        )

    async def has_entry_before(
        self, project_id: str, org_id: str, position: int
    ) -> bool:
        """Check if any entry exists before the given position."""
        return await self.count({
            "project_id": project_id,
            "organisation_id": org_id,
            "stack_position": {"$lt": position}
        }) > 0

    async def has_entry_after(
        self, project_id: str, org_id: str, position: int
    ) -> bool:
        """Check if any entry exists after the given position."""
        return await self.count({
            "project_id": project_id,
            "organisation_id": org_id,
            "stack_position": {"$gt": position}
        }) > 0

    async def delete_above_position(
        self, project_id: str, org_id: str, position: int
    ) -> int:
        """
        Prune redo branch after an undo.
        Deletes all entries where stack_position > position.
        Returns count of deleted documents.
        """
        result = await self.collection.delete_many({
            "project_id": project_id,
            "organisation_id": org_id,
            "stack_position": {"$gt": position}
        })
        return result.deleted_count

    async def delete_oldest(
        self, project_id: str, org_id: str
    ) -> Optional[str]:
        """
        Remove the oldest entry to stay within MAX_STACK_DEPTH.
        Returns the deleted entry's ID, or None if no entries exist.
        """
        oldest = await self.find_one(
            {
                "project_id": project_id,
                "organisation_id": org_id
            },
            sort=[("stack_position", ASCENDING)]
        )
        if oldest:
            deleted = await self.delete(oldest["id"])
            return oldest["id"] if deleted else None
        return None

    async def count_stack(self, project_id: str, org_id: str) -> int:
        """Count total entries in the stack for a project."""
        return await self.count({
            "project_id": project_id,
            "organisation_id": org_id
        })

    async def set_current(
        self, project_id: str, org_id: str, entry_id: str, is_current: bool
    ) -> bool:
        """
        Set is_current flag for an entry.
        Returns True if updated, False if not found.
        """
        # Convert entry_id to ObjectId if it's a string
        try:
            oid = ObjectId(entry_id) if isinstance(entry_id, str) else entry_id
        except Exception:
            oid = entry_id

        result = await self.collection.update_one(
            {"_id": oid},
            {"$set": {"is_current": is_current}}
        )
        return result.modified_count > 0

    async def get_by_entry_id(
        self, project_id: str, org_id: str, entry_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a specific entry by ID with org scope verification."""
        try:
            oid = ObjectId(entry_id) if isinstance(entry_id, str) else entry_id
        except Exception:
            return None

        return await self.find_one({
            "_id": oid,
            "project_id": project_id,
            "organisation_id": org_id
        })
