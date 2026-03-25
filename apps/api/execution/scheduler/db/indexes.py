"""
MongoDB Index Definitions for PPM Scheduler Collections.
Optimized for the query patterns defined in the System Constitution and Schema §5.

Index strategy goals:
    1. project_id + wbs_code / sort_index queries (Grid load)
    2. task_id direct lookups (O(1) engine I/O)
    3. parent_id hierarchy traversal (WBS tree rendering)
    4. external_ref_id financial join (WO/PC $lookup join key)
    5. assigned_resources multikey (resource utilization / leveling)
    6. is_critical + project_id (critical path filter)
    7. audit_log recency queries (timestamp DESC)

Schema Reference: §5 (Index Strategy)
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# Index definitions
# Each entry: { collection, index_spec, options }
# =============================================================================

SCHEDULER_INDEXES: List[Dict[str, Any]] = [

    # -------------------------------------------------------------------------
    # project_schedules — Primary query patterns
    # -------------------------------------------------------------------------
    {
        "collection": "project_schedules",
        "keys": [("project_id", 1), ("wbs_code", 1)],
        "options": {
            "name": "idx_ps_project_wbs",
            "background": True,
            # Comment: Primary grid load query — project + WBS sort
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("project_id", 1), ("sort_index", 1)],
        "options": {
            "name": "idx_ps_project_sort",
            "background": True,
            # Comment: Ordered display without wbs_code recompute
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("task_id", 1)],
        "options": {
            "name": "idx_ps_task_id",
            "unique": True,
            "background": True,
            # Comment: Direct task lookup — O(1) for engine I/O
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("parent_id", 1)],
        "options": {
            "name": "idx_ps_parent_id",
            "background": True,
            # Comment: WBS hierarchy traversal — get all children of a parent
            # Sparse: root tasks have null parent_id
            "sparse": True,
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("external_ref_id", 1)],
        "options": {
            "name": "idx_ps_external_ref_id",
            "unique": True,
            "background": True,
            # Comment: Financial join key — MUST be unique, supports $lookup from WO/PC
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("project_id", 1), ("is_critical", 1)],
        "options": {
            "name": "idx_ps_project_critical",
            "background": True,
            # Comment: Critical path overlay filter
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("assigned_resources", 1)],
        "options": {
            "name": "idx_ps_assigned_resources",
            "background": True,
            # Comment: Multikey index — supports resource utilization queries
            # across all tasks assigned to a given resource
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("project_id", 1), ("task_status", 1)],
        "options": {
            "name": "idx_ps_project_status",
            "background": True,
            # Comment: Kanban board filter — tasks by status within a project
        },
    },
    {
        "collection": "project_schedules",
        "keys": [("project_id", 1), ("is_deadline_breached", 1)],
        "options": {
            "name": "idx_ps_project_deadline_breach",
            "background": True,
            "sparse": True,
            # Comment: Alert queries for deadline breach monitoring
        },
    },

    # -------------------------------------------------------------------------
    # enterprise_resources
    # -------------------------------------------------------------------------
    {
        "collection": "enterprise_resources",
        "keys": [("resource_id", 1)],
        "options": {
            "name": "idx_er_resource_id",
            "unique": True,
            "background": True,
        },
    },
    {
        "collection": "enterprise_resources",
        "keys": [("type", 1)],
        "options": {
            "name": "idx_er_type",
            "background": True,
            # Comment: Filter by Personnel / Vendor / Machinery
        },
    },

    # -------------------------------------------------------------------------
    # schedule_baselines
    # -------------------------------------------------------------------------
    {
        "collection": "schedule_baselines",
        "keys": [("project_id", 1), ("baseline_number", 1)],
        "options": {
            "name": "idx_sb_project_baseline",
            "unique": True,
            "background": True,
            # Comment: Unique — prevents duplicate baseline numbers per project
        },
    },
    {
        "collection": "schedule_baselines",
        "keys": [("project_id", 1), ("locked_at", -1)],
        "options": {
            "name": "idx_sb_project_locked_at",
            "background": True,
            # Comment: Most recent baseline lookup
        },
    },

    # -------------------------------------------------------------------------
    # audit_log
    # -------------------------------------------------------------------------
    {
        "collection": "audit_log",
        "keys": [("project_id", 1), ("timestamp", -1)],
        "options": {
            "name": "idx_al_project_timestamp",
            "background": True,
            # Comment: Recent activity feed — project dashboard
        },
    },
    {
        "collection": "audit_log",
        "keys": [("task_id", 1), ("timestamp", -1)],
        "options": {
            "name": "idx_al_task_timestamp",
            "background": True,
            "sparse": True,
            # Comment: Task history — task detail drawer
        },
    },
    {
        "collection": "audit_log",
        "keys": [("actor_id", 1), ("timestamp", -1)],
        "options": {
            "name": "idx_al_actor_timestamp",
            "background": True,
            # Comment: Per-user activity queries
        },
    },

    # -------------------------------------------------------------------------
    # project_calendars
    # -------------------------------------------------------------------------
    {
        "collection": "project_calendars",
        "keys": [("project_id", 1)],
        "options": {
            "name": "idx_pc_project_id",
            "unique": True,
            "background": True,
            # Comment: One calendar per project — unique enforced at DB level
        },
    },

    # -------------------------------------------------------------------------
    # project_metadata
    # -------------------------------------------------------------------------
    {
        "collection": "project_metadata",
        "keys": [("project_id", 1)],
        "options": {
            "name": "idx_pm_project_id",
            "unique": True,
            "background": True,
        },
    },
    {
        "collection": "project_metadata",
        "keys": [("project_status", 1)],
        "options": {
            "name": "idx_pm_status",
            "background": True,
            # Comment: Portfolio view filter by project_status
        },
    },
]


# =============================================================================
# Index creation helper — called at application startup
# =============================================================================

async def create_scheduler_indexes(db) -> Dict[str, Any]:
    """
    Creates all PPM Scheduler indexes in MongoDB.
    Safe to call repeatedly — uses background: True and ignores
    IndexAlreadyExists errors for idempotent startup behaviour.

    Args:
        db: Motor AsyncIOMotorDatabase instance

    Returns:
        Dict with { "created": [...], "skipped": [...], "errors": [...] }
    """
    results: Dict[str, Any] = {"created": [], "skipped": [], "errors": []}

    for index_def in SCHEDULER_INDEXES:
        collection_name = index_def["collection"]
        keys = index_def["keys"]
        options = index_def["options"].copy()
        index_name = options.pop("name", None)

        try:
            collection = db[collection_name]
            await collection.create_index(keys, name=index_name, **options)
            results["created"].append(f"{collection_name}.{index_name}")
            logger.info(f"Index created: {collection_name}.{index_name}")

        except Exception as e:
            error_msg = str(e)
            if "already exists" in error_msg.lower() or "IndexKeySpecsConflict" in error_msg:
                results["skipped"].append(f"{collection_name}.{index_name}")
                logger.debug(f"Index already exists (skipped): {collection_name}.{index_name}")
            else:
                results["errors"].append({
                    "index": f"{collection_name}.{index_name}",
                    "error": error_msg,
                })
                logger.error(f"Index creation failed: {collection_name}.{index_name} — {error_msg}")

    return results


async def drop_scheduler_indexes(db) -> None:
    """
    Drops all PPM Scheduler indexes.
    USE WITH CAUTION — only for test teardown or fresh deployments.
    Production should use create_scheduler_indexes (idempotent) instead.
    """
    collections_seen = set()
    for index_def in SCHEDULER_INDEXES:
        c = index_def["collection"]
        if c not in collections_seen:
            try:
                await db[c].drop_indexes()
                collections_seen.add(c)
                logger.warning(f"Dropped all indexes on {c}")
            except Exception as e:
                logger.error(f"Failed to drop indexes on {c}: {e}")
