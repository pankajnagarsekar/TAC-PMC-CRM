"""
Financial Handshake Aggregation Pipelines.
Read-only $lookup pipelines that join the PPM Scheduler with legacy
work_orders and payment_certificates collections.

ABSOLUTE RULE (Constitution §1, Schema §2):
    These pipelines MUST NEVER contain $set, $unset, $merge, $out,
    $replaceRoot (writing form), insert, update, or delete operations.
    Only $lookup, $match, $group, $project, $addFields, $unwind,
    $sort, $limit, $skip are permitted.

Join key (Schema §2.1):
    WO/PC task_id  ←→  project_schedules.external_ref_id
    external_ref_id is the IMMUTABLE stable reference. Never join on
    wbs_code (not stable) or task_id ObjectId (may differ across systems).

Financial invariants (Constitution §2.3):
    wo_value, wo_retention_value, payment_value are NEVER persisted
    to project_schedules. Computed at read-time in this file.
    Exception: project_total_baseline_cost_cache lives in project_metadata.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from decimal import Decimal


# =============================================================================
# Approved statuses for each legacy collection
# =============================================================================

# Work Orders with these statuses contribute to wo_value
WO_APPROVED_STATUSES = ["Approved", "Completed", "Closed"]

# Payment Certificates with these statuses contribute to payment_value
PC_APPROVED_STATUSES = ["Approved", "Paid"]


# =============================================================================
# Pipeline builders — return a list of MongoDB aggregation stages
# =============================================================================

def build_wo_value_pipeline(
    project_id: str,
    task_external_ref_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    WO Value Aggregation Pipeline (Schema §2.1).

    Reads from `project_schedules` and does a $lookup into `work_orders`.
    Returns per-task wo_value and wo_retention_value.

    Join: work_orders.schedule_task_id  →  project_schedules.external_ref_id

    Args:
        project_id: The project to aggregate for.
        task_external_ref_ids: Optional list to restrict to specific tasks.
            If None, aggregates for all tasks in the project.

    Returns:
        MongoDB aggregation pipeline (list of stage dicts).
        Execute against the `project_schedules` collection.

    Output shape per document:
        {
            _id: ObjectId,
            external_ref_id: str,
            task_name: str,
            parent_id: ObjectId | None,
            is_summary: bool,
            wo_value: Decimal128,          # Sum of approved WO grand_total
            wo_retention_value: Decimal128, # Sum of retention_amount on approved WOs
        }
    """
    match_stage: Dict[str, Any] = {
        "$match": {
            "project_id": project_id,
            "is_active": True,
        }
    }
    if task_external_ref_ids:
        match_stage["$match"]["external_ref_id"] = {"$in": task_external_ref_ids}

    pipeline: List[Dict[str, Any]] = [
        # Stage 1: Scope to this project
        match_stage,

        # Stage 2: Project only the fields needed for the join
        {
            "$project": {
                "_id": 1,
                "external_ref_id": 1,
                "task_name": 1,
                "parent_id": 1,
                "is_summary": 1,
                "project_id": 1,
            }
        },

        # Stage 3: Join to work_orders via external_ref_id
        # Schema §2.1: "Join Condition: WO task_id → Scheduler external_ref_id"
        # In legacy model the field is named `schedule_task_id`
        {
            "$lookup": {
                "from": "work_orders",
                "let": {"ref_id": "$external_ref_id", "proj_id": "$project_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    # Join on external_ref_id ↔ schedule_task_id
                                    {"$eq": ["$schedule_task_id", "$$ref_id"]},
                                    # Scope to same project (safety net)
                                    {"$eq": ["$project_id", "$$proj_id"]},
                                    # Only approved WOs contribute to value
                                    {"$in": ["$status", WO_APPROVED_STATUSES]},
                                ]
                            }
                        }
                    },
                    # Keep only the financial fields — minimise data transfer
                    {
                        "$project": {
                            "_id": 0,
                            "grand_total": 1,
                            "retention_amount": 1,
                        }
                    },
                ],
                "as": "_matched_wos",
            }
        },

        # Stage 4: Compute per-task WO totals from the joined array
        {
            "$addFields": {
                "wo_value": {
                    "$reduce": {
                        "input": "$_matched_wos",
                        "initialValue": {"$numberDecimal": "0"},
                        "in": {
                            "$add": [
                                "$$value",
                                {"$ifNull": ["$$this.grand_total", {"$numberDecimal": "0"}]},
                            ]
                        },
                    }
                },
                "wo_retention_value": {
                    "$reduce": {
                        "input": "$_matched_wos",
                        "initialValue": {"$numberDecimal": "0"},
                        "in": {
                            "$add": [
                                "$$value",
                                {"$ifNull": ["$$this.retention_amount", {"$numberDecimal": "0"}]},
                            ]
                        },
                    }
                },
            }
        },

        # Stage 5: Drop the raw joined array — only expose computed totals
        {
            "$project": {
                "_matched_wos": 0,
            }
        },
    ]

    return pipeline


