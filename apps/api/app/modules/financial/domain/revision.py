from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional
from app.modules.shared.domain.financial_engine import FinancialEngine

class BudgetRevision:
    """
    Domain Entity representing a Variation Order (VO) or Budget Revision.
    Gates budget modifications behind an approval workflow.
    
    Status Lifecycle: DRAFT -> SUBMITTED -> APPROVED | REJECTED
    """

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("_id") or data.get("id")
        self.organisation_id = data.get("organisation_id")
        self.project_id = data.get("project_id")
        self.category_id = data.get("category_id")
        self.old_budget = FinancialEngine.round(Decimal(str(data.get("old_budget", 0))))
        self.new_budget = FinancialEngine.round(Decimal(str(data.get("new_budget", 0))))
        self.reason = data.get("reason", "")
        self.status = data.get("status", "DRAFT")
        self.created_by = data.get("created_by")
        self.submitted_by = data.get("submitted_by")
        self.approved_by = data.get("approved_by")
        self.created_at = data.get("created_at") or datetime.now(timezone.utc)
        self.updated_at = data.get("updated_at") or datetime.now(timezone.utc)
        self.approved_at = data.get("approved_at")
        self.version = data.get("version", 1)

    @property
    def revision_amount(self) -> Decimal:
        """The delta change in budget."""
        return FinancialEngine.round(self.new_budget - self.old_budget)

    def submit(self, user_id: str) -> None:
        """Transition to SUBMITTED."""
        if self.status != "DRAFT":
            raise ValueError(f"Cannot submit revision in status: {self.status}")
        self.status = "SUBMITTED"
        self.submitted_by = user_id
        self.updated_at = datetime.now(timezone.utc)

    def approve(self, user_id: str) -> None:
        """Transition to APPROVED."""
        if self.status != "SUBMITTED":
            raise ValueError(f"Only submitted revisions can be approved. Current status: {self.status}")
        self.status = "APPROVED"
        self.approved_by = user_id
        self.approved_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def reject(self, user_id: str, reason: str) -> None:
        """Transition to REJECTED."""
        if self.status != "SUBMITTED":
            raise ValueError(f"Only submitted revisions can be rejected. Current status: {self.status}")
        self.status = "REJECTED"
        self.approved_by = user_id # User who acted on it
        self.reason = f"{self.reason} | REJECTION NOTE: {reason}"
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "organisation_id": self.organisation_id,
            "project_id": self.project_id,
            "category_id": self.category_id,
            "old_budget": FinancialEngine.to_d128(self.old_budget),
            "new_budget": FinancialEngine.to_d128(self.new_budget),
            "revision_amount": FinancialEngine.to_d128(self.revision_amount),
            "reason": self.reason,
            "status": self.status,
            "created_by": self.created_by,
            "submitted_by": self.submitted_by,
            "approved_by": self.approved_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
            "version": self.version,
        }
