import pytest
from unittest.mock import AsyncMock, MagicMock
from app.modules.contracting.application.work_order_service import WorkOrderService
from app.modules.contracting.schemas.dto import WorkOrderCreate, WorkOrderUpdate, WOLineItem
from app.modules.shared.domain.exceptions import ValidationError, NotFoundError, DomainError
from decimal import Decimal
from bson import ObjectId
from datetime import datetime, timezone

@pytest.fixture
def mock_audit_service():
    return AsyncMock()

@pytest.fixture
def mock_permission_checker():
    checker = AsyncMock()
    checker.check_project_access.return_value = None
    checker.check_write_access_with_role.return_value = None
    return checker

@pytest.fixture
def mock_financial_service():
    service = AsyncMock()
    service.validate_financial_document.return_value = True
    service.recalculate_master_budget.return_value = None
    return service

@pytest.fixture
def work_order_service(test_db, mock_audit_service, mock_financial_service, mock_permission_checker):
    return WorkOrderService(test_db, mock_audit_service, mock_financial_service, mock_permission_checker)

@pytest.mark.asyncio
async def test_create_work_order_flow(work_order_service, test_db, test_user, test_project_id):
    # Setup dependencies
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    
    await test_db.project_category_budgets.insert_one({
        "project_id": test_project_id,
        "category_id": "CAT1",
        "organisation_id": test_user["organisation_id"],
        "remaining_budget": 10000.0,
        "committed_amount": 0.0
    })

    data = WorkOrderCreate(
        project_id=test_project_id,
        category_id="CAT1",
        vendor_id=vendor_id,
        line_items=[WOLineItem(sr_no=1, description="Test", qty=1, rate=1000)]
    )

    wo = await work_order_service.create_work_order(test_user, test_project_id, data)
    assert wo["wo_ref"].startswith("WO-")
    assert wo["status"] == "Draft"
    
    # Verify Ledger Entry
    ledger = await test_db.vendor_ledger.find_one({"ref_id": str(wo["id"])})
    assert ledger["entry_type"] == "COMMITTED"
    assert float(str(ledger["amount"])) > 0

@pytest.mark.asyncio
async def test_work_order_approval_lifecycle(work_order_service, test_db, test_user, test_project_id):
    # Setup WO in Draft
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    await test_db.project_category_budgets.insert_one({"project_id":test_project_id, "category_id":"C1", "remaining_budget":5000, "committed_amount":0})
    wo = await work_order_service.create_work_order(test_user, test_project_id, WorkOrderCreate(
        project_id=test_project_id, category_id="C1", vendor_id=vendor_id,
        line_items=[WOLineItem(sr_no=1, qty=1, rate=100)]
    ))

    # 1. Submit
    submitted = await work_order_service.submit_work_order(test_user, str(wo["id"]), expected_version=1)
    assert submitted["status"] == "Pending"

    # 2. Approve
    approved = await work_order_service.approve_work_order(test_user, str(wo["id"]), expected_version=2)
    assert approved["status"] == "Approved"

@pytest.mark.asyncio
async def test_cancel_work_order(work_order_service, test_db, test_user, test_project_id):
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    await test_db.project_category_budgets.insert_one({"project_id":test_project_id, "category_id":"C1", "remaining_budget":5000, "committed_amount":0})
    wo = await work_order_service.create_work_order(test_user, test_project_id, WorkOrderCreate(
        project_id=test_project_id, category_id="C1", vendor_id=vendor_id,
        line_items=[WOLineItem(sr_no=1, qty=1, rate=100)]
    ))

    cancelled = await work_order_service.cancel_work_order(test_user, str(wo["id"]), expected_version=1)
    assert cancelled["status"] == "Cancelled"

@pytest.mark.asyncio
async def test_update_work_order_occ(work_order_service, test_db, test_user, test_project_id):
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    await test_db.project_category_budgets.insert_one({"project_id":test_project_id, "category_id":"C1", "remaining_budget":5000, "committed_amount":0})
    wo = await work_order_service.create_work_order(test_user, test_project_id, WorkOrderCreate(
        project_id=test_project_id, category_id="C1", vendor_id=vendor_id,
        line_items=[WOLineItem(sr_no=1, qty=1, rate=100)]
    ))

    # Update with correct version
    update_data = WorkOrderUpdate(expected_version=1, line_items=[WOLineItem(sr_no=1, qty=2, rate=100)])
    updated = await work_order_service.update_work_order(test_user, str(wo["id"]), update_data)
    assert updated["version"] == 2

    # Update with stale version -> should fail
    with pytest.raises(ValidationError, match="CONFLICT"):
        await work_order_service.update_work_order(test_user, str(wo["id"]), update_data)

