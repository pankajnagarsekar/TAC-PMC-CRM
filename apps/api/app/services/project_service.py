from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId, Decimal128
from fastapi import HTTPException
import logging

from app.schemas.project import Project, ProjectUpdate
from app.repositories.project_repo import ProjectRepository
from app.repositories.financial_repo import BudgetRepository
from app.core.utils import serialize_doc

logger = logging.getLogger(__name__)

class ProjectService:
    def __init__(self, db, audit_service, permission_checker, financial_service):
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.financial_service = financial_service
        self.project_repo = ProjectRepository(db)
        self.budget_repo = BudgetRepository(db)

    async def list_projects(self, user: dict) -> List[Dict[str, Any]]:
        query = {"organisation_id": user["organisation_id"]}
        
        # Non-Admins only see assigned projects
        if user["role"] != "Admin":
            assigned = user.get("assigned_projects", [])
            query["$or"] = [
                {"_id": {"$in": [ObjectId(p) for p in assigned if ObjectId.is_valid(p)]}},
                {"project_id": {"$in": assigned}}
            ]
            
        return await self.project_repo.list(query)

    async def get_project(self, user: dict, project_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id)
        
        project = await self.project_repo.get_by_id(project_id, organisation_id=user["organisation_id"])
        if not project:
            # Try by string project_id if ObjectId fails or not found
            project = await self.project_repo.find_one({"project_id": project_id, "organisation_id": user["organisation_id"]})
            
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Hydrate project_id if missing
        if "id" in project:
            project["project_id"] = project["id"]
            
        return project

    async def update_project(self, user: dict, project_id: str, project_data: ProjectUpdate) -> Dict[str, Any]:
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, require_write=True)

        existing = await self.get_project(user, project_id)

        update_dict = project_data.dict(exclude_unset=True)
        # Convert Decimals for Mongo
        for k, v in update_dict.items():
            if isinstance(v, Decimal):
                update_dict[k] = Decimal128(str(v))

        result = await self.project_repo.update(project_id, update_dict, organisation_id=user["organisation_id"])
        if not result:
             raise HTTPException(status_code=404, detail="Project not found")

        # Audit log
        try:
            await self.audit_service.log_action(
                organisation_id=user["organisation_id"],
                module_name="PROJECT_MANAGEMENT",
                entity_type="PROJECT",
                entity_id=project_id,
                action_type="UPDATE",
                user_id=user["user_id"],
                old_value=existing,
                new_value=result
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        return result

    async def get_project_budgets(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_project_access(user, project_id)

        budgets = await self.budget_repo.list({"project_id": project_id})
        for b in budgets:
            if "category_id" in b:
                b["code_id"] = b["category_id"]
        return budgets

    async def create_or_update_project_budget(self, user: dict, project_id: str, budget_data: dict) -> Dict[str, Any]:
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, require_write=True)

        category_id = budget_data.get("category_id") or budget_data.get("code_id")
        if not category_id:
            raise HTTPException(status_code=400, detail="Category ID is required")

        original_budget = budget_data.get("original_budget")
        budget_decimal = Decimal(str(original_budget))
        
        existing = await self.budget_repo.get_by_project_and_category(project_id, category_id)

        if existing:
            update_data = {
                "original_budget": Decimal128(str(budget_decimal)),
                "description": budget_data.get("description")
            }
            result = await self.budget_repo.update(existing["id"], update_data)
        else:
            budget_dict = {
                "project_id": project_id,
                "category_id": category_id,
                "organisation_id": user["organisation_id"],
                "original_budget": Decimal128(str(budget_decimal)),
                "description": budget_data.get("description"),
                "committed_amount": Decimal128("0.0"),
                "remaining_budget": Decimal128(str(budget_decimal)),
                "version": 1
            }
            result = await self.budget_repo.create(budget_dict)

        # Async recalculation
        try:
            await self.financial_service.recalculate_all_project_financials(project_id)
        except Exception as e:
            logger.warning(f"Financial recalculation failed for project {project_id}: {e}")

        return result
