"""MongoDB index management for task collections."""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class TaskIndexManager:
    """Manages MongoDB indexes for task-related collections."""

    @staticmethod
    async def create_indexes(db: AsyncIOMotorDatabase) -> None:
        """
        Create all necessary indexes for task collections.

        Indexes are created at startup for:
        - task_sr_no_counters: atomic counter for serial numbers
        - tasks: main task collection
        - task_ai_summaries: cached AI summaries

        Args:
            db: Motor async database instance
        """
        try:
            # Index for task_sr_no_counters (atomic counter)
            # Ensures unique (org_id, project_id) pairs
            counter = db["task_sr_no_counters"]
            await counter.create_index(
                [("organisation_id", 1), ("project_id", 1)],
                unique=True
            )
            logger.debug("Created unique index on task_sr_no_counters")

            # Indexes for tasks collection
            tasks = db["tasks"]

            # Compound index for org + project filtering (most common query)
            await tasks.create_index([("organisation_id", 1), ("project_id", 1)])
            logger.debug("Created index on tasks(organisation_id, project_id)")

            # Compound index for org + project + status filtering
            await tasks.create_index(
                [("organisation_id", 1), ("project_id", 1), ("status", 1)]
            )
            logger.debug("Created index on tasks(organisation_id, project_id, status)")

            # Index for assignment queries
            await tasks.create_index([("organisation_id", 1), ("assigned_to_user_id", 1)])
            logger.debug("Created index on tasks(organisation_id, assigned_to_user_id)")

            # Index for deadline-based queries (overdue detection)
            await tasks.create_index([("deadline", 1)])
            logger.debug("Created index on tasks(deadline)")

            # Indexes for task_ai_summaries collection
            summary = db["task_ai_summaries"]

            # Compound index for cache lookups with recency
            await summary.create_index(
                [("organisation_id", 1), ("project_id", 1), ("created_at", -1)]
            )
            logger.debug(
                "Created index on task_ai_summaries(organisation_id, project_id, created_at)"
            )

            logger.info("Task indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating task indexes: {str(e)}", exc_info=True)
            raise
