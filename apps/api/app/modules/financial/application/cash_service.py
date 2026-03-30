import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from bson import Decimal128, ObjectId

from app.core.permissions import PermissionChecker
from app.core.uow import UnitOfWork
from app.modules.identity.infrastructure.repository import UserRepository

# Note: Repositories from other contexts
from app.modules.project.infrastructure.repository import ProjectRepository
from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine

from ..infrastructure.repository import (
    CashTransactionRepository,
    CodeMasterRepository,
    FundAllocationRepository,
)
from ..schemas.dto import (
    CashTransaction,
    CashTransactionCreate,
    FundAllocation,
    FundAllocationCreate,
)

logger = logging.getLogger(__name__)


class CashService:
    """
    Sovereign Cash Controller.
    Enforces atomic fund adjustments and threshold monitoring via UnitOfWork.
    """

    def __init__(self, db, permission_checker: PermissionChecker, audit_service):
        self.db = db
        self.permission_checker = permission_checker
        self.audit_service = audit_service
        self.fund_repo = FundAllocationRepository(db)
        self.txn_repo = CashTransactionRepository(db)
        self.project_repo = ProjectRepository(db)
        self.code_repo = CodeMasterRepository(db)
        self.user_repo = UserRepository(db)

    def _get_threshold_for_category(self, category, project) -> Decimal:
        default_threshold = Decimal("1000.0")
        if not category or not project:
            return default_threshold
        cat_name = category.get("category_name", "").lower()
        if "petty" in cat_name:
            return Decimal(str(project.get("threshold_petty", default_threshold)))
        elif "ovh" in cat_name or "overhead" in cat_name:
            return Decimal(str(project.get("threshold_ovh", default_threshold)))
        return default_threshold

    async def get_cash_summary(self, user: dict, project_id: str) -> Dict[str, Any]:
        """Aggregate project-wide cash state with threshold status."""
        await self.permission_checker.check_project_access(user, project_id)

        now_dt = datetime.now(timezone.utc)
        project = await self.project_repo.get_by_project_id(project_id)

        categories = await self.code_repo.list(
            {
                "organisation_id": user["organisation_id"],
                "budget_type": "fund_transfer",
            },
            limit=100,
        )

        if not categories:
            return {
                "categories": [],
                "summary": {"total_cash_in_hand": 0.0, "days_since_last_pc_close": 0},
            }

        category_ids = [str(cat["id"]) for cat in categories]

        pipeline = [
            {
                "$match": {
                    "project_id": project_id,
                    "category_id": {"$in": category_ids},
                }
            },
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
                                        {"$eq": ["$fund_request", True]},
                                    ]
                                }
                            }
                        },
                        {"$project": {"updated_at": 1}},
                    ],
                    "as": "closed_pcs",
                }
            },
            {"$addFields": {"last_pc_close_date": {"$max": "$closed_pcs.updated_at"}}},
            {"$project": {"closed_pcs": 0}},
        ]

        allocation_docs = await self.db.fund_allocations.aggregate(pipeline).to_list(
            length=200
        )
        allocation_by_cat = {str(doc["category_id"]): doc for doc in allocation_docs}
        category_map = {str(cat["id"]): cat for cat in categories}

        categories_data = []
        total_cash_in_hand = Decimal("0.0")

        for cat in categories:
            cat_id = str(cat["id"])
            allocation = allocation_by_cat.get(cat_id, {})

            threshold = self._get_threshold_for_category(cat, project)
            alloc_received = FinancialEngine.to_decimal(
                allocation.get("allocation_received", 0)
            )
            expenses = FinancialEngine.to_decimal(allocation.get("total_expenses", 0))
            alloc_original = FinancialEngine.to_decimal(
                allocation.get("allocation_original", 0)
            )

            cash_in_hand = alloc_received - expenses
            alloc_remaining = alloc_original - alloc_received
            total_cash_in_hand += cash_in_hand

            days_since = None
            last_close = allocation.get("last_pc_close_date")
            if last_close:
                if last_close.tzinfo is None:
                    last_close = last_close.replace(tzinfo=timezone.utc)
                days_since = (now_dt - last_close).days

            categories_data.append(
                {
                    "category_id": cat_id,
                    "category_name": cat.get("category_name"),
                    "cash_in_hand": float(cash_in_hand),
                    "allocation_remaining": float(alloc_remaining),
                    "allocation_total": float(alloc_original),
                    "threshold": float(threshold),
                    "days_since_last_pc_close": days_since,
                    "is_negative": cash_in_hand < 0,
                    "threshold_breached": cash_in_hand <= threshold,
                }
            )

        return {
            "categories": categories_data,
            "summary": {
                "total_cash_in_hand": float(total_cash_in_hand),
                "days_since_last_pc_close": min(
                    (
                        c["days_since_last_pc_close"]
                        for c in categories_data
                        if c["days_since_last_pc_close"] is not None
                    ),
                    default=0,
                ),
            },
        }

    async def list_fund_allocations(
        self, user: dict, project_id: str
    ) -> List[Dict[str, Any]]:
        await self.permission_checker.check_project_access(user, project_id)

        pipeline = [
            {"$match": {"project_id": project_id}},
            {"$addFields": {"cid_obj": {"$toObjectId": "$category_id"}}},
            {
                "$lookup": {
                    "from": "code_master",
                    "localField": "cid_obj",
                    "foreignField": "_id",
                    "as": "cat_info",
                }
            },
            {"$unwind": {"path": "$cat_info", "preserveNullAndEmptyArrays": True}},
            {
                "$project": {
                    "id": {"$toString": "$_id"},
                    "project_id": 1,
                    "category_id": 1,
                    "allocation_original": 1,
                    "allocation_received": 1,
                    "allocation_remaining": 1,
                    "last_pc_closed_date": 1,
                    "created_at": 1,
                    "category_name": "$cat_info.category_name",
                }
            },
            {"$sort": {"created_at": -1}},
        ]
        return await self.db.fund_allocations.aggregate(pipeline).to_list(100)

    async def list_cash_transactions(
        self,
        user: dict,
        project_id: str,
        category_id: Optional[str] = None,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)

        query = {"project_id": project_id, "organisation_id": user["organisation_id"]}
        if category_id:
            query["category_id"] = category_id
        if cursor:
            try:
                query["created_at"] = {
                    "$lt": datetime.fromisoformat(cursor.replace("Z", "+00:00"))
                }
            except ValueError:
                raise ValidationError("Invalid cursor format")

        docs = await self.txn_repo.list(query, sort=[("created_at", -1)], limit=limit)

        next_cursor = None
        if len(docs) == limit:
            ts = docs[-1].get("created_at")
            if isinstance(ts, datetime):
                next_cursor = ts.isoformat()

        for d in docs:
            if d.get("created_by"):
                u = await self.user_repo.get_by_id(d["created_by"])
                if u:
                    d["created_by_name"] = (
                        u.get("name") or u.get("email", "").split("@")[0]
                    )
            if d.get("category_id"):
                cat = await self.code_repo.get_by_id(d["category_id"])
                if cat:
                    d["category_name"] = cat.get("category_name")
            if "amount" in d:
                d["amount"] = float(FinancialEngine.to_decimal(d["amount"]))
            if "created_at" in d and isinstance(d["created_at"], datetime):
                d["created_at"] = d["created_at"].isoformat()

        return {"items": docs, "next_cursor": next_cursor}

    async def create_cash_transaction(
        self, user: dict, project_id: str, data: Dict[str, Any], idempotency_key: str
    ) -> Dict[str, Any]:
        """Atomic fund allocation and transaction record creation."""
        await self.permission_checker.check_write_access_with_role(user, project_id)

        amount = Decimal(str(data["amount"]))
        category_id = data["category_id"]
        txn_type = data["type"]

        async with UnitOfWork(self.db) as uow:
            if idempotency_key:
                from app.core.idempotency import get_recorded_operation

                recorded = await get_recorded_operation(
                    self.db, uow.session, idempotency_key
                )
                if recorded:
                    return recorded

            # Use underlying collection for atomic fund adjustment
            allocation = await uow.db.fund_allocations.find_one(
                {"project_id": project_id, "category_id": category_id},
                session=uow.session,
            )
            if not allocation:
                raise NotFoundError("Category Allocation", category_id)

            inc_ops = {
                "cash_in_hand": (
                    FinancialEngine.to_d128(-amount)
                    if txn_type == "DEBIT"
                    else FinancialEngine.to_d128(amount)
                )
            }
            if txn_type == "DEBIT":
                inc_ops["total_expenses"] = FinancialEngine.to_d128(amount)

            updated_alloc = await uow.db.fund_allocations.find_one_and_update(
                {"_id": allocation["_id"]},
                {"$inc": inc_ops},
                return_document=True,
                session=uow.session,
            )
            new_cash = FinancialEngine.to_decimal(updated_alloc.get("cash_in_hand"))

            txn_doc = {
                "project_id": project_id,
                "organisation_id": user["organisation_id"],
                "category_id": category_id,
                "amount": FinancialEngine.to_d128(amount),
                "type": txn_type,
                "description": data.get("description"),
                "transaction_date": data.get("transaction_date"),
                "created_by": user["user_id"],
                "version": 1,
            }
            new_txn = await uow.cash_transactions.create(txn_doc, session=uow.session)

            if idempotency_key:
                from app.core.idempotency import record_operation

                await record_operation(
                    self.db,
                    uow.session,
                    idempotency_key,
                    "CASH_TXN",
                    response_payload=new_txn,
                )

            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="CASH_FLOWS",
                entity_type="CASH_TRANSACTION",
                entity_id=new_txn["id"],
                action_type="CREATE",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=new_txn,
                session=uow.session,
            )

            project = await uow.projects.get_by_id(
                project_id, organisation_id=user["organisation_id"], session=uow.session
            )
            category = await uow.db.code_master.find_one(
                {"_id": ObjectId(category_id)}, session=uow.session
            )
            threshold = self._get_threshold_for_category(category, project)

            warnings = []
            if new_cash < 0:
                warnings.append("negative_cash")
            elif new_cash <= threshold:
                warnings.append("threshold_breach")

            return {
                **new_txn,
                "warnings": warnings,
                "new_cash_in_hand": float(new_cash),
            }
