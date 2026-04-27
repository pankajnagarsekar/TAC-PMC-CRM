import pytest
from unittest.mock import AsyncMock
from app.modules.contracting.application.contract_service import ContractService
from app.modules.contracting.schemas.dto import ContractCreate, ContractUpdate
from app.modules.shared.domain.exceptions import ValidationError
from decimal import Decimal
from bson import ObjectId
from datetime import datetime, timezone


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def mock_permission_checker():
    return AsyncMock()


@pytest.fixture
def contract_service(test_db, mock_audit_service, mock_permission_checker):
    return ContractService(test_db, mock_audit_service, mock_permission_checker)


@pytest.mark.asyncio
async def test_create_contract_success(contract_service, test_db, test_user):
    # Setup Approved WO
    wo_id = str(ObjectId())
    vendor_id = str(ObjectId())
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "status": "Approved",
        "project_id": "P1",
        "vendor_id": vendor_id
    })

    data = ContractCreate(
        work_order_id=wo_id,
        vendor_id=vendor_id,
        contract_value=Decimal("50000.0"),
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        terms="Test Terms"
    )

    contract = await contract_service.create_contract(test_user, wo_id, data)
    assert contract["work_order_id"] == wo_id
    assert contract["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_create_contract_blocked_by_draft_wo(contract_service, test_db, test_user):
    wo_id = str(ObjectId())
    await test_db.work_orders.insert_one({
        "_id": ObjectId(wo_id),
        "organisation_id": test_user["organisation_id"],
        "status": "Draft"
    })

    data = ContractCreate(
        work_order_id=wo_id,
        vendor_id=str(ObjectId()),
        contract_value=Decimal("100"),
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        terms="..."
    )

    with pytest.raises(ValidationError, match="Work Order must be Approved"):
        await contract_service.create_contract(test_user, wo_id, data)


@pytest.mark.asyncio
async def test_get_contract_by_wo(contract_service, test_db, test_user):
    wo_id = str(ObjectId())
    await test_db.contracts.insert_one({
        "work_order_id": wo_id,
        "organisation_id": test_user["organisation_id"],
        "terms": "Existing Contract"
    })

    contract = await contract_service.get_contract_by_wo(test_user, wo_id)
    assert contract["terms"] == "Existing Contract"


@pytest.mark.asyncio
async def test_update_contract(contract_service, test_db, test_user):
    c_id = str(ObjectId())
    await test_db.contracts.insert_one({
        "_id": ObjectId(c_id),
        "organisation_id": test_user["organisation_id"],
        "status": "DRAFT",
        "version": 1
    })

    updated = await contract_service.update_contract(
        test_user, c_id,
        ContractUpdate(status="ACTIVE", expected_version=1)
    )
    assert updated["status"] == "ACTIVE"
