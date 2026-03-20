from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime

from core.database import get_db
from auth import get_current_user
from models import VendorLedgerEntry
from core.utils import serialize_doc

financial_router = APIRouter(prefix="/api", tags=["Financials"])


# Using central serialize_doc from core.utils


@financial_router.get("/projects/{project_id}/vendor-ledger", response_model=List[VendorLedgerEntry])
async def get_project_vendor_ledger(
    project_id: str,
    vendor_id: Optional[str] = Query(None, description="Filter by vendor"),
    entry_type: Optional[str] = Query(None, description="Filter by entry type: PC_CERTIFIED, PAYMENT_MADE, RETENTION_HELD"),
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all vendor ledger entries for a project, optionally filtered by vendor or type."""
    query: dict = {"project_id": project_id}
    if vendor_id:
        query["vendor_id"] = vendor_id
    if entry_type:
        query["entry_type"] = entry_type

    entries = await db.vendor_ledger.find(query).sort("created_at", -1).to_list(length=500)
    return [serialize_doc(e) for e in entries]


@financial_router.get("/projects/{project_id}/vendor-payables")
async def get_project_vendor_payables(
    project_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Aggregate vendor payables per vendor for the project.
    Returns: vendor_id, vendor_name, total_certified, total_paid, total_retention, net_payable
    Net payable = total_certified - total_paid - total_retention
    """
    pipeline = [
        {"$match": {"project_id": project_id}},
        {
            "$group": {
                "_id": "$vendor_id",
                "total_certified": {
                    "$sum": {
                        "$cond": [{"$eq": ["$entry_type", "PC_CERTIFIED"]}, "$amount", 0]
                    }
                },
                "total_paid": {
                    "$sum": {
                        "$cond": [{"$eq": ["$entry_type", "PAYMENT_MADE"]}, "$amount", 0]
                    }
                },
                "total_retention": {
                    "$sum": {
                        "$cond": [{"$eq": ["$entry_type", "RETENTION_HELD"]}, "$amount", 0]
                    }
                },
            }
        },
        {
            "$addFields": {
                "net_payable": {
                    "$subtract": [
                        "$total_certified",
                        {"$add": ["$total_paid", "$total_retention"]}
                    ]
                }
            }
        },
        {"$sort": {"net_payable": -1}}
    ]

    results = await db.vendor_ledger.aggregate(pipeline).to_list(length=200)

    # Join vendor names
    payables = []
    for r in results:
        vendor_id = r["_id"]
        vendor_name = "Unknown"
        if vendor_id and ObjectId.is_valid(vendor_id):
            vendor = await db.vendors.find_one({"_id": ObjectId(vendor_id)}, {"name": 1})
            if vendor:
                vendor_name = vendor.get("name", "Unknown")

        payables.append({
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "total_certified": float(r.get("total_certified", 0)),
            "total_paid": float(r.get("total_paid", 0)),
            "total_retention": float(r.get("total_retention", 0)),
            "net_payable": float(r.get("net_payable", 0)),
        })

    return payables
