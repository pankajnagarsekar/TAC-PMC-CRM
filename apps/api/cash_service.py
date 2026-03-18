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
                serialized[k] = str(v.to_decimal())
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
                        "threshold_breached": bool
                    }
                ],
                "summary": {
                    "total_cash_in_hand": float,
                    "days_since_last_pc_close": int
                }
            }
        """
        now = datetime.now(timezone.utc)

        # ── Round-trip 1: project (for threshold values) ─────────────────────
        project = await self.db.projects.find_one({"project_id": project_id})

        # ── Round-trip 2: fund_transfer categories for this organisation ──────
        categories = await self.db.categories.find({
            "organisation_id": organisation_id,
            "budget_type": "fund_transfer"
        }).to_list(length=100)

        if not categories:
            return {"categories": [], "summary": {"total_cash_in_hand": 0.0, "days_since_last_pc_close": 0}}

        category_ids = [str(cat["_id"]) for cat in categories]

        # ── Round-trip 3: single aggregation — replaces N find_one calls ──────
        # Pipeline joins fund_allocations → payment_certificates and resolves
        # the latest "Closed + fund_request" PC date per category in one shot.
        pipeline = [
            # Start from fund_allocations scoped to this project + relevant cats
            {
                "$match": {
                    "project_id": project_id,
                    "category_id": {"$in": category_ids}
                }
            },
            # Join payment_certificates on matching project + category + status
            {
                "$lookup": {
                    "from": "payment_certificates",
                    "let": {"cat_id": "$category_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$project_id", project_id]},
                                        {"$eq": ["$category_id", "$$cat_id"]},
                                        {"$eq": ["$status", "Closed"]},
                                        {"$eq": ["$fund_request", True]}
                                    ]
                                }
                            }
                        },
                        # Only carry the field we need — minimise network payload
                        {"$project": {"updated_at": 1, "_id": 0}}
                    ],
                    "as": "closed_pcs"
                }
            },
            # Resolve the single latest close date per allocation document
            {
                "$addFields": {
                    "last_pc_close_date": {"$max": "$closed_pcs.updated_at"}
                }
            },
            # Drop the joined array — no longer needed
            {
                "$project": {"closed_pcs": 0}
            }
        ]

        allocation_docs = await self.db.fund_allocations.aggregate(pipeline).to_list(length=200)

        # ── Pure Python O(N) merge — zero additional DB calls ─────────────────
        allocation_by_cat = {str(doc["category_id"]): doc for doc in allocation_docs}
        category_map = {str(cat["_id"]): cat for cat in categories}

        default_threshold = Decimal("1000.0")
        categories_data = []
        total_cash_in_hand = Decimal("0")

        for cat_id, allocation in allocation_by_cat.items():
            cat = category_map.get(cat_id)
            if not cat:
                continue

            threshold = self._get_threshold_for_category(cat, project)

            # Per Spec §5.1: cash_in_hand = allocation_received - total_expenses
            def _dec(val):
                """Safely coerce Decimal128 / str / int / float → Decimal."""
                if isinstance(val, Decimal128):
                    return Decimal(str(val.to_decimal()))
                return Decimal(str(val)) if val is not None else Decimal("0")

            allocation_received  = _dec(allocation.get("allocation_received"))
            total_expenses       = _dec(allocation.get("total_expenses"))
            allocation_original  = _dec(allocation.get("allocation_original"))

            cash_in_hand         = allocation_received - total_expenses
            allocation_remaining = allocation_original - allocation_received
            total_cash_in_hand  += cash_in_hand

            # last_pc_close_date is resolved from the $lookup/$max in the aggregation
            days_since_last_pc_close = None
            last_close = allocation.get("last_pc_close_date")
            if last_close:
                if isinstance(last_close, datetime) and last_close.tzinfo is None:
                    last_close = last_close.replace(tzinfo=timezone.utc)
                days_since_last_pc_close = (now - last_close).days

            categories_data.append({
                "category_id":              cat_id,
                "category_name":            cat.get("category_name"),
                "cash_in_hand":             str(cash_in_hand),
                "allocation_remaining":     str(allocation_remaining),
                "allocation_total":         str(allocation_original),
                "threshold":                str(threshold),
                "days_since_last_pc_close": days_since_last_pc_close,
                "is_negative":              cash_in_hand < 0,
                "threshold_breached":       cash_in_hand <= threshold,
            })

        return {
            "categories": categories_data,
            "summary": {
                "total_cash_in_hand": str(total_cash_in_hand),
                "days_since_last_pc_close": min(
                    (c["days_since_last_pc_close"] for c in categories_data if c["days_since_last_pc_close"] is not None),
                    default=0
                )
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
