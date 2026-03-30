from decimal import Decimal
from typing import Any, Dict

from app.modules.shared.domain.exceptions import DomainError


class WorkOrder:
    """
    Aggregate Root for Contracting.
    Manages Work Order lifecycle and linked financial invariants.
    """

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id") or data.get("_id")
        self.status = data.get("status", "Draft")
        self.grand_total = Decimal(str(data.get("grand_total") or 0))
        self.project_id = data.get("project_id")
        self.data = data

    def validate_for_update(self, linked_pc_total: Decimal, new_total: Decimal):
        """Invariant: Cannot reduce Work Order below the total of already certified payments."""
        if self.status not in ["Draft", "Pending"]:
            raise DomainError(
                f"Only 'Draft' or 'Pending' Work Orders can be edited. "
                f"Current: {self.status}"
            )

        if linked_pc_total > 0 and new_total < linked_pc_total:
            msg = (
                f"Cannot reduce Work Order below linked Payment Certificate total of "
                f"{linked_pc_total}. New total: {new_total}"
            )
            raise DomainError(msg)


class Vendor:
    """Aggregate Root for Vendors."""

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id") or data.get("_id")
        self.organisation_id = data.get("organisation_id")
        self.is_active = data.get("is_active", True)
