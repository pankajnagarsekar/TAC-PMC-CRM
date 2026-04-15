from typing import Any, Dict, List

from app.modules.shared.domain.exceptions import DomainError
from app.modules.shared.domain.state_machine import StateMachine


class DailyProgressReport:
    """
    Aggregate Root for Site Operations.
    Enforces invariants for DPR lifecycle.
    """

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id") or data.get("_id")
        self.status = data.get("status", "Draft")
        self.image_count = data.get("image_count", 0)
        self.project_id = data.get("project_id")
        self.dpr_date = data.get("dpr_date")
        self.data = data

    def validate_for_submission(self):
        """Invariant: DPR requires progress notes before submission."""
        StateMachine.validate_transition("DPR", self.status, "Submitted")

        errors = []
        notes = self.data.get("progress_notes") or ""
        if not notes or len(str(notes).strip()) < 5:
            errors.append("Progress notes (min 5 chars) are required")

        if errors:
            raise DomainError(
                f"Validation failed: {'. '.join(errors)}",
                entity_id=str(self.id),
            )

    def can_modify(self):
        """Invariant: Modification only allowed in Draft or Rejected states."""
        StateMachine.check_modification_allowed("DPR", self.status)


class WorkerLog:
    """Entity representing a daily labor log."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.total_workers = data.get("total_workers", 0)
        self.total_hours = data.get("total_hours", 0)

    @classmethod
    def calculate_totals(
        cls, entries: List[Any], workers: List[Any]
    ) -> Dict[str, Any]:
        """Domain logic to aggregate worker counts and hours. Handles both dicts and Pydantic objects."""
        def get_val(obj, key, default=0):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        total_workers = (
            sum(get_val(e, "workers_count") for e in entries)
            if entries
            else len(workers or [])
        )
        total_hours = (
            sum(float(get_val(w, "hours_worked")) for w in workers) if workers else 0
        )
        return {"total_workers": total_workers, "total_hours": total_hours}
