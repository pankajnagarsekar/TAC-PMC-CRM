from fastapi import APIRouter, Depends, Query, status
from typing import List, Dict, Any

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_vendor_service
from app.services.vendor_service import VendorService
from app.schemas.vendor import Vendor, VendorCreate, VendorUpdate

router = APIRouter(prefix="/vendors", tags=["Vendors"])

@router.get("/", response_model=List[Vendor])
async def list_vendors(
    active_only: bool = Query(True),
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service)
):
    return await vendor_service.list_vendors(user, active_only)

@router.post("/", response_model=Vendor, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    vendor_data: VendorCreate,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service)
):
    return await vendor_service.create_vendor(user, vendor_data)

@router.get("/{vendor_id}", response_model=Vendor)
async def get_vendor(
    vendor_id: str,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service)
):
    return await vendor_service.get_vendor(user, vendor_id)

@router.put("/{vendor_id}", response_model=Vendor)
async def update_vendor(
    vendor_id: str,
    vendor_update: VendorUpdate,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service)
):
    return await vendor_service.update_vendor(user, vendor_id, vendor_update)

@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service)
):
    return await vendor_service.delete_vendor(user, vendor_id)

@router.get("/{vendor_id}/ledger")
async def get_vendor_ledger(
    vendor_id: str,
    user: dict = Depends(get_authenticated_user),
    vendor_service: VendorService = Depends(get_vendor_service)
):
    return await vendor_service.get_ledger(user, vendor_id)
