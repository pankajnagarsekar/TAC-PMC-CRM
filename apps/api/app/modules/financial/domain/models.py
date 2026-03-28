from decimal import Decimal
from typing import Dict, Any, Optional
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
        return FinancialEngine.round(self.original_budget - self.committed_value)

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
            "over_commit_flag": self.is_over_committed
        }
