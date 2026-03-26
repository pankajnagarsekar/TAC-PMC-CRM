from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal
from bson import ObjectId, Decimal128
from fastapi import HTTPException

from app.repositories.base_repo import BaseRepository
from app.schemas.project import Project, ProjectUpdate
from app.core.utils import serialize_doc

class ProjectService:
    def __init__(self, db, audit_service, permission_checker, financial_service):
        self.db = db
        self.audit_service = audit_service
        self.permission_checker = permission_checker
        self.financial_service = financial_service
        self.project_repo = BaseRepository(db, "projects", Project)

    async def list_projects(self, user: dict) -> List[Dict[str, Any]]:
        query = {"organisation_id": user["organisation_id"]}
        
        # Non-Admins only see assigned projects
        if user["role"] != "Admin":
            assigned = user.get("assigned_projects", [])
            query["$or"] = [
                {"_id": {"$in": [ObjectId(p) for p in assigned if ObjectId.is_valid(p)]}},
                {"project_id": {"$in": assigned}}
            ]
            
        projects = await self.db.projects.find(query).to_list(length=100)
        return [serialize_doc(p) for p in projects]

    async def get_project(self, user: dict, project_id: str) -> Dict[str, Any]:
        await self.permission_checker.check_project_access(user, project_id, self.db)
        
        try:
            query = {"_id": ObjectId(project_id)}
        except:
            query = {"project_id": project_id}
            
        project = await self.db.projects.find_one({**query, "organisation_id": user["organisation_id"]})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Hydrate project_id if missing
        if "_id" in project:
            project["project_id"] = str(project["_id"])
            
        return serialize_doc(project)

    async def update_project(self, user: dict, project_id: str, project_data: ProjectUpdate) -> Dict[str, Any]:
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, self.db, require_write=True)

        update_dict = {}
        for k, v in project_data.dict(exclude_unset=True).items():
            if v is not None:
                if isinstance(v, Decimal):
                    update_dict[k] = Decimal128(str(v))
                else:
                    update_dict[k] = v
        update_dict["updated_at"] = datetime.now(timezone.utc)

        try:
            query = {"_id": ObjectId(project_id)}
        except:
            query = {"project_id": project_id}

        result = await self.db.projects.find_one_and_update(
            query,
            {"$set": update_dict},
            return_document=True
        )

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
                new_value=serialize_doc(update_dict)
            )
        except Exception as e:
            # Non-blocking logger
            import logging
            logging.getLogger(__name__).warning(f"Audit log failed: {e}")

        return serialize_doc(result)

    async def get_project_budgets(self, user: dict, project_id: str) -> List[Dict[str, Any]]:
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_project_access(user, project_id, self.db)

        budgets = await self.db.project_category_budgets.find({"project_id": project_id}).to_list(length=100)
        result = []
        for b in budgets:
            serialized = serialize_doc(b)
            if "category_id" in serialized:
                serialized["code_id"] = serialized["category_id"]
            result.append(serialized)
        return result

    async def create_or_update_project_budget(self, user: dict, project_id: str, budget_data: dict) -> Dict[str, Any]:
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, self.db, require_write=True)

        category_id = budget_data.get("category_id") or budget_data.get("code_id")
        if not category_id:
            raise HTTPException(status_code=400, detail="Category ID is required")

        original_budget = budget_data.get("original_budget")
        budget_decimal = Decimal(str(original_budget))
        
        budget_dict = {
            "project_id": project_id,
            "category_id": category_id,
            "organisation_id": user["organisation_id"],
            "updated_at": datetime.now(timezone.utc),
            "original_budget": Decimal128(str(budget_decimal)),
            "description": budget_data.get("description")
        }

        existing = await self.db.project_category_budgets.find_one({"project_id": project_id, "category_id": category_id})

        if existing:
            await self.db.project_category_budgets.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "original_budget": budget_dict["original_budget"],
                    "description": budget_dict["description"],
                    "updated_at": budget_dict["updated_at"]
                }}
            )
            result = await self.db.project_category_budgets.find_one({"_id": existing["_id"]})
        else:
            budget_dict["created_at"] = datetime.now(timezone.utc)
            budget_dict["committed_amount"] = Decimal128("0.0")
            budget_dict["remaining_budget"] = budget_dict["original_budget"]
            budget_dict["version"] = 1
            insert_res = await self.db.project_category_budgets.insert_one(budget_dict)
            result = await self.db.project_category_budgets.find_one({"_id": insert_res.inserted_id})

        # Async recalculation
        try:
            await self.financial_service.recalculate_all_project_financials(project_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Financial recalculation failed for project {project_id}: {e}")

        return serialize_doc(result)
