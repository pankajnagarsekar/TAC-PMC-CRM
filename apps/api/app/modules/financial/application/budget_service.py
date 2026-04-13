"""
Budget Service - Domain-Driven Design Application Layer

Orchestrates budget creation, updates, allocation tracking, and forecasting.
Enforces invariants via domain model and persists via repository.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional

from bson import ObjectId

from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.shared.application.audit_service import AuditService

from ..domain.budget import Budget, BudgetAllocation
from ..infrastructure.repository import BudgetRepository
from ..schemas.dto import BudgetCreate, BudgetUpdate

logger = logging.getLogger(__name__)


class BudgetService:
    """
    Sovereign Budget Orchestrator.
    Manages budget lifecycle: create, allocate, forecast, lock, close.
    """

    def __init__(self, db, audit_service: AuditService):
        self.db = db
        self.audit_service = audit_service
        self.budget_repo = BudgetRepository(db)

    async def create_budget(
        self, user: dict, project_id: str, budget_data: BudgetCreate
    ) -> Dict[str, Any]:
        """
        Create a new budget for a project.

        Args:
            user: Authenticated user dict (contains organisation_id)
            project_id: Project ID
            budget_data: BudgetCreate DTO with total_budget and allocations

        Returns:
            Created budget dict

        Raises:
            ValidationError: If budget invariants violated
        """
        organisation_id = user["organisation_id"]

        # Build domain model
        budget_dict = {
            "_id": ObjectId(),
            "project_id": project_id,
            "organisation_id": organisation_id,
            "total_budget": budget_data.total_budget,
            "allocations": [a.model_dump() for a in budget_data.allocations],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        budget.validate_on_create()  # Raises ValueError if invariants fail

        # Persist
        created = await self.budget_repo.create(budget.to_dict())
        budget_id = str(created["_id"])

        # Audit
        await self.audit_service.log_action(
            organisation_id=organisation_id,
            module_name="FINANCIAL_MANAGEMENT",
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="CREATE",
            user_id=user.get("user_id"),
            project_id=project_id,
            new_value=created,
        )

        logger.info(f"Budget created: {budget_id} for project {project_id}")
        return created

    async def get_budget(
        self, user: dict, budget_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve a budget by ID with org scoping.

        Args:
            user: Authenticated user
            budget_id: Budget ID

        Returns:
            Budget dict

        Raises:
            NotFoundError: If budget not found
        """
        organisation_id = user["organisation_id"]

        try:
            budget_dict = await self.budget_repo.get_by_id(
                budget_id, organisation_id=organisation_id
            )
        except NotFoundError:
            raise NotFoundError(f"Budget {budget_id} not found")

        return budget_dict

    async def update_allocations(
        self, user: dict, budget_id: str, allocation_data: BudgetUpdate
    ) -> Dict[str, Any]:
        """
        Update budget allocations.

        Args:
            user: Authenticated user
            budget_id: Budget ID
            allocation_data: BudgetUpdate DTO with new allocations

        Returns:
            Updated budget dict

        Raises:
            NotFoundError: If budget not found
            ValidationError: If allocations invalid
        """
        organisation_id = user["organisation_id"]

        # Fetch current budget
        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        old_budget = Budget(budget_dict)

        # Apply changes via domain
        new_allocs = [a.model_dump() for a in allocation_data.allocations]
        old_budget.update_allocations(new_allocs)

        # Persist with version check
        updated = await self.budget_repo.update(
            budget_id, old_budget.to_dict(), organisation_id=organisation_id
        )

        # Audit
        await self.audit_service.log_action(
            organisation_id=organisation_id,
            module_name="FINANCIAL_MANAGEMENT",
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="UPDATE",
            user_id=user.get("user_id"),
            project_id=old_budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(f"Budget allocations updated: {budget_id}")
        return updated

    async def allocate_to_payment(
        self, user: dict, budget_id: str, code: str, amount: Decimal
    ) -> Dict[str, Any]:
        """
        Allocate budget amount for a payment under a specific code.

        Decrements available budget; used when creating/approving payments.

        Args:
            user: Authenticated user
            budget_id: Budget ID
            code: Financial code (LABOR, MATERIAL, etc.)
            amount: Amount to allocate (Decimal)

        Returns:
            Updated budget dict with new allocation state

        Raises:
            NotFoundError: If budget or code not found
            ValidationError: If insufficient balance
        """
        organisation_id = user["organisation_id"]
        amount = FinancialEngine.round(Decimal(str(amount)))

        # Fetch current budget
        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        # Allocate via domain (raises ValueError if insufficient)
        try:
            budget.allocate_to_payment(code, amount)
        except ValueError as e:
            raise ValidationError(str(e))

        # Persist
        updated = await self.budget_repo.update(
            budget_id, budget.to_dict(), organisation_id=organisation_id
        )

        # Audit
        await self.audit_service.log_action(
            organisation_id=organisation_id,
            module_name="FINANCIAL_MANAGEMENT",
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="UPDATE",
            user_id=user.get("user_id"),
            project_id=budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(
            f"Budget allocation: ${amount} for code {code} in budget {budget_id}"
        )
        return updated

    async def forecast_eac(
        self, user: dict, budget_id: str, percent_complete: Decimal = Decimal("50")
    ) -> Dict[str, Any]:
        """
        Calculate Estimate at Completion (EAC) based on current burn rate.

        Args:
            user: Authenticated user
            budget_id: Budget ID
            percent_complete: Project completion percentage (0-100)

        Returns:
            Dict with eac, projected_overrun, variance_at_completion

        Raises:
            NotFoundError: If budget not found
            ValidationError: If percent_complete invalid
        """
        organisation_id = user["organisation_id"]
        percent_complete = Decimal(str(percent_complete))

        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        try:
            forecast = budget.forecast_eac(percent_complete)
        except ValueError as e:
            raise ValidationError(str(e))

        return forecast

    async def lock_budget(self, user: dict, budget_id: str) -> Dict[str, Any]:
        """
        Lock budget to prevent allocation changes (transitions ACTIVE → LOCKED).

        Args:
            user: Authenticated user
            budget_id: Budget ID

        Returns:
            Updated budget dict

        Raises:
            NotFoundError: If budget not found
            ValidationError: If transition invalid
        """
        organisation_id = user["organisation_id"]

        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        try:
            budget.lock_budget()
        except ValueError as e:
            raise ValidationError(str(e))

        updated = await self.budget_repo.update(
            budget_id, budget.to_dict(), organisation_id=organisation_id
        )

        await self.audit_service.log_action(
            organisation_id=organisation_id,
            module_name="FINANCIAL_MANAGEMENT",
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="TRANSITION",
            user_id=user.get("user_id"),
            project_id=budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(f"Budget locked: {budget_id}")
        return updated

    async def close_budget(self, user: dict, budget_id: str) -> Dict[str, Any]:
        """
        Close budget (final state: LOCKED/ACTIVE → CLOSED).

        Args:
            user: Authenticated user
            budget_id: Budget ID

        Returns:
            Updated budget dict

        Raises:
            NotFoundError: If budget not found
            ValidationError: If transition invalid
        """
        organisation_id = user["organisation_id"]

        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        try:
            budget.close_budget()
        except ValueError as e:
            raise ValidationError(str(e))

        updated = await self.budget_repo.update(
            budget_id, budget.to_dict(), organisation_id=organisation_id
        )

        await self.audit_service.log_action(
            organisation_id=organisation_id,
            module_name="FINANCIAL_MANAGEMENT",
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="TRANSITION",
            user_id=user.get("user_id"),
            project_id=budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(f"Budget closed: {budget_id}")
        return updated

    async def list_budgets(
        self, user: dict, project_id: str, limit: int = 100
    ) -> Dict[str, Any]:
        """
        List all budgets for a project.

        Args:
            user: Authenticated user
            project_id: Project ID
            limit: Max results

        Returns:
            Dict with items (list of budgets)
        """
        organisation_id = user["organisation_id"]
        budgets = await self.budget_repo.list_by_project(
            project_id, organisation_id, limit
        )
        return {"items": budgets, "count": len(budgets)}
