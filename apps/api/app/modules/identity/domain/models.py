from typing import Dict, Any, Optional
from app.modules.shared.domain.exceptions import DomainError

class User:
    """
    Aggregate Root for Identity and Access Management.
    Enforces user-level invariants.
    """
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id") or data.get("_id")
        self.email = data.get("email")
        self.active_status = data.get("active_status", True)
        self.data = data

    def validate_for_deactivation(self, actor_user_id: str):
        """Invariant: User cannot deactivate themselves."""
        if str(self.id) == str(actor_user_id):
             raise DomainError("Cannot deactivate yourself", entity_id=str(self.id))
