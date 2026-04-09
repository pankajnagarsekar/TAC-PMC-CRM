"""
Baseline Locking Manager for Scheduler

Implements immutability enforcement for baseline-locked tasks.
Prevents modifications after baseline is set and provides snapshot management.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.modules.shared.domain.exceptions import DataFreezeError, ValidationError

logger = logging.getLogger(__name__)


class BaselineManager:
    """
    Sovereign manager for baseline lifecycle and immutability enforcement.

    Responsibilities:
    - Mark tasks as baseline_locked
    - Enforce immutability on locked tasks
    - Create and manage snapshots on lock
    - Support unlock operations (with audit)
    """

    IMMUTABLE_FIELDS = {
        "scheduled_start",
        "scheduled_finish",
        "duration",
        "task_name",
        "is_critical",
        "slack"
    }

    def __init__(self, db):
        """Initialize with database connection for snapshot storage."""
        self.db = db
        self.snapshots_collection = db["baseline_snapshots"]

    async def lock_baseline(
        self,
        project_id: str,
        organisation_id: str,
        user_id: str,
        tasks: List[Dict[str, Any]],
        baseline_version: int = 1,
    ) -> Dict[str, Any]:
        """
        Lock all tasks in the current schedule as a baseline.

        Args:
            project_id: Project identifier
            organisation_id: Organization identifier
            user_id: User locking the baseline
            tasks: Current task list to lock
            baseline_version: Baseline version number (default: 1)

        Returns:
            Dict with lock status and snapshot reference

        Raises:
            ValidationError: If tasks are invalid
        """
        if not tasks:
            raise ValidationError("Cannot lock baseline with empty task list")

        # Mark all tasks as baseline_locked and add baseline dates
        locked_tasks = [
            {
                **task,
                "baseline_locked": True,
                "baseline_version": baseline_version,
                "baseline_locked_at": datetime.now(timezone.utc).isoformat(),
                "baseline_locked_by": user_id,
                # Store baseline dates for variance tracking
                "baseline_start": task.get("scheduled_start"),
                "baseline_finish": task.get("scheduled_finish"),
            }
            for task in tasks
        ]

        # Create snapshot of locked schedule state (with baseline dates)
        snapshot = await self._create_snapshot(
            project_id,
            organisation_id,
            user_id,
            locked_tasks,
            baseline_version
        )

        logger.info(
            f"BASELINE_LOCKED: Project {project_id} - "
            f"{len(locked_tasks)} tasks locked at version {baseline_version}"
        )

        return {
            "locked_tasks": len(locked_tasks),
            "baseline_version": baseline_version,
            "snapshot_id": str(snapshot.get("_id", "")),
            "locked_at": datetime.now(timezone.utc).isoformat(),
            "locked_by": user_id,
        }

    async def unlock_baseline(
        self,
        project_id: str,
        organisation_id: str,
        user_id: str,
        tasks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Unlock tasks from baseline to allow modifications.

        Args:
            project_id: Project identifier
            organisation_id: Organization identifier
            user_id: User unlocking the baseline
            tasks: Task list to unlock

        Returns:
            Dict with unlock status
        """
        unlocked_tasks = [
            {
                **task,
                "baseline_locked": False,
            }
            for task in tasks
        ]

        logger.info(
            f"BASELINE_UNLOCKED: Project {project_id} - "
            f"{len(unlocked_tasks)} tasks unlocked"
        )

        return {
            "unlocked_tasks": len(unlocked_tasks),
            "unlocked_at": datetime.now(timezone.utc).isoformat(),
            "unlocked_by": user_id,
        }

    def check_baseline_locked(
        self,
        task: Dict[str, Any],
        attempting_modification: bool = True,
    ) -> bool:
        """
        Check if a task is baseline-locked.

        Args:
            task: Task object to check
            attempting_modification: If True, raises DataFreezeError if locked

        Returns:
            True if locked, False otherwise

        Raises:
            DataFreezeError: If task is locked and modification attempted
        """
        is_locked = task.get("baseline_locked", False)

        if is_locked and attempting_modification:
            raise DataFreezeError(
                "TASK",
                f"Baseline (v{task.get('baseline_version', '?')})"
            )

        return is_locked

    def validate_modifications(
        self,
        original_task: Dict[str, Any],
        modifications: Dict[str, Any],
    ) -> bool:
        """
        Validate that modifications don't violate baseline lock.

        Args:
            original_task: Original task state
            modifications: Proposed changes

        Returns:
            True if modifications are allowed

        Raises:
            DataFreezeError: If attempting to modify immutable fields
        """
        is_locked = original_task.get("baseline_locked", False)

        if not is_locked:
            return True

        # Check which fields are being modified
        modified_fields = set(modifications.keys())
        immutable_modified = modified_fields & self.IMMUTABLE_FIELDS

        if immutable_modified:
            raise DataFreezeError(
                "TASK",
                f"Baseline (v{original_task.get('baseline_version', '?')})"
            )

        # Allow metadata updates (notes, comments, etc.)
        return True

    async def _create_snapshot(
        self,
        project_id: str,
        organisation_id: str,
        user_id: str,
        tasks: List[Dict[str, Any]],
        baseline_version: int,
    ) -> Dict[str, Any]:
        """
        Create immutable snapshot of baseline state.

        Args:
            project_id: Project identifier
            organisation_id: Organization identifier
            user_id: User creating snapshot
            tasks: Task list to snapshot
            baseline_version: Baseline version

        Returns:
            Snapshot document
        """
        snapshot_doc = {
            "project_id": project_id,
            "organisation_id": organisation_id,
            "baseline_version": baseline_version,
            "tasks": tasks,
            "created_by": user_id,
            "created_at": datetime.now(timezone.utc),
            "task_count": len(tasks),
            "total_duration_days": self._calculate_duration(tasks),
        }

        result = await self.snapshots_collection.insert_one(snapshot_doc)

        logger.info(
            f"SNAPSHOT_CREATED: {result.inserted_id} for project {project_id}"
        )

        return {**snapshot_doc, "_id": result.inserted_id}

    async def get_snapshot(
        self,
        project_id: str,
        organisation_id: str,
        baseline_version: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a baseline snapshot by version.

        Args:
            project_id: Project identifier
            organisation_id: Organization identifier
            baseline_version: Baseline version to retrieve

        Returns:
            Snapshot document or None if not found
        """
        snapshot = await self.snapshots_collection.find_one(
            {
                "project_id": project_id,
                "organisation_id": organisation_id,
                "baseline_version": baseline_version,
            }
        )

        return snapshot

    async def list_snapshots(
        self,
        project_id: str,
        organisation_id: str,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List all baseline snapshots for a project.

        Args:
            project_id: Project identifier
            organisation_id: Organization identifier
            limit: Max results
            skip: Pagination offset

        Returns:
            List of snapshot summaries
        """
        snapshots = await (
            self.snapshots_collection
            .find({
                "project_id": project_id,
                "organisation_id": organisation_id,
            })
            .sort("baseline_version", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )

        return [
            {
                "baseline_version": s.get("baseline_version"),
                "created_at": s.get("created_at"),
                "created_by": s.get("created_by"),
                "task_count": s.get("task_count"),
                "total_duration_days": s.get("total_duration_days"),
            }
            for s in snapshots
        ]

    def _calculate_duration(self, tasks: List[Dict[str, Any]]) -> int:
        """Calculate total project duration from task list."""
        if not tasks:
            return 0

        # Find the maximum finish date
        max_finish = None
        for task in tasks:
            finish = task.get("scheduled_finish")
            if finish:
                if max_finish is None or finish > max_finish:
                    max_finish = finish

        # Find the minimum start date
        min_start = None
        for task in tasks:
            start = task.get("scheduled_start")
            if start:
                if min_start is None or start < min_start:
                    min_start = start

        if min_start and max_finish:
            # Parse dates and calculate difference
            try:
                from datetime import datetime as dt
                fmt = "%Y-%m-%d"
                start_dt = dt.strptime(str(min_start)[:10], fmt)
                finish_dt = dt.strptime(str(max_finish)[:10], fmt)
                return (finish_dt - start_dt).days
            except Exception:
                return 0

        return 0
