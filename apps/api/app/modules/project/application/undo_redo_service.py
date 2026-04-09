"""
Undo/Redo Service
Full-schedule snapshot-based undo/redo system for scheduler.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING
from app.modules.shared.domain.exceptions import ValidationError
from app.modules.project.infrastructure.schedule_history_repo import (
    ScheduleHistoryRepository,
)


class UndoRedoService:
    """
    Manages undo/redo stack for scheduler.
    Uses full-schedule snapshots with deduplication and depth enforcement.
    """

    MAX_STACK_DEPTH = 50
    FROZEN_STATES = {"Completed", "Cancelled", "Closed", "Paid"}

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repo = ScheduleHistoryRepository(db)

    async def capture_snapshot(
        self,
        project_id: str,
        org_id: str,
        user_id: str,
        change_type: str,
        summary: str,
        tasks: List[Dict[str, Any]],
    ) -> str:
        """
        Capture a snapshot of the schedule state.
        Deduplicates, prunes redo branch, enforces depth, updates HEAD pointer.
        Returns the new history entry ID.
        """
        # 1. Compute checksum for deduplication
        checksum = self._compute_checksum(tasks)

        # Ensure indexes exist
        await self.repo.ensure_indexes()

        # 2. Get current HEAD
        current = await self.repo.get_current(project_id, org_id)

        # 3. Deduplication: if checksum matches current, skip capture
        if current and current.get("data_checksum") == checksum:
            return current.get("id") or str(current.get("_id"))

        # 4. Prune redo branch: delete all entries above current position
        current_pos = current.get("stack_position", -1) if current else -1
        await self.repo.delete_above_position(project_id, org_id, current_pos)

        # 5. New position
        new_pos = current_pos + 1

        # 6. Enforce MAX_STACK_DEPTH — delete oldest if at limit
        count = await self.repo.count_stack(project_id, org_id)
        if count >= self.MAX_STACK_DEPTH:
            await self.repo.delete_oldest(project_id, org_id)
            # Note: positions not renumbered; relative queries still work

        # 7. Unset current flag on old HEAD
        if current:
            await self.repo.set_current(
                project_id, org_id, current.get("id") or str(current.get("_id")), False
            )

        # 8. Insert new entry as current HEAD
        entry = {
            "project_id": project_id,
            "organisation_id": org_id,
            "stack_position": new_pos,
            "is_current": True,
            "change_type": change_type,
            "summary": summary,
            "tasks_snapshot": tasks,
            "data_checksum": checksum,
            "captured_by": user_id,
            "captured_at": datetime.now(timezone.utc),
        }
        result = await self.repo.create(entry)
        return result.get("id") or str(result.get("_id"))

    async def undo(
        self, project_id: str, org_id: str, user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Undo the last change.
        Moves HEAD pointer back one position and returns the previous tasks.
        Raises ValidationError if at oldest entry or no history.
        Validates state machine constraints before returning.
        """
        current = await self.repo.get_current(project_id, org_id)
        if not current:
            raise ValidationError("No history available to undo")

        prev = await self.repo.get_entry_before(
            project_id, org_id, current.get("stack_position")
        )
        if not prev:
            raise ValidationError("Nothing to undo — already at oldest state")

        # Move pointer back
        await self.repo.set_current(
            project_id, org_id, current.get("id") or str(current.get("_id")), False
        )
        await self.repo.set_current(
            project_id, org_id, prev.get("id") or str(prev.get("_id")), True
        )

        # Validate state machine constraints
        await self._validate_no_frozen_state_revert(
            current.get("tasks_snapshot", []),
            prev.get("tasks_snapshot", [])
        )

        return prev.get("tasks_snapshot", [])

    async def redo(
        self, project_id: str, org_id: str, user_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Redo the next change (forward after undo).
        Moves HEAD pointer forward one position and returns the next tasks.
        Raises ValidationError if at newest entry or no history.
        Validates state machine constraints before returning.
        """
        current = await self.repo.get_current(project_id, org_id)
        if not current:
            raise ValidationError("No history available to redo")

        nxt = await self.repo.get_entry_after(
            project_id, org_id, current.get("stack_position")
        )
        if not nxt:
            raise ValidationError("Nothing to redo — already at latest state")

        # Move pointer forward
        await self.repo.set_current(
            project_id, org_id, current.get("id") or str(current.get("_id")), False
        )
        await self.repo.set_current(
            project_id, org_id, nxt.get("id") or str(nxt.get("_id")), True
        )

        # Validate state machine constraints
        await self._validate_no_frozen_state_revert(
            current.get("tasks_snapshot", []),
            nxt.get("tasks_snapshot", [])
        )

        return nxt.get("tasks_snapshot", [])

    async def list_history(
        self, project_id: str, org_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all history entries for a project (newest first).
        Excludes tasks_snapshot (too heavy for list view).
        """
        entries = await self.repo.list(
            {"project_id": project_id, "organisation_id": org_id},
            sort=[("stack_position", DESCENDING)],
            limit=self.MAX_STACK_DEPTH,
        )

        # Remove tasks_snapshot from list response
        return [
            {
                "id": e.get("id") or str(e.get("_id")),
                "stack_position": e.get("stack_position"),
                "is_current": e.get("is_current"),
                "change_type": e.get("change_type"),
                "summary": e.get("summary"),
                "captured_by": e.get("captured_by"),
                "captured_at": e.get("captured_at"),
            }
            for e in entries
        ]

    async def get_stack_info(self, project_id: str, org_id: str) -> Dict[str, Any]:
        """
        Return metadata about the undo/redo stack.
        Includes can_undo, can_redo, current version, summary.
        """
        current = await self.repo.get_current(project_id, org_id)
        if not current:
            return {
                "current_version": None,
                "current_position": None,
                "can_undo": False,
                "can_redo": False,
                "summary": None,
                "captured_at": None,
            }

        can_undo = await self.repo.has_entry_before(
            project_id, org_id, current.get("stack_position")
        )
        can_redo = await self.repo.has_entry_after(
            project_id, org_id, current.get("stack_position")
        )

        return {
            "current_version": current.get("id") or str(current.get("_id")),
            "current_position": current.get("stack_position"),
            "can_undo": can_undo,
            "can_redo": can_redo,
            "summary": current.get("summary"),
            "captured_at": current.get("captured_at"),
        }

    async def restore_to(
        self, project_id: str, org_id: str, user_id: str, change_id: str
    ) -> List[Dict[str, Any]]:
        """
        Restore schedule to a specific history point.
        Moves HEAD pointer to the requested entry.
        Captures a new "RESTORE" snapshot for undo of the restore.
        Returns the restored tasks_snapshot.
        """
        entry = await self.repo.get_by_entry_id(project_id, org_id, change_id)
        if not entry:
            raise ValidationError(f"History entry {change_id} not found")

        current = await self.repo.get_current(project_id, org_id)
        if current:
            await self.repo.set_current(
                project_id, org_id, current.get("id") or str(current.get("_id")), False
            )

        await self.repo.set_current(
            project_id, org_id, entry.get("id") or str(entry.get("_id")), True
        )

        # Capture the restore action itself as a new snapshot
        captured_at = entry.get("captured_at", "unknown")
        if isinstance(captured_at, dict):
            captured_at_str = captured_at.get("__str__", str(captured_at))
        else:
            captured_at_str = str(captured_at)
        restore_summary = f"Restored to: {entry.get('summary')} ({captured_at_str})"
        await self.capture_snapshot(
            project_id,
            org_id,
            user_id,
            "RESTORE",
            restore_summary,
            entry.get("tasks_snapshot", []),
        )

        return entry.get("tasks_snapshot", [])

    async def _validate_no_frozen_state_revert(
        self, current_tasks: List[Dict[str, Any]], restore_tasks: List[Dict[str, Any]]
    ) -> None:
        """
        Validate that undo/redo doesn't violate state machine.
        Raises ValidationError if any task in FROZEN state would have its status changed.
        """
        current_map = {t.get("task_id"): t for t in current_tasks}
        violations = []

        for task in restore_tasks:
            task_id = task.get("task_id")
            current = current_map.get(task_id)

            if current and current.get("status") in self.FROZEN_STATES:
                if task.get("status") != current.get("status"):
                    violations.append(task_id)

        if violations:
            raise ValidationError(
                f"Cannot undo/redo: tasks in final states cannot revert status: {', '.join(violations)}"
            )

    @staticmethod
    def _compute_checksum(tasks: List[Dict[str, Any]]) -> str:
        """Compute SHA-256 checksum of tasks for deduplication."""
        try:
            serialized = json.dumps(tasks, sort_keys=True, default=str).encode()
            return hashlib.sha256(serialized).hexdigest()
        except Exception:
            # Fallback: if serialization fails, use len as checksum (weak but safe)
            return hashlib.sha256(str(len(tasks)).encode()).hexdigest()
