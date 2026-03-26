from typing import List, Optional, Dict, Any
from decimal import Decimal
from bson import ObjectId, Decimal128
from fastapi import HTTPException
import logging
import secrets

from app.schemas.project import Project, ProjectUpdate, ProjectCreate
from app.repositories.project_repo import ProjectRepository
from app.repositories.financial_repo import BudgetRepository
from app.repositories.read_models import ProjectStatsRepository
from app.core.time import now
from app.domain.state_machine import StateMachine
from app.core.financial_utils import to_decimal

logger = logging.getLogger(__name__)

class ProjectService:
    """
    Sovereign Logic for Project Lifecycle (Point 1, 31, 87).
    Enforces transitions via StateMachine and manages financial budget allocation.
    """
    def __init__(self, db, audit_service, permission_checker, financial_service):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.financial_service = financial_service
        self.project_repo = ProjectRepository(db)
        self.budget_repo = BudgetRepository(db)
        self.stats_repo = ProjectStatsRepository(db)

    async def list_projects(self, user: dict) -> List[Dict[str, Any]]:
        query = {"organisation_id": user["organisation_id"]}
        if user["role"] != "Admin":
            assigned = user.get("assigned_projects", [])
            query["$or"] = [
                {"_id": {"$in": [ObjectId(p) for p in assigned if ObjectId.is_valid(p)]}},
                {"project_id": {"$in": assigned}}
            ]
        return await self.project_repo.list(query)

    async def create_project(self, user: dict, project_data: ProjectCreate) -> Dict[str, Any]:
        """Fixed CR-13: Authoritative project creation logic."""
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)

        doc = project_data.model_dump()
        doc["organisation_id"] = user["organisation_id"]
        
        # Auto-generate project_id if missing
        if not doc.get("project_id"):
            doc["project_id"] = f"PROJ-{secrets.token_hex(4).upper()}"

        # Initialize technical fields
        doc.update({
            "version": 1,
            "created_at": now(),
            "updated_at": now(),
            "master_original_budget": Decimal128("0.0"),
            "master_remaining_budget": Decimal128("0.0"),
            "completion_percentage": Decimal128("0.0")
        })

        # Decimal to Decimal128 conversion
        for k, v in doc.items():
            if isinstance(v, Decimal):
                doc[k] = Decimal128(str(v))

        result = await self.project_repo.create(doc)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="PROJECT_MANAGEMENT",
            entity_type="PROJECT",
            entity_id=result["id"],
            action_type="CREATE",
            user_id=user["user_id"],
            project_id=result["project_id"],
            new_value=result
        )
        
        # Initialize stats read model
        await self.stats_repo.refresh_stats(result["project_id"], {
            "master_budget": 0.0,
            "total_committed": 0.0,
            "total_phases": 0
        })

        return result

    async def get_project(self, user: dict, project_id: str) -> Dict[str, Any]:
        """Fetch project with authoritative access control (Point 17)."""
        await self.permission_checker.check_project_access(user, project_id)
        project = await self.project_repo.get_by_id(project_id, organisation_id=user["organisation_id"])
        
        if not project:
            project = await self.project_repo.find_one({
                "project_id": project_id, 
                "organisation_id": user["organisation_id"]
            })
            
        if not project:
            raise HTTPException(status_code=404, detail="PROJECT_NOT_FOUND")
            
        return project

    async def update_project(self, user: dict, project_id: str, project_data: ProjectUpdate) -> Dict[str, Any]:
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, require_write=True)

        existing = await self.get_project(user, project_id)
        current_status = existing.get("status", "Draft")
        
        update_dict = project_data.model_dump(exclude_unset=True)

        if "status" in update_dict:
            StateMachine.validate_transition("PROJECT", current_status, update_dict["status"])
        
        StateMachine.check_modification_allowed("PROJECT", current_status)

        for k, v in update_dict.items():
            if isinstance(v, Decimal):
                update_dict[k] = Decimal128(str(v))

        update_dict["updated_at"] = now()
        result = await self.project_repo.update(project_id, update_dict, organisation_id=user["organisation_id"])
        
        if not result:
             raise HTTPException(status_code=404, detail="DATA_CONSISTENCY_ERROR")

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"],
            module_name="PROJECT_MANAGEMENT",
            entity_type="PROJECT",
            entity_id=project_id,
            action_type="UPDATE",
            user_id=user["user_id"],
            project_id=project_id,
            old_value=existing,
            new_value=result
        )

        return result

    async def create_or_update_project_budget(self, user: dict, project_id: str, budget_data: dict) -> Dict[str, Any]:
        # ... (existing logic)
        return result

    async def delete_project(self, user: dict, project_id: str) -> bool:
        """Fixed CR-18 (Point 43): Sovereign Soft-Delete Cascade."""
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
        project = await self.get_project(user, project_id)
        
        from app.core.uow import UnitOfWork
        async with UnitOfWork(self.db) as uow:
            # 1. Soft Delete Project
            await uow.projects.soft_delete(project_id, session=uow.session)
            
            # 2. Cascade to Financial Entities
            query = {"project_id": project_id}
            # Note: Repo soft_delete takes ID, but we want bulk for project-scoped items
            # We use underlying collection for efficiency in cascades
            await uow.budgets.collection.update_many(query, {"$set": {"is_deleted": True, "deleted_at": now()}}, session=uow.session)
            await uow.work_orders.collection.update_many(query, {"$set": {"is_deleted": True, "deleted_at": now()}}, session=uow.session)
            await uow.payments.collection.update_many(query, {"$set": {"is_deleted": True, "deleted_at": now()}}, session=uow.session)
            
            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="PROJECT_MANAGEMENT",
                entity_type="PROJECT",
                entity_id=project_id,
                action_type="DELETE",
                user_id=user["user_id"],
                project_id=project_id,
                old_value=project,
                session=uow.session
            )
            
        return True
