"""
Budget Service Tests - Unit + Integration

Tests budget creation, allocation, forecasting, and status transitions.
Uses real MongoDB test database for integration tests.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from bson import ObjectId

from app.modules.financial.application.budget_service import BudgetService
from app.modules.financial.domain.budget import Budget, BudgetAllocation
from app.modules.financial.infrastructure.repository import BudgetRepository
from app.modules.financial.schemas.dto import BudgetCreate, BudgetUpdate, BudgetAllocationUpdate
from app.modules.shared.application.audit_service import AuditService
from app.modules.shared.domain.exceptions import ValidationError, NotFoundError
from app.modules.shared.domain.financial_engine import FinancialEngine


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_user():
    """Mock authenticated user."""
    return {
        "user_id": "user-budget-test-001",
        "organisation_id": "org-budget-test-123",
        "role": "Admin",
    }


@pytest.fixture
def test_project_id():
    """Test project ID."""
    return str(ObjectId())


@pytest.fixture
async def test_db_with_budget(test_db):
    """Test database with budget collection initialized."""
    # Ensure collections exist
    await test_db.budgets.drop()
    await test_db.audit_logs.drop()
    yield test_db


@pytest.fixture
async def audit_service(test_db_with_budget):
    """Audit service for logging."""
    return AuditService(test_db_with_budget)


@pytest.fixture
async def budget_service(test_db_with_budget, audit_service):
    """Budget service with test database."""
    return BudgetService(test_db_with_budget, audit_service)


# ============================================================================
# UNIT TESTS (Domain Logic)
# ============================================================================


class TestBudgetDomainModel:
    """Test Budget aggregate root validation and commands."""

    def test_budget_creation_valid(self):
        """Budget created with valid total and allocations."""
        budget_dict = {
            "_id": ObjectId(),
            "project_id": str(ObjectId()),
            "organisation_id": "org-123",
            "total_budget": Decimal("100000"),
            "allocations": [
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                }
            ],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        budget.validate_on_create()  # Should not raise
        assert budget.total_budget == Decimal("100000")
        assert len(budget.allocations) == 1

    def test_budget_validation_total_budget_zero(self):
        """Budget creation fails if total_budget <= 0."""
        budget_dict = {
            "_id": ObjectId(),
            "project_id": str(ObjectId()),
            "organisation_id": "org-123",
            "total_budget": Decimal("0"),
            "allocations": [],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        with pytest.raises(ValueError, match="Total budget must be greater than 0"):
            budget.validate_on_create()

    def test_budget_validation_allocations_exceed_total(self):
        """Budget creation fails if sum of allocations > total."""
        budget_dict = {
            "_id": ObjectId(),
            "project_id": str(ObjectId()),
            "organisation_id": "org-123",
            "total_budget": Decimal("100000"),
            "allocations": [
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("60000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                },
                {
                    "code": "MATERIAL",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                },
            ],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        with pytest.raises(ValueError, match="exceeds total budget"):
            budget.validate_on_create()

    def test_allocate_to_payment_success(self):
        """Allocate amount to payment reduces spent balance."""
        budget_dict = {
            "_id": ObjectId(),
            "project_id": str(ObjectId()),
            "organisation_id": "org-123",
            "total_budget": Decimal("100000"),
            "allocations": [
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                }
            ],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        budget.allocate_to_payment("LABOR", Decimal("10000"))

        labor_alloc = budget.get_allocation("LABOR")
        assert labor_alloc.spent_amount == Decimal("10000")
        assert labor_alloc.remaining == Decimal("40000")

    def test_allocate_to_payment_insufficient_balance(self):
        """Allocate to payment fails if insufficient balance."""
        budget_dict = {
            "_id": ObjectId(),
            "project_id": str(ObjectId()),
            "organisation_id": "org-123",
            "total_budget": Decimal("100000"),
            "allocations": [
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("40000"),
                    "threshold_percentage": 80,
                }
            ],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        with pytest.raises(ValueError, match="Insufficient budget"):
            budget.allocate_to_payment("LABOR", Decimal("15000"))

    def test_forecast_eac_calculation(self):
        """EAC calculated based on burn rate."""
        budget_dict = {
            "_id": ObjectId(),
            "project_id": str(ObjectId()),
            "organisation_id": "org-123",
            "total_budget": Decimal("100000"),
            "allocations": [
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("100000"),
                    "spent_amount": Decimal("25000"),
                    "threshold_percentage": 80,
                }
            ],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        forecast = budget.forecast_eac(Decimal("25"))

        # EAC = spent / percent_complete * 100 = 25000 / 0.25 = 100000
        assert forecast["eac"] == Decimal("100000")
        assert forecast["projected_overrun"] == Decimal("0")


# ============================================================================
# INTEGRATION TESTS (Service + Repository)
# ============================================================================


@pytest.mark.asyncio
class TestBudgetServiceIntegration:
    """Integration tests: Service → Repository → Database."""

    async def test_create_budget_end_to_end(
        self, budget_service, test_user, test_project_id
    ):
        """Create budget and verify persistence."""
        budget_data = BudgetCreate(
            project_id=test_project_id,
            total_budget=Decimal("100000"),
            allocations=[
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                },
                {
                    "code": "MATERIAL",
                    "budgeted_amount": Decimal("30000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 75,
                },
            ],
        )

        created = await budget_service.create_budget(test_user, test_project_id, budget_data)

        assert created["project_id"] == test_project_id
        assert created["total_budget"] == Decimal("100000")
        assert len(created["allocations"]) == 2
        assert created["status"] == "ACTIVE"
        assert created["version"] == 1

    async def test_get_budget_success(self, budget_service, test_user, test_project_id):
        """Retrieve budget by ID."""
        budget_data = BudgetCreate(
            project_id=test_project_id,
            total_budget=Decimal("50000"),
            allocations=[
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                }
            ],
        )

        created = await budget_service.create_budget(test_user, test_project_id, budget_data)
        budget_id = str(created["_id"])

        retrieved = await budget_service.get_budget(test_user, budget_id)
        assert retrieved["_id"] == created["_id"]
        assert retrieved["project_id"] == test_project_id

    async def test_allocate_to_payment_integration(
        self, budget_service, test_user, test_project_id
    ):
        """Allocate funds via service."""
        budget_data = BudgetCreate(
            project_id=test_project_id,
            total_budget=Decimal("100000"),
            allocations=[
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                }
            ],
        )

        created = await budget_service.create_budget(test_user, test_project_id, budget_data)
        budget_id = str(created["_id"])

        updated = await budget_service.allocate_to_payment(
            test_user, budget_id, "LABOR", Decimal("15000")
        )

        labor_alloc = next(a for a in updated["allocations"] if a["code"] == "LABOR")
        assert labor_alloc["spent_amount"] == Decimal("15000")
        assert labor_alloc["remaining"] == Decimal("35000")

    async def test_allocate_to_payment_insufficient_balance_integration(
        self, budget_service, test_user, test_project_id
    ):
        """Allocate fails when insufficient balance."""
        budget_data = BudgetCreate(
            project_id=test_project_id,
            total_budget=Decimal("100000"),
            allocations=[
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("50000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                }
            ],
        )

        created = await budget_service.create_budget(test_user, test_project_id, budget_data)
        budget_id = str(created["_id"])

        with pytest.raises(ValidationError, match="Insufficient budget"):
            await budget_service.allocate_to_payment(
                test_user, budget_id, "LABOR", Decimal("60000")
            )

    async def test_lock_budget_integration(self, budget_service, test_user, test_project_id):
        """Lock budget transitions ACTIVE → LOCKED."""
        budget_data = BudgetCreate(
            project_id=test_project_id,
            total_budget=Decimal("100000"),
            allocations=[],
        )

        created = await budget_service.create_budget(test_user, test_project_id, budget_data)
        budget_id = str(created["_id"])

        locked = await budget_service.lock_budget(test_user, budget_id)
        assert locked["status"] == "LOCKED"

    async def test_close_budget_integration(self, budget_service, test_user, test_project_id):
        """Close budget transitions to CLOSED."""
        budget_data = BudgetCreate(
            project_id=test_project_id,
            total_budget=Decimal("100000"),
            allocations=[],
        )

        created = await budget_service.create_budget(test_user, test_project_id, budget_data)
        budget_id = str(created["_id"])

        locked = await budget_service.lock_budget(test_user, budget_id)
        closed = await budget_service.close_budget(test_user, budget_id)
        assert closed["status"] == "CLOSED"

    async def test_list_budgets_integration(self, budget_service, test_user, test_project_id):
        """List budgets by project."""
        for i in range(3):
            budget_data = BudgetCreate(
                project_id=test_project_id,
                total_budget=Decimal("100000") * (i + 1),
                allocations=[],
            )
            await budget_service.create_budget(test_user, test_project_id, budget_data)

        result = await budget_service.list_budgets(test_user, test_project_id)
        assert result["count"] == 3
        assert len(result["items"]) == 3

    async def test_forecast_eac_integration(self, budget_service, test_user, test_project_id):
        """Forecast EAC via service."""
        budget_data = BudgetCreate(
            project_id=test_project_id,
            total_budget=Decimal("100000"),
            allocations=[
                {
                    "code": "LABOR",
                    "budgeted_amount": Decimal("100000"),
                    "spent_amount": Decimal("0"),
                    "threshold_percentage": 80,
                }
            ],
        )

        created = await budget_service.create_budget(test_user, test_project_id, budget_data)
        budget_id = str(created["_id"])

        # Allocate some funds
        await budget_service.allocate_to_payment(
            test_user, budget_id, "LABOR", Decimal("25000")
        )

        # Forecast at 25% complete
        forecast = await budget_service.forecast_eac(
            test_user, budget_id, Decimal("25")
        )

        assert forecast["eac"] == Decimal("100000")
        assert forecast["projected_overrun"] == Decimal("0")
