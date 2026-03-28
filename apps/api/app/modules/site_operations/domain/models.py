from typing import List, Optional, Dict, Any
from datetime import datetime
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
        """Invariant: DPR requires minimum 4 images before submission."""
        StateMachine.validate_transition("DPR", self.status, "Submitted")
        if self.image_count < 4:
            raise DomainError(
                f"DPR requires minimum 4 images for submission. Current: {self.image_count}",
                entity_id=str(self.id)
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
    def calculate_totals(cls, entries: List[Dict[str, Any]], workers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Domain logic to aggregate worker counts and hours."""
        total_workers = sum(e.get("workers_count", 0) for e in entries) if entries else len(workers or [])
        total_hours = sum(float(w.get("hours_worked", 0)) for w in workers) if workers else 0
        return {
            "total_workers": total_workers,
            "total_hours": total_hours
        }
