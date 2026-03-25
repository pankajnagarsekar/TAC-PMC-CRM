"""
DAG Validator — Circular dependency detection via topological sort.
Stub with full interface. Implementation in Phase 2, Session 2.3.

Constitution Reference: §2.2 (DAG invariant), §4 Step 1 (input validation)
Schema Reference: §4.2 (pre-calculation validators)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum


# =============================================================================
# Data structures
# =============================================================================

@dataclass
class DependencyEdge:
    """Represents a directed edge in the task dependency graph."""
    from_task_id: str   # predecessor
    to_task_id: str     # successor


@dataclass
class DAGValidationInput:
    """
    Input contract for the DAG validator.
    Passed by the API before every CPM run (Constitution §4 Step 1).
    """
    task_ids: List[str]
    edges: List[DependencyEdge]
    project_id: str


class DAGValidationStatus(str, Enum):
    VALID   = "valid"
    INVALID = "invalid"


@dataclass
class DAGValidationResult:
    """
    Output contract for the DAG validator.
    Returned to the API layer to decide whether to proceed with CPM.
    """
    status: DAGValidationStatus
    is_valid: bool

    # Present only when status == INVALID
    # Schema §4.2: "identify the cycle path (e.g., Task A → Task B → Task C → Task A)"
    cycle_path: Optional[List[str]] = None
    error_message: Optional[str] = None

    # Topological order — valid only when is_valid == True
    # Used by the CPM engine for forward pass ordering
    topological_order: Optional[List[str]] = None

    # Orphan check results (Schema §4.2)
    orphan_task_ids: List[str] = field(default_factory=list)

    # External dependency issues
    invalid_external_refs: List[str] = field(default_factory=list)


# =============================================================================
# Interface (stub — full implementation in Phase 2, Session 2.3)
# =============================================================================

def validate_dag(input_data: DAGValidationInput) -> DAGValidationResult:
    """
    Validates that the task dependency graph is a Directed Acyclic Graph (DAG).

    Algorithm (to be implemented in Phase 2):
        Kahn's algorithm / DFS-based topological sort.
        If a cycle is detected, trace it and return the full cycle path.

    Checks performed:
        1. Cycle detection — rejects circular dependencies with clear error
           identifying the full cycle path (e.g. "A → B → C → A")
        2. Orphan check — no task references a predecessor that doesn't exist
           in task_ids
        3. Returns topological order for CPM forward pass when valid

    Args:
        input_data: DAGValidationInput with task_ids and dependency edges

    Returns:
        DAGValidationResult with is_valid flag and error details if invalid

    Raises:
        Nothing — all errors are returned in the result object, not raised.
        The API layer decides whether to abort the CPM run.

    Constitution §2.2: "The dependency graph is a DAG. Circular dependencies
    are rejected BEFORE CPM runs. Validation via topological sort."
    """
    # -------------------------------------------------------------------------
    # STUB — Phase 2 (Session 2.3) will implement full topological sort
    # -------------------------------------------------------------------------
    task_set: Set[str] = set(input_data.task_ids)
    adj: Dict[str, List[str]] = {tid: [] for tid in task_set}
    in_degree: Dict[str, int] = {tid: 0 for tid in task_set}

    orphans: List[str] = []

    for edge in input_data.edges:
        if edge.from_task_id not in task_set:
            orphans.append(edge.from_task_id)
            continue
        if edge.to_task_id not in task_set:
            orphans.append(edge.to_task_id)
            continue
        adj[edge.from_task_id].append(edge.to_task_id)
        in_degree[edge.to_task_id] += 1

    if orphans:
        return DAGValidationResult(
            status=DAGValidationStatus.INVALID,
            is_valid=False,
            error_message=f"Orphan task references found: {orphans}",
            orphan_task_ids=orphans,
        )

    # Kahn's algorithm stub — returns VALID for now (full logic in Phase 2)
    # TODO (Phase 2 Session 2.3): implement cycle detection with cycle path tracing
    return DAGValidationResult(
        status=DAGValidationStatus.VALID,
        is_valid=True,
        topological_order=list(task_set),  # placeholder — real sort in Phase 2
        orphan_task_ids=[],
    )


def format_cycle_path(cycle: List[str]) -> str:
    """
    Human-readable cycle description for error messages.
    e.g. ["A", "B", "C"] → "Task A → Task B → Task C → Task A"

    Constitution §4 Step 1 / Schema §4.2 error format.
    """
    if not cycle:
        return "(empty cycle)"
    path = " → ".join(f"Task {tid}" for tid in cycle)
    return f"{path} → Task {cycle[0]}"  # close the loop
