import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

from bson import ObjectId

from app.core.uow import UnitOfWork
from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine

from ..infrastructure.repository import (
    RetentionReleaseRepository,
    WorkOrderRepository,
)
from ..schemas.retention_dto import RetentionReleaseCreate

logger = logging.getLogger(__name__)


class RetentionService:
    """
    Sovereign Retention Orchestrator for Contracting Context.
    Manages work order retention releases, audits, and vendor ledger balancing.
    """

    def __init__(self, db, audit_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.wo_repo = WorkOrderRepository(db)
        self.retention_repo = RetentionReleaseRepository(db)

    async def get_retention_balance(self, user: dict, wo_id: str) -> Dict[str, Any]:
        """
        Calculate total retention held, released, and remaining balance for a Work Order.
        """
        organisation_id = user["organisation_id"]
        wo = await self.wo_repo.get_by_id(wo_id, organisation_id=organisation_id)
        if not wo:
            raise NotFoundError("Work Order", wo_id)

        project_id = wo["project_id"]
        await self.permission_checker.check_project_access(
            user, project_id, require_write=False
        )

        # 1. Sum all retention amount held in Paid Payment Certificates linked to this Work Order
        pipeline = [
            {
                "$match": {
                    "work_order_id": wo_id,
                    "organisation_id": organisation_id,
                    "status": "Paid",
                }
            },
            {"$group": {"_id": None, "total_held": {"$sum": "$retention_amount"}}},
        ]

        held_result = await self.db.payment_certificates.aggregate(pipeline).to_list(1)
        total_held = FinancialEngine.to_decimal(
            held_result[0]["total_held"] if held_result else 0
        )

        # 2. Sum all previous retention releases
        release_pipeline = [
            {"$match": {"wo_id": wo_id, "organisation_id": organisation_id}},
            {
                "$group": {
                    "_id": None,
                    "total_released": {"$sum": "$amount_released"},
                }
            },
        ]

        release_result = await self.db.retention_releases.aggregate(
            release_pipeline
        ).to_list(1)
        total_released = FinancialEngine.to_decimal(
            release_result[0]["total_released"] if release_result else 0
        )

        current_balance = total_held - total_released
        if current_balance < 0:
            current_balance = Decimal("0.00")

        return {
            "work_order_id": wo_id,
            "total_held": float(total_held),
            "total_released": float(total_released),
            "current_balance": float(current_balance),
        }

    async def create_retention_release(
        self, user: dict, wo_id: str, release_data: RetentionReleaseCreate
    ) -> Dict[str, Any]:
        """
        Release full/partial retention in an atomic transaction.
        Writes PAYMENT_MADE entry in vendor_ledger and log a financial audit event.
        """
        organisation_id = user["organisation_id"]

        # Permission Gate: Requires admin access for releasing funds/retention
        await self.permission_checker.check_admin_role(user)

        async with UnitOfWork(self.db) as uow:
            # 1. Fetch work order to confirm existence & get project_id
            wo = await uow.work_orders.get_by_id(
                wo_id, organisation_id=organisation_id, session=uow.session
            )
            if not wo:
                raise NotFoundError("Work Order", wo_id)

            project_id = wo["project_id"]
            vendor_id = wo.get("vendor_id")
            if not vendor_id:
                raise ValidationError("Work Order is not linked to a vendor.")

            # Validate project access
            await self.permission_checker.check_project_access(
                user, project_id, require_write=True
            )

            # 2. Calculate balance in transaction to prevent race conditions
            pc_pipeline = [
                {
                    "$match": {
                        "work_order_id": wo_id,
                        "organisation_id": organisation_id,
                        "status": "Paid",
                    }
                },
                {"$group": {"_id": None, "total_held": {"$sum": "$retention_amount"}}},
            ]
            held_result = await uow.payments.collection.aggregate(
                pc_pipeline, session=uow.session
            ).to_list(1)
            total_held = FinancialEngine.to_decimal(
                held_result[0]["total_held"] if held_result else 0
            )

            release_pipeline = [
                {"$match": {"wo_id": wo_id, "organisation_id": organisation_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_released": {"$sum": "$amount_released"},
                    }
                },
            ]
            release_result = await uow.retention_releases.collection.aggregate(
                release_pipeline, session=uow.session
            ).to_list(1)
            total_released = FinancialEngine.to_decimal(
                release_result[0]["total_released"] if release_result else 0
            )

            current_balance = total_held - total_released
            if current_balance < 0:
                current_balance = Decimal("0.00")

            release_amount = FinancialEngine.to_decimal(release_data.amount_released)
            if release_amount <= 0:
                raise ValidationError("Release amount must be greater than zero.")

            if release_amount > current_balance:
                raise ValidationError(
                    f"OVER_RELEASE: Cannot release {release_amount}. Current retention balance is {current_balance}."
                )

            # 3. Create RetentionRelease document
            now_dt = datetime.now(timezone.utc)
            release_entry = {
                "organisation_id": organisation_id,
                "wo_id": wo_id,
                "amount_released": FinancialEngine.to_d128(release_amount),
                "release_date": release_data.release_date,
                "release_reference": release_data.release_reference,
                "notes": release_data.notes or "",
                "released_by": user["user_id"],
                "created_at": now_dt,
            }

            new_release = await uow.retention_releases.create(
                release_entry, session=uow.session
            )

            # 4. Write standard PAYMENT_MADE entry to the vendor_ledger (balancing accounts)
            ledger_entry = {
                "vendor_id": str(vendor_id),
                "project_id": project_id,
                "ref_id": str(new_release["id"]),
                "entry_type": "PAYMENT_MADE",
                "amount": FinancialEngine.to_d128(release_amount),
                "created_at": now_dt,
            }
            await uow.ledger.create(ledger_entry, session=uow.session)

            # 5. Log financial audit event
            await self.audit_service.log_financial_event(
                organisation_id=organisation_id,
                entity_type="RETENTION_RELEASE",
                entity_id=str(new_release["id"]),
                action_type="CREATE",
                user_id=user["user_id"],
                project_id=project_id,
                new_value=new_release,
                session=uow.session,
            )

            # 6. Format Decimal elements for DTO serialization
            new_release["amount_released"] = float(release_amount)
            new_release["id"] = str(new_release["id"])
            return new_release

    async def list_retention_releases(
        self, user: dict, wo_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all retention releases matching a Work Order.
        """
        organisation_id = user["organisation_id"]
        wo = await self.wo_repo.get_by_id(wo_id, organisation_id=organisation_id)
        if not wo:
            raise NotFoundError("Work Order", wo_id)

        project_id = wo["project_id"]
        await self.permission_checker.check_project_access(
            user, project_id, require_write=False
        )

        releases = await self.retention_repo.list(
            {"wo_id": wo_id, "organisation_id": organisation_id}
        )

        for release in releases:
            release["id"] = str(release.get("id") or release.get("_id") or "")
            release["amount_released"] = float(
                FinancialEngine.to_decimal(release.get("amount_released") or 0)
            )

        return releases
