import pytest
from decimal import Decimal
from datetime import datetime, timezone
from bson import ObjectId, Decimal128
from fastapi import HTTPException

from app.modules.financial.application.budget_service import BudgetService
from app.modules.financial.application.financial_service import FinancialService
from app.modules.financial.schemas.dto import BudgetRevisionCreate, BudgetRevisionAction
from app.modules.shared.domain.exceptions import ValidationError

@pytest.fixture
def admin_user():
    """Admin user mock."""
    return {
        "user_id": "user-admin-01",
        "organisation_id": "org-test-123",
        "role": "Admin",
    }

@pytest.fixture
def non_admin_user():
    """Non-admin user mock."""
    return {
        "user_id": "user-client-01",
        "organisation_id": "org-test-123",
        "role": "Client",
    }

@pytest.fixture
def test_project_id():
    """Test project ID."""
    return str(ObjectId())

@pytest.fixture
def test_category_id():
    """Test category ID."""
    return str(ObjectId())

@pytest.fixture
async def audit_service(test_db):
    from app.modules.shared.application.audit_service import AuditService
    return AuditService(test_db)

@pytest.fixture
async def budget_service(test_db, audit_service):
    return BudgetService(test_db, audit_service)

@pytest.fixture
async def financial_service(test_db, audit_service):
    return FinancialService(test_db, audit_service)

@pytest.mark.asyncio
class TestBudgetRevisionsWorkflow:
    """Test budget revisions (Variation Order) workflows, gating, and triggers."""

    async def test_revisions_access_control(
        self, budget_service, admin_user, non_admin_user, test_project_id, test_category_id, test_db
    ):
        """Verify non-admin is blocked from approving or rejecting, but admin succeeds."""
        # 1. Setup category budget
        await test_db.project_category_budgets.insert_one({
            "project_id": test_project_id,
            "organisation_id": "org-test-123",
            "category_id": test_category_id,
            "original_budget": Decimal128("5000000.00"),
            "committed_amount": Decimal128("0.0"),
            "remaining_budget": Decimal128("5000000.00"),
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })

        # 2. Create budget revision draft
        revision_data = BudgetRevisionCreate(
            project_id=test_project_id,
            category_id=test_category_id,
            new_budget=Decimal("6000000.00"),
            reason="Increase due to extra scope",
            document_url="https://docs.tacpmc.com/vo-001.pdf",
            document_name="vo-001.pdf"
        )
        
        # Any authenticated user can create revision drafts
        created = await budget_service.create_revision(non_admin_user, revision_data)
        revision_id = str(created["_id"])
        
        # Submit the revision first
        await budget_service.submit_revision(non_admin_user, revision_id)
        
        # 3. Non-admin attempts to approve -> Rejected with 403 HTTP Exception
        with pytest.raises(HTTPException) as exc_info:
            await budget_service.approve_revision(non_admin_user, revision_id)
        assert exc_info.value.status_code == 403
        assert "Administrative role required" in exc_info.value.detail

        # 4. Non-admin attempts to reject -> Rejected with 403 HTTP Exception
        reject_action = BudgetRevisionAction(expected_version=1, comment="Invalid budget")
        with pytest.raises(HTTPException) as exc_info:
            await budget_service.reject_revision(non_admin_user, revision_id, reject_action)
        assert exc_info.value.status_code == 403
        assert "Administrative role required" in exc_info.value.detail

        # 5. Admin rejects successfully
        rejected = await budget_service.reject_revision(admin_user, revision_id, reject_action)
        assert rejected["status"] == "REJECTED"
        assert "REJECTION NOTE: Invalid budget" in rejected["reason"]

        # 6. Create another revision draft (we leave it as DRAFT to verify draft auto-submit on approval)
        created2 = await budget_service.create_revision(non_admin_user, revision_data)
        revision_id2 = str(created2["_id"])

        # 7. Admin approves successfully, updates budget, and triggers master recalculation
        approved = await budget_service.approve_revision(admin_user, revision_id2)
        assert approved["status"] == "APPROVED"

        # Verify category budget updated
        updated_budget = await test_db.project_category_budgets.find_one({"project_id": test_project_id, "category_id": test_category_id})
        assert updated_budget["original_budget"].to_decimal() == Decimal("6000000.00")

        # Verify master state updated in financial_state collection via master recalculation trigger
        master_state = await test_db.financial_state.find_one({"project_id": test_project_id, "category_id": "MASTER"})
        assert master_state is not None
        assert master_state["original_budget"].to_decimal() == Decimal("6000000.00")
