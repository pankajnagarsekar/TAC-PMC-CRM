"""
Payment Service Tests - Approval Workflow

Tests payment approval workflow with multi-level approvals, role-based checks,
idempotency, and audit trail. Uses real MongoDB test database.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone
from bson import ObjectId

from app.modules.financial.application.payment_service import PaymentService
from app.modules.financial.schemas.dto import PaymentCertificateCreate
from app.modules.shared.application.audit_service import AuditService
from app.modules.shared.domain.exceptions import ValidationError, NotFoundError
from app.modules.shared.domain.state_machine import StateMachine


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def supervisor_user():
    """Mock supervisor user with $10k approval limit."""
    return {
        "user_id": "supervisor-001",
        "organisation_id": "org-payment-test-123",
        "role": "Supervisor",
        "active_status": True,
    }


@pytest.fixture
def finance_manager_user():
    """Mock finance manager user with unlimited approval."""
    return {
        "user_id": "finance-mgr-001",
        "organisation_id": "org-payment-test-123",
        "role": "Finance Manager",
        "active_status": True,
    }


@pytest.fixture
def test_project_id():
    """Test project ID."""
    return str(ObjectId())


@pytest.fixture
async def test_db_with_payments(test_db):
    """Test database with payment collection initialized."""
    await test_db.payment_certificates.drop()
    await test_db.audit_logs.drop()
    await test_db.idempotency_store.drop()
    await test_db.sequences.drop()
    yield test_db


@pytest.fixture
async def audit_service(test_db_with_payments):
    """Audit service for logging."""
    return AuditService(test_db_with_payments)


@pytest.fixture
async def payment_service(test_db_with_payments, audit_service):
    """Payment service with test database."""
    from unittest.mock import AsyncMock, MagicMock
    
    mock_financial = MagicMock()
    mock_financial.validate_financial_document = AsyncMock(return_value=None)
    mock_financial.recalculate_master_budget = AsyncMock(return_value={})
    
    mock_permission = MagicMock()
    mock_permission.check_project_access = AsyncMock(return_value=None)
    mock_permission.check_write_access_with_role = AsyncMock(return_value=None)

    return PaymentService(
        test_db_with_payments,
        audit_service,
        mock_financial,
        mock_permission,
    )


@pytest.fixture
async def payment_in_draft(payment_service, supervisor_user, test_project_id):
    """Create a payment certificate in Draft status."""
    pc_data = PaymentCertificateCreate(
        project_id=test_project_id,
        vendor_id=str(ObjectId()),
        line_items=[],
        retention_percent=Decimal("5.0"),
    )
    payment = await payment_service.create_payment_certificate(supervisor_user, pc_data)
    return payment


# ============================================================================
# TEST CASES
# ============================================================================

class TestPaymentApprovalWorkflow:
    """Test payment approval workflow with multi-level approvals."""

    @pytest.mark.asyncio
    async def test_submit_for_approval(self, payment_service, supervisor_user, payment_in_draft):
        """Test 1: Submit payment for approval (Draft -> Submitted)."""
        payment_id = payment_in_draft["id"]

        result = await payment_service.submit_for_approval(supervisor_user, payment_id, expected_version=1)

        assert result["status"] == "Submitted", f"Expected Submitted, got {result['status']}"
        assert "submitted_at" in result, "submitted_at should be populated"

    @pytest.mark.asyncio
    async def test_submit_idempotency(self, payment_service, supervisor_user, payment_in_draft):
        """Test 2: Duplicate submission with same idempotency key returns same result."""
        payment_id = payment_in_draft["id"]
        idempotency_key = f"submit-{payment_id}-001"

        result1 = await payment_service.submit_for_approval(
            supervisor_user, payment_id, expected_version=1, idempotency_key=idempotency_key
        )

        # Second call - payment is already Submitted so idempotency returns cached
        result2 = await payment_service.submit_for_approval(
            supervisor_user, payment_id, expected_version=1, idempotency_key=idempotency_key
        )

        assert result1["id"] == result2["id"], "Idempotency: should return same payment"
        assert result2["status"] == "Submitted", "Status should still be Submitted"

    @pytest.mark.asyncio
    async def test_supervisor_approves_within_limit(
        self, payment_service, supervisor_user, payment_in_draft, test_db_with_payments
    ):
        """Test 3: Supervisor approves payment <= $10k."""
        payment_id = payment_in_draft["id"]

        # Update grand_total to within limit
        from bson import ObjectId as BsonObjectId
        from app.modules.shared.domain.financial_engine import FinancialEngine
        await test_db_with_payments.payment_certificates.update_one(
            {"_id": BsonObjectId(payment_id)},
            {"$set": {"grand_total": FinancialEngine.to_d128(Decimal("5000.00"))}}
        )

        await payment_service.submit_for_approval(supervisor_user, payment_id, expected_version=1)

        result = await payment_service.approve_payment(
            supervisor_user, payment_id, expected_version=2, comment="Approved within limit"
        )

        assert result["status"] == "Approved", "Status should be Approved"
        assert len(result.get("approval_trail", [])) > 0, "Approval trail should be populated"
        approval_event = result["approval_trail"][-1]
        assert approval_event["status"] == "Approved"
        assert approval_event["approver_id"] == supervisor_user["user_id"]

    @pytest.mark.asyncio
    async def test_supervisor_rejects_payment(
        self, payment_service, supervisor_user, payment_in_draft
    ):
        """Test 4: Supervisor rejects payment (Submitted -> Rejected)."""
        payment_id = payment_in_draft["id"]

        await payment_service.submit_for_approval(supervisor_user, payment_id, expected_version=1)

        result = await payment_service.reject_payment(
            supervisor_user, payment_id, expected_version=2, reason="Vendor documentation incomplete"
        )

        assert result["status"] == "Rejected", "Status should be Rejected"
        assert "rejected_at" in result, "rejected_at should be populated"
        approval_trail = result.get("approval_trail", [])
        assert len(approval_trail) > 0
        rejection_event = approval_trail[-1]
        assert rejection_event["status"] == "Rejected"
        assert rejection_event["comment"] == "Vendor documentation incomplete"

    @pytest.mark.asyncio
    async def test_supervisor_cannot_approve_over_threshold(
        self, payment_service, supervisor_user, payment_in_draft, test_db_with_payments
    ):
        """Test 5: Supervisor cannot approve payments > $10k."""
        payment_id = payment_in_draft["id"]

        from bson import ObjectId as BsonObjectId
        from app.modules.shared.domain.financial_engine import FinancialEngine
        await test_db_with_payments.payment_certificates.update_one(
            {"_id": BsonObjectId(payment_id)},
            {"$set": {"grand_total": FinancialEngine.to_d128(Decimal("15000.00"))}}
        )

        await payment_service.submit_for_approval(supervisor_user, payment_id, expected_version=1)

        with pytest.raises(ValidationError) as excinfo:
            await payment_service.approve_payment(supervisor_user, payment_id, expected_version=2)

        assert "Supervisor can only approve" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_finance_manager_approves_high_amount(
        self, payment_service, finance_manager_user, payment_in_draft, test_db_with_payments
    ):
        """Test 6: Finance Manager can approve payments > $10k."""
        payment_id = payment_in_draft["id"]

        from bson import ObjectId as BsonObjectId
        from app.modules.shared.domain.financial_engine import FinancialEngine
        await test_db_with_payments.payment_certificates.update_one(
            {"_id": BsonObjectId(payment_id)},
            {"$set": {"grand_total": FinancialEngine.to_d128(Decimal("25000.00"))}}
        )

        await payment_service.submit_for_approval(finance_manager_user, payment_id, expected_version=1)

        result = await payment_service.approve_payment(
            finance_manager_user, payment_id, expected_version=2, comment="Approved by Finance Manager"
        )

        assert result["status"] == "Approved", "Finance Manager should be able to approve > $10k"

    @pytest.mark.asyncio
    async def test_version_increments_on_update(
        self, payment_service, supervisor_user, payment_in_draft, test_db_with_payments
    ):
        """Test 7: Version field increments on each update (optimistic locking support)."""
        payment_id = payment_in_draft["id"]

        original_version = payment_in_draft.get("version", 1)

        await payment_service.submit_for_approval(supervisor_user, payment_id, expected_version=1)

        from bson import ObjectId as BsonObjectId
        from app.modules.shared.domain.financial_engine import FinancialEngine
        await test_db_with_payments.payment_certificates.update_one(
            {"_id": BsonObjectId(payment_id)},
            {"$set": {"grand_total": FinancialEngine.to_d128(Decimal("5000.00"))}}
        )

        result = await payment_service.approve_payment(supervisor_user, payment_id, expected_version=2)

        assert result.get("version", 0) > original_version, "Version should be incremented after updates"

    @pytest.mark.asyncio
    async def test_audit_trail_populated(
        self, payment_service, supervisor_user, payment_in_draft, test_db_with_payments
    ):
        """Test 8: Audit trail populated with submit and approve actions."""
        payment_id = payment_in_draft["id"]

        from bson import ObjectId as BsonObjectId
        from app.modules.shared.domain.financial_engine import FinancialEngine
        await test_db_with_payments.payment_certificates.update_one(
            {"_id": BsonObjectId(payment_id)},
            {"$set": {"grand_total": FinancialEngine.to_d128(Decimal("5000.00"))}}
        )

        await payment_service.submit_for_approval(supervisor_user, payment_id, expected_version=1)
        await payment_service.approve_payment(supervisor_user, payment_id, expected_version=2, comment="Approved")

        audit_logs = await test_db_with_payments.audit_logs.find(
            {"entity_id": payment_id}
        ).to_list(None)

        assert len(audit_logs) >= 2, "Should have at least 2 audit logs (SUBMIT, APPROVE)"

        action_types = [log.get("action_type") for log in audit_logs]
        assert "SUBMIT" in action_types, "SUBMIT action should be logged"
        assert "APPROVE" in action_types, "APPROVE action should be logged"
