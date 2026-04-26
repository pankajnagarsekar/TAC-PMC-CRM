"""Cache management for task AI summaries."""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.modules.tasks.infrastructure.repository import TaskAISummaryRepository

logger = logging.getLogger(__name__)


class TaskAISummaryCache:
    """Manages invalidation of cached AI summaries for tasks."""

    @staticmethod
    async def invalidate_for_project(
        db: AsyncIOMotorDatabase, org_id: str, project_id: str
    ) -> None:
        """
        Invalidate (delete) all cached AI summaries for a project.

        Called when a task is created, updated, or deleted to ensure
        the summary cache reflects current state.

        Args:
            db: Motor async database instance
            org_id: Organization ID for scoping
            project_id: Project ID to invalidate cache for
        """
        repo = TaskAISummaryRepository(db)
        try:
            result = await repo.collection.delete_many({
                "project_id": project_id,
                "organisation_id": org_id
            })
            if result.deleted_count > 0:
                logger.debug(
                    f"Invalidated {result.deleted_count} cached summaries "
                    f"for project {project_id} in org {org_id}"
                )
        except Exception as e:
            logger.error(
                f"Error invalidating task summary cache: {str(e)}",
                exc_info=True
            )
            # Don't propagate cache errors - allow task operations to succeed
            pass
