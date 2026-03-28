from typing import Dict, Any, Optional
from app.modules.shared.domain.state_machine import StateMachine

class Project:
    """
    Aggregate Root for Project Management.
    Enforces project lifecycle rules and state invariants.
    """
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id") or data.get("_id")
        self.project_id = data.get("project_id")
        self.status = data.get("status", "Draft")
        self.data = data

    def validate_transition(self, next_status: str):
        """Invariant: Project status must follow allowed transitions."""
        StateMachine.validate_transition("PROJECT", self.status, next_status)

    def can_modify(self):
        """Invariant: Project can only be modified in non-final states."""
        StateMachine.check_modification_allowed("PROJECT", self.status)

class ProjectBudget:
    """Entity representing a project's line-item budget."""
    def __init__(self, data: Dict[str, Any]):
        self.category_id = data.get("category_id")
        self.original_budget = data.get("original_budget", 0)
        self.revised_budget = data.get("revised_budget", 0)
