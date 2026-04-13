"""
Budget Aggregate Root - Domain-Driven Design

Manages budget allocation across financial codes (LABOR, MATERIAL, EQUIPMENT, OVERHEAD, CONTINGENCY).
Enforces invariants: total budget must equal or exceed sum of allocations.
Supports forecasting, allocation, and variance tracking.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.modules.shared.domain.financial_engine import FinancialEngine


class BudgetAllocation:
    """Value object representing a budget allocation for a single financial code."""

    def __init__(
        self,
        code: str,
        budgeted_amount: Decimal,
        spent_amount: Decimal = Decimal("0"),
        threshold_percentage: int = 80,
    ):
        self.code = code
        self.budgeted_amount = FinancialEngine.round(budgeted_amount)
        self.spent_amount = FinancialEngine.round(spent_amount)
        self.threshold_percentage = threshold_percentage

    @property
    def variance(self) -> Decimal:
        """Variance = budgeted - spent (positive = under budget, negative = over budget)."""
        return FinancialEngine.round(self.budgeted_amount - self.spent_amount)

    @property
    def percent_spent(self) -> Decimal:
        """Percentage of budget spent."""
        if self.budgeted_amount == 0:
            return Decimal("0")
        pct = (self.spent_amount / self.budgeted_amount) * 100
        return FinancialEngine.round(pct)

    @property
    def is_threshold_breached(self) -> bool:
        """Check if spent percentage exceeds threshold."""
        return self.percent_spent >= self.threshold_percentage

    @property
    def remaining(self) -> Decimal:
        """Remaining budget for this allocation."""
        return FinancialEngine.round(self.budgeted_amount - self.spent_amount)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "budgeted_amount": self.budgeted_amount,
            "spent_amount": self.spent_amount,
            "variance": self.variance,
            "percent_spent": self.percent_spent,
            "threshold_percentage": self.threshold_percentage,
            "is_threshold_breached": self.is_threshold_breached,
            "remaining": self.remaining,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BudgetAllocation":
        """Reconstruct from dict (e.g., from MongoDB)."""
        return BudgetAllocation(
            code=data["code"],
            budgeted_amount=Decimal(str(data.get("budgeted_amount", 0))),
            spent_amount=Decimal(str(data.get("spent_amount", 0))),
            threshold_percentage=data.get("threshold_percentage", 80),
        )


class Budget:
    """
    Budget Aggregate Root.

    Manages budget allocation across multiple financial codes.
    Enforces invariants:
    - total_budget > 0
    - sum(allocations) <= total_budget
    - spent_amount <= budgeted_amount (per allocation)

    Status lifecycle: ACTIVE → LOCKED → CLOSED
    """

    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("_id") or data.get("id")
        self.project_id = data.get("project_id")
        self.organisation_id = data.get("organisation_id")
        self.total_budget = FinancialEngine.round(
            Decimal(str(data.get("total_budget") or 0))
        )
        self.allocations = [
            BudgetAllocation.from_dict(a) if isinstance(a, dict) else a
            for a in data.get("allocations", [])
        ]
        self.status = data.get("status", "ACTIVE")  # ACTIVE, LOCKED, CLOSED
        self.version = data.get("version", 1)
        self.created_at = data.get("created_at", datetime.now(timezone.utc))
        self.updated_at = data.get("updated_at", datetime.now(timezone.utc))

    # Invariants

    def validate_on_create(self) -> None:
        """Validate budget before creation."""
        if self.total_budget <= 0:
            raise ValueError("Total budget must be greater than 0")

        total_allocated = self._sum_allocations()
        if total_allocated > self.total_budget:
            raise ValueError(
                f"Sum of allocations (${total_allocated}) exceeds total budget (${self.total_budget})"
            )

    def validate_allocation_update(self, new_allocations: List[BudgetAllocation]) -> None:
        """Validate allocation update."""
        total_allocated = sum(
            a.budgeted_amount for a in new_allocations
        )  # FinancialEngine.round() not needed for sum check
        if total_allocated > self.total_budget:
            raise ValueError(
                f"Sum of allocations (${total_allocated}) exceeds total budget (${self.total_budget})"
            )

        if self.status == "LOCKED":
            raise ValueError("Cannot update allocations for a locked budget")

    # Commands

    def allocate_to_payment(self, code: str, amount: Decimal) -> None:
        """
        Allocate amount from budget for payment. Enforces constraints.

        Raises:
            ValueError: If code not found, or insufficient balance.
        """
        allocation = self._find_allocation(code)
        if not allocation:
            raise ValueError(f"Allocation for code '{code}' not found")

        amount = FinancialEngine.round(amount)
        if allocation.spent_amount + amount > allocation.budgeted_amount:
            raise ValueError(
                f"Insufficient budget for code '{code}'. Remaining: ${allocation.remaining}, Requested: ${amount}"
            )

        # Update spent amount (in-memory, persisted by repository.update)
        allocation.spent_amount = FinancialEngine.round(
            allocation.spent_amount + amount
        )

    def update_allocations(self, new_allocations: List[Dict[str, Any]]) -> None:
        """
        Update allocations. Converts dicts to BudgetAllocation objects.

        Raises:
            ValueError: If budget is locked or allocations invalid.
        """
        new_alloc_objs = [BudgetAllocation.from_dict(a) for a in new_allocations]
        self.validate_allocation_update(new_alloc_objs)
        self.allocations = new_alloc_objs
        self.updated_at = datetime.now(timezone.utc)

    def lock_budget(self) -> None:
        """Lock budget to prevent allocation changes."""
        if self.status == "LOCKED":
            raise ValueError("Budget is already locked")
        self.status = "LOCKED"
        self.updated_at = datetime.now(timezone.utc)

    def close_budget(self) -> None:
        """Close budget (final state)."""
        if self.status == "CLOSED":
            raise ValueError("Budget is already closed")
        self.status = "CLOSED"
        self.updated_at = datetime.now(timezone.utc)

    # Queries

    def get_allocation(self, code: str) -> Optional[BudgetAllocation]:
        """Get allocation by code."""
        return self._find_allocation(code)

    def get_total_spent(self) -> Decimal:
        """Calculate total spent across all allocations."""
        return FinancialEngine.round(sum(a.spent_amount for a in self.allocations))

    def get_total_budgeted(self) -> Decimal:
        """Calculate total budgeted across all allocations."""
        return FinancialEngine.round(
            sum(a.budgeted_amount for a in self.allocations)
        )

    def get_total_variance(self) -> Decimal:
        """Calculate total variance (total_budget - total_spent)."""
        return FinancialEngine.round(
            self.total_budget - self.get_total_spent()
        )

    def get_breached_allocations(self) -> List[BudgetAllocation]:
        """Return allocations that have breached their threshold."""
        return [a for a in self.allocations if a.is_threshold_breached]

    def forecast_eac(self, percent_complete: Decimal = Decimal("50")) -> Dict[str, Any]:
        """
        Estimate at Completion (EAC) based on current burn rate.

        Formula: EAC = (total_spent / percent_complete) * 100

        Args:
            percent_complete: Project completion percentage (0-100)

        Returns:
            Dict with EAC, projected_overrun, variance_at_completion
        """
        if percent_complete <= 0 or percent_complete > 100:
            raise ValueError("percent_complete must be between 0 and 100")

        total_spent = self.get_total_spent()

        # Avoid division by zero
        if percent_complete == 0:
            return {
                "eac": self.total_budget,
                "projected_overrun": Decimal("0"),
                "variance_at_completion": self.total_budget - total_spent,
            }

        percent_decimal = percent_complete / 100
        eac = FinancialEngine.round(total_spent / percent_decimal)
        projected_overrun = FinancialEngine.round(eac - self.total_budget)
        variance_at_completion = FinancialEngine.round(
            self.total_budget - total_spent
        )

        return {
            "eac": eac,
            "projected_overrun": projected_overrun,
            "variance_at_completion": variance_at_completion,
        }

    # Serialization

    def to_dict(self) -> Dict[str, Any]:
        """Serialize budget to dict for storage/API response."""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "organisation_id": self.organisation_id,
            "total_budget": self.total_budget,
            "allocations": [a.to_dict() for a in self.allocations],
            "total_spent": self.get_total_spent(),
            "total_budgeted": self.get_total_budgeted(),
            "variance": self.get_total_variance(),
            "status": self.status,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    # Private helpers

    def _find_allocation(self, code: str) -> Optional[BudgetAllocation]:
        """Find allocation by code."""
        for a in self.allocations:
            if a.code == code:
                return a
        return None

    def _sum_allocations(self) -> Decimal:
        """Sum all allocation amounts."""
        return FinancialEngine.round(
            sum(a.budgeted_amount for a in self.allocations)
        )