@pytest.mark.asyncio
async def test_work_order_invariant_violation(work_order_service, test_db, test_user, test_project_id):
    # Cannot reduce WO below certified payments
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    await test_db.project_category_budgets.insert_one({"project_id":test_project_id, "category_id":"C1", "remaining_budget":5000, "committed_amount":0})
    wo = await work_order_service.create_work_order(test_user, test_project_id, WorkOrderCreate(
        project_id=test_project_id, category_id="C1", vendor_id=vendor_id,
        line_items=[WOLineItem(sr_no=1, qty=10, rate=100)] # 1000
    ))

    # Add a mock PC for 500
    await test_db.payment_certificates.insert_one({
        "work_order_id": str(wo["id"]),
        "grand_total": 500.0,
        "status": "Certified",
        "organisation_id": test_user["organisation_id"]
    })

    # Try to reduce WO to 400 -> should fail
    update_data = WorkOrderUpdate(expected_version=1, line_items=[WOLineItem(sr_no=1, qty=4, rate=100)])
    with pytest.raises(DomainError, match="Cannot reduce Work Order below linked Payment Certificate total"):
        await work_order_service.update_work_order(test_user, str(wo["id"]), update_data)

@pytest.mark.asyncio
async def test_list_work_orders(work_order_service, test_user, test_project_id, test_db):
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    await test_db.project_category_budgets.insert_one({"project_id":test_project_id, "category_id":"C1", "remaining_budget":5000})
    await work_order_service.create_work_order(test_user, test_project_id, WorkOrderCreate(
        project_id=test_project_id, category_id="C1", vendor_id=vendor_id,
        line_items=[WOLineItem(sr_no=1, qty=1, rate=100)]
    ))
    
    result = await work_order_service.list_work_orders(test_user, test_project_id, limit=10, cursor=None)
    assert len(result["items"]) == 1

@pytest.mark.asyncio
async def test_create_work_order_invalid_vendor(work_order_service, test_user, test_project_id, test_db):
    await test_db.project_category_budgets.insert_one({"project_id":test_project_id, "category_id":"C1", "remaining_budget":5000})
    
    with pytest.raises(ValidationError, match="Vendor not found"):
        await work_order_service.create_work_order(test_user, test_project_id, WorkOrderCreate(
            project_id=test_project_id, category_id="C1", vendor_id=str(ObjectId()),
            line_items=[WOLineItem(sr_no=1, qty=1, rate=100)]
        ))

@pytest.mark.asyncio
async def test_create_work_order_invalid_budget(work_order_service, test_user, test_db):
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    
    with pytest.raises(ValidationError, match="Category budget not initialized"):
        await work_order_service.create_work_order(test_user, "P_MISSING", WorkOrderCreate(
            project_id="P_MISSING", category_id="CAT_NONE", vendor_id=vendor_id,
            line_items=[WOLineItem(sr_no=1, qty=1, rate=100)]
        ))

@pytest.mark.asyncio
async def test_approve_non_pending_wo(work_order_service, test_db, test_user, test_project_id):
    vendor_id = str(ObjectId())
    await test_db.vendors.insert_one({"_id": ObjectId(vendor_id), "organisation_id": test_user["organisation_id"], "name": "V1"})
    await test_db.project_category_budgets.insert_one({"project_id":test_project_id, "category_id":"C1", "remaining_budget":5000})
    wo = await work_order_service.create_work_order(test_user, test_project_id, WorkOrderCreate(
        project_id=test_project_id, category_id="C1", vendor_id=vendor_id,
        line_items=[WOLineItem(sr_no=1, qty=1, rate=100)]
    ))
    
    # Status is Draft, trying to approve directly
    with pytest.raises(DomainError, match="Only Pending Work Orders can be approved"):
        await work_order_service.approve_work_order(test_user, str(wo["id"]), expected_version=1)