def build_payment_value_pipeline(
    project_id: str,
    task_external_ref_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Payment Certificate Value Aggregation Pipeline (Schema §2.2).

    Reads from `project_schedules` and does a $lookup into `payment_certificates`.
    Returns per-task payment_value (sum of Approved + Paid certificates).

    Args:
        project_id: The project to aggregate for.
        task_external_ref_ids: Optional restrict to specific tasks.

    Returns:
        MongoDB aggregation pipeline.
        Execute against the `project_schedules` collection.

    Output shape per document:
        {
            _id: ObjectId,
            external_ref_id: str,
            task_name: str,
            parent_id: ObjectId | None,
            is_summary: bool,
            payment_value: Decimal128,  # Sum of Approved + Paid PC grand_total
        }
    """
    match_stage: Dict[str, Any] = {
        "$match": {
            "project_id": project_id,
            "is_active": True,
        }
    }
    if task_external_ref_ids:
        match_stage["$match"]["external_ref_id"] = {"$in": task_external_ref_ids}

    pipeline: List[Dict[str, Any]] = [
        match_stage,

        {
            "$project": {
                "_id": 1,
                "external_ref_id": 1,
                "task_name": 1,
                "parent_id": 1,
                "is_summary": 1,
                "project_id": 1,
            }
        },

        # Join to payment_certificates via external_ref_id
        {
            "$lookup": {
                "from": "payment_certificates",
                "let": {"ref_id": "$external_ref_id", "proj_id": "$project_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$schedule_task_id", "$$ref_id"]},
                                    {"$eq": ["$project_id", "$$proj_id"]},
                                    {"$in": ["$status", PC_APPROVED_STATUSES]},
                                ]
                            }
                        }
                    },
                    {
                        "$project": {
                            "_id": 0,
                            "grand_total": 1,
                        }
                    },
                ],
                "as": "_matched_pcs",
            }
        },

        {
            "$addFields": {
                "payment_value": {
                    "$reduce": {
                        "input": "$_matched_pcs",
                        "initialValue": {"$numberDecimal": "0"},
                        "in": {
                            "$add": [
                                "$$value",
                                {"$ifNull": ["$$this.grand_total", {"$numberDecimal": "0"}]},
                            ]
                        },
                    }
                },
            }
        },

        {"$project": {"_matched_pcs": 0}},
    ]

    return pipeline


def build_parent_rollup_pipeline(project_id: str) -> List[Dict[str, Any]]:
    """
    Parent Rollup Aggregation Pipeline (Schema §2.1 — "parent rollup aggregation for summary tasks").

    After computing leaf-task wo_value and payment_value, this pipeline
    rolls up those values to parent/summary tasks by grouping on parent_id.

    This is a two-pass approach:
        Pass 1: build_wo_value_pipeline + build_payment_value_pipeline per leaf task
        Pass 2: this pipeline groups and sums children → parent

    Typically run AFTER the leaf-task pipelines have populated an in-memory
    task map. However, for a single-query version, this pipeline can be run
    directly against project_schedules joined to work_orders.

    Returns:
        MongoDB aggregation pipeline stages for rollup.
        Execute against the `project_schedules` collection.

    Output shape per document:
        {
            _id: ObjectId (parent task_id),
            parent_wo_value: Decimal128,          # Sum of all child wo_values
            parent_wo_retention_value: Decimal128,
            parent_payment_value: Decimal128,
        }
    """
    pipeline: List[Dict[str, Any]] = [
        {
            "$match": {
                "project_id": project_id,
                "is_active": True,
                "parent_id": {"$ne": None},  # leaf tasks only
            }
        },

        # Join WOs for leaf tasks
        {
            "$lookup": {
                "from": "work_orders",
                "let": {"ref_id": "$external_ref_id", "proj_id": "$project_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$schedule_task_id", "$$ref_id"]},
                                    {"$eq": ["$project_id", "$$proj_id"]},
                                    {"$in": ["$status", WO_APPROVED_STATUSES]},
                                ]
                            }
                        }
                    },
                    {"$project": {"_id": 0, "grand_total": 1, "retention_amount": 1}},
                ],
                "as": "_wos",
            }
        },

        # Join PCs for leaf tasks
        {
            "$lookup": {
                "from": "payment_certificates",
                "let": {"ref_id": "$external_ref_id", "proj_id": "$project_id"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$schedule_task_id", "$$ref_id"]},
                                    {"$eq": ["$project_id", "$$proj_id"]},
                                    {"$in": ["$status", PC_APPROVED_STATUSES]},
                                ]
                            }
                        }
                    },
                    {"$project": {"_id": 0, "grand_total": 1}},
                ],
                "as": "_pcs",
            }
        },

        # Compute per-leaf totals
        {
            "$addFields": {
                "_leaf_wo_value": {
                    "$reduce": {
                        "input": "$_wos",
                        "initialValue": {"$numberDecimal": "0"},
                        "in": {"$add": ["$$value", {"$ifNull": ["$$this.grand_total", {"$numberDecimal": "0"}]}]},
                    }
                },
                "_leaf_wo_retention": {
                    "$reduce": {
                        "input": "$_wos",
                        "initialValue": {"$numberDecimal": "0"},
                        "in": {"$add": ["$$value", {"$ifNull": ["$$this.retention_amount", {"$numberDecimal": "0"}]}]},
                    }
                },
                "_leaf_payment_value": {
                    "$reduce": {
                        "input": "$_pcs",
                        "initialValue": {"$numberDecimal": "0"},
                        "in": {"$add": ["$$value", {"$ifNull": ["$$this.grand_total", {"$numberDecimal": "0"}]}]},
                    }
                },
            }
        },

        # Group by parent to produce summary task totals
        {
            "$group": {
                "_id": "$parent_id",
                "parent_wo_value": {"$sum": "$_leaf_wo_value"},
                "parent_wo_retention_value": {"$sum": "$_leaf_wo_retention"},
                "parent_payment_value": {"$sum": "$_leaf_payment_value"},
                "child_count": {"$sum": 1},
            }
        },
    ]

    return pipeline


# =============================================================================
# Combined financial enrichment — used by the API layer
# =============================================================================

@dataclass
class FinancialEnrichmentRequest:
    """
    Input to get_financial_enrichment().
    Specifies which project and optionally which tasks to enrich.
    """
    project_id: str
    task_external_ref_ids: Optional[List[str]] = None  # None = all tasks


@dataclass
class TaskFinancials:
    """
    Per-task financial data returned by the enrichment service.
    Computed in-memory — NEVER persisted to project_schedules (Constitution §2.3).
    """
    external_ref_id: str
    wo_value: Decimal
    wo_retention_value: Decimal
    payment_value: Decimal

    # Computed fields (Constitution §2.3, Schema §2.3)
    cost_variance: Decimal          # wo_value - baseline_cost
    cost_variance_flag: str         # "on_budget" | "overrun" | "underrun"
    weightage_percent: Decimal      # (baseline_cost / project_total) * 100


def compute_cost_variance_flag(variance: Decimal) -> str:
    """
    Constitution §2.3: flag the direction of cost variance.
    Called per-task after computing cost_variance = wo_value - baseline_cost.
    """
    if variance > Decimal("0"):
        return "overrun"
    elif variance < Decimal("0"):
        return "underrun"
    return "on_budget"


def compute_weightage_percent(
    baseline_cost: Optional[Decimal],
    project_total_baseline_cost: Decimal,
) -> Decimal:
    """
    Schema §2.3: weightage = (task.baseline_cost / project_total_baseline_cost) * 100
    Uses the cached project_total_baseline_cost from project_metadata to avoid
    expensive re-aggregation on every request (Constitution §2.3).

    Returns 0 if baseline_cost is None or project total is 0.
    """
    if not baseline_cost or project_total_baseline_cost == Decimal("0"):
        return Decimal("0")
    return (baseline_cost / project_total_baseline_cost * Decimal("100")).quantize(Decimal("0.01"))


# =============================================================================
# Pipeline safety audit — verify no write stages are present
# =============================================================================

# Stages that would cause writes — must NEVER appear in these pipelines
_WRITE_STAGES = frozenset([
    "$out",
    "$merge",
])

# Stages that exist in our pipelines — the complete allowed set
_ALLOWED_STAGES = frozenset([
    "$match",
    "$project",
    "$lookup",
    "$addFields",
    "$group",
    "$unwind",
    "$sort",
    "$limit",
    "$skip",
    "$count",
    "$facet",
])


def assert_pipeline_is_readonly(pipeline: List[Dict[str, Any]], pipeline_name: str = "") -> None:
    """
    Verifies that an aggregation pipeline contains no write operations.
    Raises AssertionError if a write stage is found.

    Called by tests (test_financial_readonly.py) and can be called at startup
    to guard against accidental mutations (Constitution §1 absolute rule).
    """
    for i, stage in enumerate(pipeline):
        for key in stage:
            if key in _WRITE_STAGES:
                raise AssertionError(
                    f"WRITE STAGE DETECTED in pipeline '{pipeline_name}' "
                    f"at stage {i}: '{key}' is forbidden. "
                    f"PPM Scheduler has ZERO write access to legacy collections. "
                    f"(Constitution §1)"
                )
