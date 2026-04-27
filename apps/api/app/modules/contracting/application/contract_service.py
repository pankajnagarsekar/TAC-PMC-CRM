import logging
from datetime import datetime, timezone
from typing import Any, Dict

from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
from ..infrastructure.repository import ContractRepository, WorkOrderRepository
from ..schemas.dto import ContractCreate, ContractUpdate

logger = logging.getLogger(__name__)


class ContractService:
    def __init__(self, db, audit_service, permission_checker):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.contract_repo = ContractRepository(db)
        self.wo_repo = WorkOrderRepository(db)

    async def create_contract(self, user: dict, wo_id: str, data: ContractCreate) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]

        # 1. Fetch WO
        wo = await self.wo_repo.get_by_id(wo_id, organisation_id=organisation_id)
        if not wo:
            raise NotFoundError("Work Order", wo_id)

        # 2. Check if contract already exists
        existing = await self.contract_repo.find_one({"work_order_id": wo_id})
        if existing:
            raise ValidationError("Contract already exists for this Work Order")

        # 3. Check WO status (Must be Approved to create contract)
        if wo.get("status") not in ["Approved", "Completed", "Closed"]:
            raise ValidationError(
                f"Work Order must be Approved before creating a contract. Current: {wo.get('status')}"
            )

        contract_dict = data.dict()
        contract_dict.update({
            "organisation_id": organisation_id,
            "status": "DRAFT",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        new_contract = await self.contract_repo.create(contract_dict)

        await self.audit_service.log_action(
            organisation_id=organisation_id,
            module_name="CONTRACT_MANAGEMENT",
            entity_type="CONTRACT",
            entity_id=new_contract["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=wo.get("project_id"),
            new_value=new_contract
        )
        return new_contract

    async def get_contract_by_wo(self, user: dict, wo_id: str) -> Dict[str, Any]:
        contract = await self.contract_repo.find_one({"work_order_id": wo_id})
        if not contract:
            raise NotFoundError("Contract for Work Order", wo_id)
        return contract

    async def update_contract(self, user: dict, contract_id: str, data: ContractUpdate) -> Dict[str, Any]:
        organisation_id = user["organisation_id"]
        existing = await self.contract_repo.get_by_id(contract_id, organisation_id=organisation_id)
        if not existing:
            raise NotFoundError("Contract", contract_id)

        update_dict = data.dict(exclude_unset=True)
        update_dict["updated_at"] = datetime.now(timezone.utc)
        update_dict["version"] = data.expected_version + 1

        updated = await self.contract_repo.update(
            contract_id,
            update_dict,
            expected_version=data.expected_version
        )
        if not updated:
            raise ValidationError("CONFLICT: Contract was modified by another process (Version Mismatch).")

        await self.audit_service.log_action(
            organisation_id=organisation_id,
            module_name="CONTRACT_MANAGEMENT",
            entity_type="CONTRACT",
            entity_id=contract_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            old_value=existing,
            new_value=updated
        )
        return updated
