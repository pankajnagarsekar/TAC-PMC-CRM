import logging
import secrets
from decimal import Decimal
from typing import List, Optional, Dict, Any
from bson import ObjectId, Decimal128

from ..schemas.dto import Project, ProjectUpdate, ProjectCreate, ProjectBudget
from ..infrastructure.repository import ProjectRepository, BudgetRepository
from ..infrastructure.read_models import ProjectStatsRepository
from app.modules.shared.domain.state_machine import StateMachine
from app.core.time import now
from app.core.uow import UnitOfWork
from app.modules.shared.domain.exceptions import ValidationError, NotFoundError
from app.modules.shared.domain.financial_engine import FinancialEngine
from ..domain.models import Project as ProjectModel

logger = logging.getLogger(__name__)

class ProjectService:
    """
    Sovereign Logic for Project Lifecycle.
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
        """Project creation with auto-ID and initial financial state."""
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)

        doc = project_data.model_dump()
        doc["organisation_id"] = user["organisation_id"]
        
        if not doc.get("project_id"):
            doc["project_id"] = f"PROJ-{secrets.token_hex(4).upper()}"

        doc.update({
            "version": 1,
            "created_at": now(),
            "updated_at": now(),
            "master_original_budget": FinancialEngine.to_d128(Decimal("0.0")),
            "master_remaining_budget": FinancialEngine.to_d128(Decimal("0.0")),
            "completion_percentage": FinancialEngine.to_d128(Decimal("0.0"))
        })

        for k, v in doc.items():
            if isinstance(v, Decimal):
                doc[k] = FinancialEngine.to_d128(v)

        result = await self.project_repo.create(doc)
        
        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="PROJECT_MANAGEMENT",
            entity_type="PROJECT", entity_id=result["id"], action_type="CREATE",
            user_id=user["user_id"], project_id=result["project_id"], new_value=result
        )
        
        await self.stats_repo.refresh_stats(result["project_id"], {
            "master_budget": 0.0, "total_committed": 0.0, "total_phases": 0
        })

        return result

    async def get_project(self, user: dict, project_id: str) -> Dict[str, Any]:
        """Fetch project with access control."""
        await self.permission_checker.check_project_access(user, project_id)
        project = await self.project_repo.get_by_id(project_id, organisation_id=user["organisation_id"])
        
        if not project:
            project = await self.project_repo.find_one({
                "project_id": project_id, "organisation_id": user["organisation_id"]
            })
            
        if not project:
            raise NotFoundError("Project", project_id)
            
        return project

    async def update_project(self, user: dict, project_id: str, project_data: ProjectUpdate) -> Dict[str, Any]:
        """Update project with state machine validation."""
        await self.permission_checker.check_web_crm_access(user)
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, require_write=True)

        existing = await self.get_project(user, project_id)
        project_model = ProjectModel(existing)
        
        update_dict = project_data.model_dump(exclude_unset=True)

        if "status" in update_dict:
            project_model.validate_transition(update_dict["status"])
        
        project_model.can_modify()

        for k, v in update_dict.items():
            if isinstance(v, Decimal):
                update_dict[k] = FinancialEngine.to_d128(v)

        update_dict["updated_at"] = now()
        result = await self.project_repo.update(project_id, update_dict, organisation_id=user["organisation_id"])
        
        if not result:
             raise ValidationError("DATA_CONSISTENCY_ERROR: Project not found or update failed.")

        await self.audit_service.log_action(
            organisation_id=user["organisation_id"], module_name="PROJECT_MANAGEMENT",
            entity_type="PROJECT", entity_id=project_id, action_type="UPDATE",
            user_id=user["user_id"], project_id=project_id, old_value=existing, new_value=result
        )

        return result

    async def delete_project(self, user: dict, project_id: str) -> bool:
        """Sovereign Soft-Delete Cascade across financial entities."""
        await self.permission_checker.check_admin_role(user)
        await self.permission_checker.check_project_access(user, project_id, require_write=True)
        
        project = await self.get_project(user, project_id)
        
        async with UnitOfWork(self.db) as uow:
            await uow.projects.soft_delete(project_id, session=uow.session)
            
            query = {"project_id": project_id}
            await uow.budgets.collection.update_many(query, {"$set": {"is_deleted": True, "deleted_at": now()}}, session=uow.session)
            await uow.work_orders.collection.update_many(query, {"$set": {"is_deleted": True, "deleted_at": now()}}, session=uow.session)
            await uow.payments.collection.update_many(query, {"$set": {"is_deleted": True, "deleted_at": now()}}, session=uow.session)
            
            await self.audit_service.log_action(
                organisation_id=user["organisation_id"], module_name="PROJECT_MANAGEMENT",
                entity_type="PROJECT", entity_id=project_id, action_type="DELETE",
                user_id=user["user_id"], project_id=project_id, old_value=project, session=uow.session
            )
            
        return True
