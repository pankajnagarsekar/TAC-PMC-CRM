from typing import List, Optional, Dict, Any
from decimal import Decimal
from bson import ObjectId, Decimal128
from fastapi import HTTPException
import logging

from app.schemas.project import Project, ProjectUpdate
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
        """Budget logic with immediate reconciliation and read-model sync (Point 46, 61)."""
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
        category_id = budget_data.get("category_id") or budget_data.get("code_id")
        if not category_id: raise HTTPException(status_code=400, detail="CATEGORY_ID_REQUIRED")

        project = await self.get_project(user, project_id)
        StateMachine.check_modification_allowed("PROJECT", project.get("status"))

        original_budget = Decimal(str(budget_data.get("original_budget", "0")))
        existing = await self.budget_repo.get_by_project_and_category(project_id, category_id)

        if existing:
            update = {
                "original_budget": Decimal128(str(original_budget)),
                "updated_at": now()
            }
            result = await self.budget_repo.update(existing["id"], update)
        else:
            doc = {
                "project_id": project_id,
                "category_id": category_id,
                "organisation_id": user["organisation_id"],
                "original_budget": Decimal128(str(original_budget)),
                "committed_amount": Decimal128("0.0"),
                "remaining_budget": Decimal128(str(original_budget)),
                "version": 1,
                "created_at": now()
            }
            result = await self.budget_repo.create(doc)

        # RELIABILITY: Recalculate Master Budget (Point 61)
        master = await self.financial_service.recalculate_master_budget(project_id)
        
        # PUSH TO READ MODEL (Point 46)
        await self.stats_repo.refresh_stats(project_id, {
            "master_budget": float(to_decimal(master["total_budget"])),
            "total_committed": float(to_decimal(master["total_committed"])),
            "total_phases": await self.budget_repo.count_documents({"project_id": project_id})
        })

        return result
