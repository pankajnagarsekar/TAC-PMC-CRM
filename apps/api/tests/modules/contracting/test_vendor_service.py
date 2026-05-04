import pytest
from unittest.mock import AsyncMock
from app.modules.contracting.application.vendor_service import VendorService
from app.modules.contracting.schemas.dto import VendorCreate, VendorUpdate
from app.modules.shared.domain.exceptions import ValidationError, NotFoundError
from bson import ObjectId


@pytest.fixture
def mock_audit_service():
    return AsyncMock()


@pytest.fixture
def mock_permission_checker():
    checker = AsyncMock()
    # By default, allow everything
    checker.check_admin_role.return_value = None
    return checker


@pytest.fixture
def vendor_service(test_db, mock_audit_service, mock_permission_checker):
    return VendorService(test_db, mock_audit_service, mock_permission_checker)


@pytest.mark.asyncio
async def test_create_vendor_success(vendor_service, test_user, mock_audit_service):
    data = VendorCreate(
        name="Modern Concrete Ltd",
        gstin="27AAACM1234F1Z1",
        contact_person="John Doe",
        phone="1234567890",
        email="john@example.com"
    )
    vendor = await vendor_service.create_vendor(test_user, data)

    assert vendor["name"] == "Modern Concrete Ltd"
    assert vendor["organisation_id"] == test_user["organisation_id"]
    assert vendor["active_status"] is True
    mock_audit_service.log_action.assert_called_once()


@pytest.mark.asyncio
async def test_create_vendor_duplicate_name(vendor_service, test_user):
    data = VendorCreate(
        name="Duplicate Corp",
        contact_person="John Doe",
        phone="1234567890",
        email="john@example.com"
    )
    await vendor_service.create_vendor(test_user, data)

    with pytest.raises(ValidationError, match="VENDOR_ALREADY_EXISTS"):
        await vendor_service.create_vendor(test_user, data)


@pytest.mark.asyncio
async def test_get_vendor_success(vendor_service, test_user):
    data = VendorCreate(
        name="Single Vendor",
        contact_person="John Doe",
        phone="1234567890",
        email="john@example.com"
    )
    created = await vendor_service.create_vendor(test_user, data)

    fetched = await vendor_service.get_vendor(test_user, str(created["id"]))
    assert fetched["name"] == "Single Vendor"


@pytest.mark.asyncio
async def test_get_vendor_not_found(vendor_service, test_user):
    with pytest.raises(NotFoundError):
        await vendor_service.get_vendor(test_user, str(ObjectId()))


@pytest.mark.asyncio
async def test_update_vendor_success(vendor_service, test_user, mock_audit_service):
    created = await vendor_service.create_vendor(
        test_user,
        VendorCreate(
            name="Old Name",
            contact_person="John Doe",
            phone="1234567890",
            email="john@example.com"
        )
    )

    update_data = VendorUpdate(name="New Awesome Name", email="contact@awesome.com", expected_version=1)
    updated = await vendor_service.update_vendor(test_user, str(created["id"]), update_data)

    assert updated["name"] == "New Awesome Name"
    assert updated["email"] == "contact@awesome.com"


@pytest.mark.asyncio
async def test_soft_delete_vendor(vendor_service, test_user, mock_audit_service):
    created = await vendor_service.create_vendor(
        test_user,
        VendorCreate(
            name="To Delete",
            contact_person="John Doe",
            phone="1234567890",
            email="john@example.com"
        )
    )

    await vendor_service.delete_vendor(test_user, str(created["id"]))

    fetched = await vendor_service.get_vendor(test_user, str(created["id"]))
    assert fetched["active_status"] is False


@pytest.mark.asyncio
async def test_delete_vendor_blocked_by_wo(vendor_service, test_user, test_db):
    vendor = await vendor_service.create_vendor(
        test_user,
        VendorCreate(
            name="Busy Vendor",
            contact_person="John Doe",
            phone="1234567890",
            email="john@example.com"
        )
    )

    # Manually insert a work order for this vendor
    await test_db.work_orders.insert_one({
        "vendor_id": str(vendor["id"]),
        "organisation_id": test_user["organisation_id"],
        "status": "Draft"
    })

    with pytest.raises(ValidationError, match="DELETION_BLOCKED"):
        await vendor_service.delete_vendor(test_user, str(vendor["id"]))


@pytest.mark.asyncio
async def test_list_vendors_filter(vendor_service, test_user):
    await vendor_service.create_vendor(
        test_user,
        VendorCreate(
            name="Active 1",
            contact_person="John Doe",
            phone="1234567890",
            email="john@example.com"
        )
    )
    v2 = await vendor_service.create_vendor(
        test_user,
        VendorCreate(
            name="Inactive soon",
            contact_person="John Doe",
            phone="1234567890",
            email="john@example.com"
        )
    )
    await vendor_service.delete_vendor(test_user, str(v2["id"]))

    all_vendors = await vendor_service.list_vendors(test_user, active_only=False)
    assert len(all_vendors) == 2

    active_only = await vendor_service.list_vendors(test_user, active_only=True)
    assert len(active_only) == 1
    assert active_only[0]["name"] == "Active 1"
