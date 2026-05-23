"""
Budget Service - Domain-Driven Design Application Layer

Orchestrates budget creation, updates, allocation tracking, and forecasting.
Enforces invariants via domain model and persists via repository.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.modules.shared.domain.exceptions import NotFoundError, ValidationError
from app.modules.shared.domain.financial_engine import FinancialEngine
from app.modules.shared.application.audit_service import AuditService

from ..domain.budget import Budget
from ..domain.revision import BudgetRevision as BudgetRevisionDomain
from ..infrastructure.repository import BudgetRepository, BudgetRevisionRepository, FinancialStateRepository
from ..schemas.dto import BudgetCreate, BudgetUpdate, BudgetRevisionCreate, BudgetRevisionAction

logger = logging.getLogger(__name__)


class BudgetService:
    """
    Sovereign Budget Orchestrator.
    Manages budget lifecycle: create, allocate, forecast, lock, close.
    """

    def __init__(self, db, audit_service: AuditService):
        self.db = db
        self.audit_service = audit_service
        self.budget_repo = BudgetRepository(db)
        self.revision_repo = BudgetRevisionRepository(db)
        self.financial_state_repo = FinancialStateRepository(db)

    async def create_budget(
        self, user: dict, project_id: str, budget_data: BudgetCreate
    ) -> Dict[str, Any]:
        """
        Create a new budget for a project.

        Args:
            user: Authenticated user dict (contains organisation_id)
            project_id: Project ID
            budget_data: BudgetCreate DTO with total_budget and allocations

        Returns:
            Created budget dict

        Raises:
            ValidationError: If budget invariants violated
        """
        organisation_id = user["organisation_id"]

        # Build domain model
        budget_dict = {
            "_id": ObjectId(),
            "project_id": project_id,
            "organisation_id": organisation_id,
            "total_budget": budget_data.total_budget,
            "allocations": [a.model_dump() for a in budget_data.allocations],
            "status": "ACTIVE",
            "version": 1,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }

        budget = Budget(budget_dict)
        budget.validate_on_create()  # Raises ValueError if invariants fail

        # Persist
        created = await self.budget_repo.create(budget.to_dict())
        budget_id = str(created["_id"])

        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="CREATE",
            user_id=user.get("user_id"),
            project_id=project_id,
            new_value=created,
        )

        logger.info(f"Budget created: {budget_id} for project {project_id}")
        return created

    async def get_budget(
        self, user: dict, budget_id: str
    ) -> Dict[str, Any]:
        """
        Retrieve a budget by ID with org scoping.

        Args:
            user: Authenticated user
            budget_id: Budget ID

        Returns:
            Budget dict

        Raises:
            NotFoundError: If budget not found
        """
        organisation_id = user["organisation_id"]

        try:
            budget_dict = await self.budget_repo.get_by_id(
                budget_id, organisation_id=organisation_id
            )
        except NotFoundError:
            raise NotFoundError(f"Budget {budget_id} not found")

        return budget_dict

    async def update_allocations(
        self, user: dict, budget_id: str, allocation_data: BudgetUpdate
    ) -> Dict[str, Any]:
        """
        Update budget allocations.

        Args:
            user: Authenticated user
            budget_id: Budget ID
            allocation_data: BudgetUpdate DTO with new allocations

        Returns:
            Updated budget dict

        Raises:
            NotFoundError: If budget not found
            ValidationError: If allocations invalid
        """
        organisation_id = user["organisation_id"]

        # Fetch current budget
        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        old_budget = Budget(budget_dict)

        # Apply changes via domain
        new_allocs = [a.model_dump() for a in allocation_data.allocations]
        old_budget.update_allocations(new_allocs)

        # Persist with version check
        budget_updates = old_budget.to_dict()
        budget_updates["version"] = allocation_data.expected_version + 1
        budget_updates["updated_at"] = datetime.now(timezone.utc)

        updated = await self.budget_repo.update(
            budget_id,
            budget_updates,
            organisation_id=organisation_id,
            expected_version=allocation_data.expected_version
        )
        if not updated:
            raise ValidationError("CONFLICT: Budget was modified by another process (Version Mismatch).")

        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="UPDATE",
            user_id=user.get("user_id"),
            project_id=old_budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(f"Budget allocations updated: {budget_id}")
        return updated

    async def allocate_to_payment(
        self, user: dict, budget_id: str, code: str, amount: Decimal
    ) -> Dict[str, Any]:
        """
        Allocate budget amount for a payment under a specific code.

        Decrements available budget; used when creating/approving payments.

        Args:
            user: Authenticated user
            budget_id: Budget ID
            code: Financial code (LABOR, MATERIAL, etc.)
            amount: Amount to allocate (Decimal)

        Returns:
            Updated budget dict with new allocation state

        Raises:
            NotFoundError: If budget or code not found
            ValidationError: If insufficient balance
        """
        organisation_id = user["organisation_id"]
        amount = FinancialEngine.round(Decimal(str(amount)))

        # Fetch current budget
        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        # Allocate via domain (raises ValueError if insufficient)
        try:
            budget.allocate_to_payment(code, amount)
        except ValueError as e:
            raise ValidationError(str(e))

        # Persist with version check
        current_version = budget_dict.get("version", 1)
        budget_updates = budget.to_dict()
        budget_updates["version"] = current_version + 1
        budget_updates["updated_at"] = datetime.now(timezone.utc)

        updated = await self.budget_repo.update(
            budget_id,
            budget_updates,
            organisation_id=organisation_id,
            expected_version=current_version
        )
        if not updated:
            raise ValidationError("CONFLICT: Budget was modified by another process (Version Mismatch).")

        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="UPDATE",
            user_id=user.get("user_id"),
            project_id=budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(
            f"Budget allocation: ${amount} for code {code} in budget {budget_id}"
        )
        return updated

    async def forecast_eac(
        self, user: dict, budget_id: str, percent_complete: Decimal = Decimal("50")
    ) -> Dict[str, Any]:
        """
        Calculate Estimate at Completion (EAC) based on current burn rate.

        Args:
            user: Authenticated user
            budget_id: Budget ID
            percent_complete: Project completion percentage (0-100)

        Returns:
            Dict with eac, projected_overrun, variance_at_completion

        Raises:
            NotFoundError: If budget not found
            ValidationError: If percent_complete invalid
        """
        organisation_id = user["organisation_id"]
        percent_complete = Decimal(str(percent_complete))

        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        try:
            forecast = budget.forecast_eac(percent_complete)
        except ValueError as e:
            raise ValidationError(str(e))

        return forecast

    async def lock_budget(self, user: dict, budget_id: str, expected_version: int) -> Dict[str, Any]:
        """
        Lock budget to prevent allocation changes (transitions ACTIVE → LOCKED).

        Args:
            user: Authenticated user
            budget_id: Budget ID
            expected_version: Current version provided by client

        Returns:
            Updated budget dict

        Raises:
            NotFoundError: If budget not found
            ValidationError: If transition invalid
        """
        organisation_id = user["organisation_id"]

        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        try:
            budget.lock_budget()
        except ValueError as e:
            raise ValidationError(str(e))

        budget_updates = budget.to_dict()
        budget_updates["version"] = expected_version + 1
        budget_updates["updated_at"] = datetime.now(timezone.utc)

        updated = await self.budget_repo.update(
            budget_id,
            budget_updates,
            organisation_id=organisation_id,
            expected_version=expected_version
        )
        if not updated:
            raise ValidationError("CONFLICT: Budget was modified by another process (Version Mismatch).")

        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="TRANSITION",
            user_id=user.get("user_id"),
            project_id=budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(f"Budget locked: {budget_id}")
        return updated

    async def close_budget(self, user: dict, budget_id: str, expected_version: int) -> Dict[str, Any]:
        """
        Close budget (final state: LOCKED/ACTIVE → CLOSED).

        Args:
            user: Authenticated user
            budget_id: Budget ID
            expected_version: Current version provided by client

        Returns:
            Updated budget dict

        Raises:
            NotFoundError: If budget not found
            ValidationError: If transition invalid
        """
        organisation_id = user["organisation_id"]

        budget_dict = await self.budget_repo.get_by_id(
            budget_id, organisation_id=organisation_id
        )
        budget = Budget(budget_dict)

        try:
            budget.close_budget()
        except ValueError as e:
            raise ValidationError(str(e))

        budget_updates = budget.to_dict()
        budget_updates["version"] = expected_version + 1
        budget_updates["updated_at"] = datetime.now(timezone.utc)

        updated = await self.budget_repo.update(
            budget_id,
            budget_updates,
            organisation_id=organisation_id,
            expected_version=expected_version
        )
        if not updated:
            raise ValidationError("CONFLICT: Budget was modified by another process (Version Mismatch).")

        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET",
            entity_id=budget_id,
            action_type="TRANSITION",
            user_id=user.get("user_id"),
            project_id=budget.project_id,
            old_value=budget_dict,
            new_value=updated,
        )

        logger.info(f"Budget closed: {budget_id}")
        return updated

    async def list_budgets(
        self, user: dict, project_id: str, limit: int = 100
    ) -> Dict[str, Any]:
        """
        List all budgets for a project.

        Args:
            user: Authenticated user
            project_id: Project ID
            limit: Max results

        Returns:
            Dict with items (list of budgets)
        """
        organisation_id = user["organisation_id"]
        budgets = await self.budget_repo.list_by_project(
            project_id, organisation_id, limit
        )
        return {"items": budgets, "count": len(budgets)}

    async def create_revision(
        self, user: dict, revision_data: BudgetRevisionCreate
    ) -> Dict[str, Any]:
        """
        Create a new budget revision (Variation Order).
        """
        organisation_id = user["organisation_id"]
        user_id = user.get("user_id")

        # Fetch current budget for the category
        budget_query = {
            "project_id": revision_data.project_id,
            "category_id": revision_data.category_id,
            "organisation_id": organisation_id
        }
        current_budget_doc = await self.budget_repo.find_one(budget_query)
        if not current_budget_doc:
            raise NotFoundError(f"Budget for category {revision_data.category_id} not found.")

        old_budget = Decimal(str(current_budget_doc.get("original_budget", 0)))

        # Build revision domain model
        revision_dict = {
            "organisation_id": organisation_id,
            "project_id": revision_data.project_id,
            "category_id": revision_data.category_id,
            "old_budget": old_budget,
            "new_budget": revision_data.new_budget,
            "reason": revision_data.reason,
            "status": "DRAFT",
            "created_by": user_id,
            "version": 1,
            "document_url": revision_data.document_url,
            "document_name": revision_data.document_name,
        }

        revision = BudgetRevisionDomain(revision_dict)
        
        # Persist
        created = await self.revision_repo.create(revision.to_dict())
        
        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET_REVISION",
            entity_id=str(created["_id"]),
            action_type="CREATE",
            user_id=user_id,
            project_id=revision_data.project_id,
            new_value=created,
        )

        return created

    async def submit_revision(
        self, user: dict, revision_id: str
    ) -> Dict[str, Any]:
        """
        Submit a budget revision for approval.
        """
        organisation_id = user["organisation_id"]
        user_id = user.get("user_id")

        revision_doc = await self.revision_repo.get_by_id(revision_id, organisation_id=organisation_id)
        revision = BudgetRevisionDomain(revision_doc)
        
        revision.submit(user_id)
        
        updated = await self.revision_repo.update(revision_id, revision.to_dict(), organisation_id=organisation_id)
        
        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET_REVISION",
            entity_id=revision_id,
            action_type="SUBMIT",
            user_id=user_id,
            project_id=revision.project_id,
            new_value=updated,
        )

        return updated

    async def reject_revision(
        self, user: dict, revision_id: str, action: BudgetRevisionAction
    ) -> Dict[str, Any]:
        """
        Reject a budget revision with a reason.
        """
        # Admin gate check for Variation Order actions (BUG-028/NR-005)
        from app.core.permissions import PermissionChecker
        await PermissionChecker.check_admin_role(user)

        organisation_id = user["organisation_id"]
        user_id = user.get("user_id")

        if not action.comment:
            raise ValidationError("Rejection reason (comment) is mandatory.")

        revision_doc = await self.revision_repo.get_by_id(revision_id, organisation_id=organisation_id)
        revision = BudgetRevisionDomain(revision_doc)
        
        revision.reject(user_id, action.comment)
        
        updated = await self.revision_repo.update(revision_id, revision.to_dict(), organisation_id=organisation_id)
        
        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET_REVISION",
            entity_id=revision_id,
            action_type="REJECT",
            user_id=user_id,
            project_id=revision.project_id,
            new_value=updated,
        )

        return updated

    async def approve_revision(
        self, user: dict, revision_id: str
    ) -> Dict[str, Any]:
        """
        Approve a budget revision and atomically update the project budget.
        """
        # Admin gate check for Variation Order actions (BUG-028/NR-005)
        from app.core.permissions import PermissionChecker
        await PermissionChecker.check_admin_role(user)

        organisation_id = user["organisation_id"]
        user_id = user.get("user_id")

        # 1. Fetch Revision
        revision_doc = await self.revision_repo.get_by_id(revision_id, organisation_id=organisation_id)
        revision = BudgetRevisionDomain(revision_doc)
        
        if revision.status == "APPROVED":
            raise ValidationError("Revision is already approved.")

        # For simplicity in this phase, we assume it was submitted or we allow direct approval by authorized users
        if revision.status == "DRAFT":
            revision.submit(user_id)
        
        revision.approve(user_id)

        async def perform_updates(session=None):
            # Update Revision Status
            await self.revision_repo.collection.update_one(
                {"_id": ObjectId(revision_id)},
                {"$set": revision.to_dict()},
                session=session
            )

            # Update Category Budget
            budget_query = {
                "project_id": revision.project_id,
                "category_id": revision.category_id,
                "organisation_id": organisation_id
            }
            budget_update = {
                "$set": {
                    "original_budget": FinancialEngine.to_d128(revision.new_budget),
                    "updated_at": datetime.now(timezone.utc)
                },
                "$inc": {"version": 1}
            }
            
            budget_result = await self.budget_repo.collection.update_one(
                budget_query, budget_update, session=session
            )
            
            if budget_result.matched_count == 0:
                raise NotFoundError("Target budget for revision not found.")

            # Update Financial State (Derived State)
            state_update = {
                "$set": {
                    "original_budget": FinancialEngine.to_d128(revision.new_budget),
                    "last_updated": datetime.now(timezone.utc)
                },
                "$inc": {"version": 1}
            }
            await self.financial_state_repo.collection.update_one(
                budget_query, state_update, session=session
            )

        # 2. Atomic Update using Transaction (with graceful fallback to sequential if standalone MongoDB)
        try:
            async with await self.db.client.start_session() as session:
                async with session.start_transaction():
                    await perform_updates(session)
        except Exception as e:
            if "Transaction numbers are only allowed" in str(e) or "replica set member" in str(e):
                logger.warning("MongoDB transaction not supported (standalone mode). Executing updates sequentially.")
                await perform_updates(None)
            else:
                raise

        # 3. Trigger Master Recalculation
        from .financial_service import FinancialService
        financial_service = FinancialService(self.db, self.audit_service)
        await financial_service.recalculate_master_budget(revision.project_id)

        # 4. Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET_REVISION",
            entity_id=revision_id,
            action_type="APPROVE",
            user_id=user_id,
            project_id=revision.project_id,
            old_value=revision_doc,
            new_value=revision.to_dict(),
        )

        logger.info(f"Budget revision approved: {revision_id} for project {revision.project_id}")
        return revision.to_dict()

    async def list_revisions(
        self, user: dict, project_id: str, category_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List budget revisions for a project or specific category.
        """
        organisation_id = user["organisation_id"]
        return await self.revision_repo.list_by_project(
            project_id, organisation_id, category_id
        )

    async def attach_document(
        self, user: dict, revision_id: str, file_name: str, file_content: bytes
    ) -> Dict[str, Any]:
        """Attach a supporting document to a budget revision draft."""
        import uuid
        from app.core.storage import storage_manager

        organisation_id = user["organisation_id"]
        revision_doc = await self.revision_repo.get_by_id(revision_id, organisation_id=organisation_id)
        if not revision_doc:
            raise NotFoundError(f"Budget revision {revision_id} not found.")

        revision = BudgetRevisionDomain(revision_doc)
        if revision.status != "DRAFT":
            raise ValidationError(f"Cannot upload attachments in status: {revision.status}")

        # 1. Save to storage
        file_ext = file_name.split(".")[-1] if "." in file_name else "pdf"
        file_id = str(uuid.uuid4())
        relative_path = f"organisations/{organisation_id}/revisions/{revision_id}/{file_id}.{file_ext}"
        await storage_manager.save_file(file_content, relative_path)

        # 2. Update revision record
        revision.document_url = relative_path
        revision.document_name = file_name
        revision.updated_at = datetime.now(timezone.utc)

        updated = await self.revision_repo.update(revision_id, revision.to_dict(), organisation_id=organisation_id)

        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET_REVISION",
            entity_id=revision_id,
            action_type="ATTACH_DOCUMENT",
            user_id=user["user_id"],
            project_id=revision.project_id,
            new_value={"document_url": relative_path, "document_name": file_name},
        )

        return updated

    async def delete_document(self, user: dict, revision_id: str) -> Dict[str, Any]:
        """Delete supporting document from a budget revision draft."""
        from app.core.storage import storage_manager

        organisation_id = user["organisation_id"]
        revision_doc = await self.revision_repo.get_by_id(revision_id, organisation_id=organisation_id)
        if not revision_doc:
            raise NotFoundError(f"Budget revision {revision_id} not found.")

        revision = BudgetRevisionDomain(revision_doc)
        if revision.status != "DRAFT":
            raise ValidationError(f"Cannot delete attachments in status: {revision.status}")

        if not revision.document_url:
            return revision.to_dict()

        # 1. Delete from storage
        try:
            await storage_manager.delete_file(revision.document_url)
        except Exception as e:
            logger.error(f"Failed to delete file {revision.document_url} from storage: {e}")

        # 2. Clear fields
        revision.document_url = None
        revision.document_name = None
        revision.updated_at = datetime.now(timezone.utc)

        updated = await self.revision_repo.update(revision_id, revision.to_dict(), organisation_id=organisation_id)

        # Audit
        await self.audit_service.log_financial_event(
            organisation_id=organisation_id,
            entity_type="BUDGET_REVISION",
            entity_id=revision_id,
            action_type="DELETE_DOCUMENT",
            user_id=user["user_id"],
            project_id=revision.project_id,
            new_value={},
        )

        return updated
