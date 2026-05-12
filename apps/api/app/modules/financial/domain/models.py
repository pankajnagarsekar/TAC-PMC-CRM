from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from app.modules.shared.domain.financial_engine import FinancialEngine


class FinancialState:
    """
    Aggregate representing the financial health of a project/category.
    Encapsulates budget, commitments, and certified values.
    """

    def __init__(self, data: Dict[str, Any]):
        self.project_id = data.get("project_id")
        self.category_id = data.get("category_id")
        self.original_budget = Decimal(str(data.get("original_budget") or 0))
        self.committed_value = Decimal(str(data.get("committed_value") or 0))
        self.certified_value = Decimal(str(data.get("certified_value") or 0))
        self.logic_version = data.get("logic_version")

    @property
    def balance_remaining(self) -> Decimal:
        """
        Spec-compliant remaining budget calculation.
        Remaining = Budget - max(Committed, Certified)
        """
        return FinancialEngine.round(
            self.original_budget - max(self.committed_value, self.certified_value)
        )

    @property
    def is_over_committed(self) -> bool:
        return self.committed_value > self.original_budget

    def is_threshold_breached(self, cash_in_hand: Decimal, threshold: Decimal) -> bool:
        """Domain invariant for fund transfer categories."""
        return cash_in_hand <= threshold

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "category_id": self.category_id,
            "original_budget": self.original_budget,
            "committed_value": self.committed_value,
            "certified_value": self.certified_value,
            "balance_budget_remaining": self.balance_remaining,
            "over_commit_flag": self.is_over_committed,
        }


class ApprovalEvent:
    """Value object: immutable approval event for payment workflow."""

    def __init__(
        self,
        action: str,
        user_id: str,
        user_role: str,
        timestamp: datetime,
        comment: str,
        payment_state_before: str,
        payment_state_after: str,
    ):
        self.action = action
        self.user_id = user_id
        self.user_role = user_role
        self.timestamp = timestamp
        self.comment = comment
        self.payment_state_before = payment_state_before
        self.payment_state_after = payment_state_after

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "user_id": self.user_id,
            "user_role": self.user_role,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "comment": self.comment,
            "payment_state_before": self.payment_state_before,
            "payment_state_after": self.payment_state_after,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalEvent":
        return cls(
            action=data["action"],
            user_id=data["user_id"],
            user_role=data["user_role"],
            timestamp=(
                data["timestamp"] if isinstance(data["timestamp"], datetime)
                else datetime.fromisoformat(data["timestamp"])
            ),
            comment=data["comment"],
            payment_state_before=data["payment_state_before"],
            payment_state_after=data["payment_state_after"],
        )
