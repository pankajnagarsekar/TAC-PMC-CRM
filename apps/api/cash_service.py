"""
Cash Transaction Business Logic Service

Implements the MongoDB Multi-Document Transactions for recording
cash expenses (Petty Cash / OVH) as defined in the Technical Architecture.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId, Decimal128
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.performance import measure_performance

logger = logging.getLogger(__name__)


class CashService:
    def __init__(self, db: AsyncIOMotorDatabase, audit_service=None):
        self.db = db
        self.audit_service = audit_service

    def _serialize_doc(self, doc: dict) -> dict:
        """Convert MongoDB document to JSON-serializable dict."""
        if not doc:
            return doc
        serialized = {}
        for k, v in doc.items():
            if k == '_id' and isinstance(v, ObjectId):
                serialized[k] = str(v)
            elif isinstance(v, Decimal128):
                serialized[k] = float(v.to_decimal())
            elif isinstance(v, datetime):
                serialized[k] = v.isoformat()
            else:
                serialized[k] = v
        return serialized

    def _get_threshold_for_category(self, category, project) -> Decimal:
        """Determine threshold based on category name (Petty vs OVH)."""
        default_threshold = Decimal("1000.0")
        
        if not category or not project:
            return default_threshold
        
        cat_name = category.get("category_name", "").lower()
        
        if "petty" in cat_name:
            return Decimal(str(project.get("threshold_petty", default_threshold)))
        elif "ovh" in cat_name or "overhead" in cat_name:
            return Decimal(str(project.get("threshold_ovh", default_threshold)))
        
        return default_threshold

    async def get_cash_summary(self, project_id: str, organisation_id: str) -> dict:
        """
        Get cash summary per category with threshold and countdown.
        
        Returns:
            {
                "categories": [
                    {
                        "category_id": str,
                        "category_name": str,
                        "cash_in_hand": float,
                        "allocation_remaining": float,
                        "allocation_total": float,
                        "threshold": float,
                        "days_since_last_pc_close": int | None,
                        "is_negative": bool,
                        "is_below_threshold": bool
                    }
                ],
                "summary": {
                    "total_cash_in_hand": float,
                    "days_since_last_pc_close": int
                }
            }
        """
        # Get project for threshold values
        project = await self.db.projects.find_one({"project_id": project_id})
        
        # Get all categories for this organisation with budget_type = fund_transfer
        categories = await self.db.categories.find({
            "organisation_id": organisation_id,
            "budget_type": "fund_transfer"
        }).to_list(length=100)
        
        # Get all fund allocations for this project
        allocations = await self.db.fund_allocations.find({"project_id": project_id}).to_list(length=100)
        
        # Build allocation lookup by category_id
        allocation_by_cat = {str(a.get("category_id")): a for a in allocations}
        
        default_threshold = Decimal("1000.0")
        
        categories_data = []
        total_cash_in_hand = Decimal("0")
        
        for cat in categories:
            cat_id = str(cat.get("_id"))
            allocation = allocation_by_cat.get(cat_id)
            
            if not allocation:
                continue
            
            threshold = self._get_threshold_for_category(cat, project)
            
            # Per Spec §5.1: cash_in_hand = allocation_received - total_expenses
            allocation_received = Decimal(str(allocation.get("allocation_received", Decimal128("0")).to_decimal()))
            total_expenses = Decimal(str(allocation.get("total_expenses", Decimal128("0")).to_decimal()))
            cash_in_hand = allocation_received - total_expenses
            total_cash_in_hand += cash_in_hand
            
            # Find last PC close date for this category
            last_pc = await self.db.payment_certificates.find_one(
                {
                    "project_id": project_id,
                    "category_id": cat_id,
                    "status": "Closed",
                    "fund_request": True
                },
                sort=[("updated_at", -1)]
            )
            
            days_since_last_pc_close = None
            if last_pc and last_pc.get("updated_at"):
                last_date = last_pc["updated_at"]
                if last_date.tzinfo is None:
                    last_date = last_date.replace(tzinfo=timezone.utc)
                diff = datetime.now(timezone.utc) - last_date
                days_since_last_pc_close = diff.days
            
            is_negative = cash_in_hand < 0
            threshold_breached = cash_in_hand <= threshold  # 3.2.5: Use threshold_breached per spec
            
            # Per Spec §5.1: allocation_remaining = allocation_original - allocation_received
            allocation_original = Decimal(str(allocation.get("allocation_original", Decimal128("0")).to_decimal()))
            allocation_received = Decimal(str(allocation.get("allocation_received", Decimal128("0")).to_decimal()))
            allocation_remaining = allocation_original - allocation_received

            categories_data.append({
                "category_id": cat_id,
                "category_name": cat.get("category_name"),
                "cash_in_hand": float(cash_in_hand),
                "allocation_remaining": float(allocation_remaining),  # FIXED: Now correctly calculated per spec
                "allocation_total": float(allocation_original),
                "threshold": float(threshold),
                "days_since_last_pc_close": days_since_last_pc_close,
                "is_negative": is_negative,
                "threshold_breached": threshold_breached  # 3.2.5: Fixed field name per spec
            })
        
        # For backward compatibility, also return summary totals
        return {
            "categories": categories_data,
            "summary": {
                "total_cash_in_hand": float(total_cash_in_hand),
                "days_since_last_pc_close": min([c["days_since_last_pc_close"] for c in categories_data if c["days_since_last_pc_close"] is not None] or [0])
            }
        }

    async def list_cash_transactions(
        self,
        project_id: str,
        organisation_id: str,
        category_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100
    ) -> dict:
        """
        List cash transactions with pagination.
        
        Returns:
            {
                "items": [...],
                "next_cursor": str | None
            }
        """
        query = {"project_id": project_id, "organisation_id": organisation_id}
        if category_id:
            query["category_id"] = category_id
            
        if cursor:
            try:
                parsed_cursor = datetime.fromisoformat(cursor.replace('Z', '+00:00'))
                query["created_at"] = {"$lt": parsed_cursor}
            except ValueError:
                raise ValueError("Invalid cursor format")

        cursor_obj = self.db.cash_transactions.find(query).sort("created_at", -1).limit(limit)
        docs = await cursor_obj.to_list(length=limit)
        
        next_cursor = None
        if len(docs) == limit:
            last_doc = docs[-1]
            ts = last_doc.get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()

        return {
            "items": [self._serialize_doc(d) for d in docs],
            "next_cursor": next_cursor
        }
