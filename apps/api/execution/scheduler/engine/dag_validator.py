"""
DAG Validator — Full implementation of circular dependency detection.
Replaces the stub in validators/dag_validator.py with a production-ready
topological sort using Kahn's algorithm.

Constitution Reference: §2.2, §4 Step 1
Schema Reference: §4.2

This module runs BEFORE the CPM engine on every calculation request.
The engine MUST NOT be called if DAG validation fails.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque

from .interfaces import CalculationRequest, TaskInput


# =============================================================================
# Result types
# =============================================================================

@dataclass
class DAGResult:
    is_valid: bool
    topological_order: Optional[List[str]]   # Valid only when is_valid == True
    cycle_path: Optional[List[str]]           # Valid only when is_valid == False
    error_message: Optional[str]
    orphan_refs: List[str] = field(default_factory=list)   # predecessor IDs not in project
    invalid_externals: List[str] = field(default_factory=list)  # bad cross-project refs


# =============================================================================
# Main validator
# =============================================================================

def validate_dag(request: CalculationRequest) -> DAGResult:
    """
    Validates the task dependency graph before CPM runs.

    Checks (in order):
        1. Orphan check — no task references a predecessor that doesn't exist
        2. Cycle detection — topological sort (Kahn's algorithm)
           If cycle found: traces and returns the full cycle path
        3. Returns topological order for use by the CPM engine's forward pass

    Only considers same-project (non-external) dependencies.
    External dependencies (is_external=True) are validated separately.

    Args:
        request: Full CalculationRequest from the API

    Returns:
        DAGResult with is_valid flag, topological_order if valid,
        or cycle_path + error_message if invalid.
    """
    task_ids: Set[str] = {t.task_id for t in request.tasks}
    task_map: Dict[str, TaskInput] = {t.task_id: t for t in request.tasks}

    # ─── 1. Orphan check ──────────────────────────────────────────────────────
    orphans: List[str] = []
    for task in request.tasks:
        for pred in task.predecessors:
            if pred.is_external:
                continue  # Cross-project: validated by external dependency check
            if pred.task_id not in task_ids:
                orphans.append(pred.task_id)

    if orphans:
        return DAGResult(
            is_valid=False,
            topological_order=None,
            cycle_path=None,
            error_message=(
                f"Orphan predecessor reference(s) found: {sorted(set(orphans))}. "
                f"These task IDs do not exist in project {request.project_id}."
            ),
            orphan_refs=sorted(set(orphans)),
        )

    # ─── 2. Build adjacency lists for Kahn's algorithm ────────────────────────
    in_degree: Dict[str, int] = {tid: 0 for tid in task_ids}
    adj: Dict[str, List[str]] = defaultdict(list)  # predecessor → successors

    for task in request.tasks:
        for pred in task.predecessors:
            if pred.is_external:
                continue
            pred_id = pred.task_id
            if pred_id in task_ids:
                adj[pred_id].append(task.task_id)
                in_degree[task.task_id] += 1

    # ─── 3. Kahn's algorithm ──────────────────────────────────────────────────
    # Queue: all tasks with no incoming edges (no predecessors)
    queue: deque = deque(sorted(tid for tid, deg in in_degree.items() if deg == 0))
    topo_order: List[str] = []

    while queue:
        node = queue.popleft()
        topo_order.append(node)
        for succ in sorted(adj.get(node, [])):  # sorted for determinism
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)
                # Re-sort to maintain determinism (small overhead for correctness)
                # For large graphs, a heap would be faster but adds complexity
                queue = deque(sorted(queue))

    # ─── 4. Cycle detection ───────────────────────────────────────────────────
    if len(topo_order) == len(task_ids):
        # All tasks processed — no cycle
        return DAGResult(
            is_valid=True,
            topological_order=topo_order,
            cycle_path=None,
            error_message=None,
        )

    # Cycle exists — find and trace it
    cycle = _find_cycle(task_ids, in_degree, adj, task_map)
    cycle_str = _format_cycle(cycle)

    return DAGResult(
        is_valid=False,
        topological_order=None,
        cycle_path=cycle,
        error_message=(
            f"Circular dependency detected in project {request.project_id}: "
            f"{cycle_str}. "
            f"Fix the dependency chain before recalculating."
        ),
    )


# =============================================================================
# Cycle tracer — DFS-based, returns the cycle path
# =============================================================================

def _find_cycle(
    task_ids: Set[str],
    in_degree: Dict[str, int],
    adj: Dict[str, List[str]],
    task_map: Dict[str, TaskInput],
) -> List[str]:
    """
    Finds and returns a cycle path using DFS with coloring.
    Called only when Kahn's algorithm confirmed a cycle exists.

    Returns the cycle as an ordered list of task_ids, e.g. ["A", "B", "C"]
    where C→A closes the cycle.
    """
    # Build predecessor adjacency for reverse traversal
    # (adj has pred→succ; we need the original pred structure from task_map)
    pred_adj: Dict[str, List[str]] = {tid: [] for tid in task_ids}
    for task in task_map.values():
        for pred in task.predecessors:
            if not pred.is_external and pred.task_id in task_ids:
                pred_adj[task.task_id].append(pred.task_id)  # succ → pred (reversed)

    # DFS coloring: 0=white(unvisited), 1=gray(in-stack), 2=black(done)
    color: Dict[str, int] = {tid: 0 for tid in task_ids}
    parent: Dict[str, Optional[str]] = {tid: None for tid in task_ids}

    def dfs(node: str) -> Optional[List[str]]:
        color[node] = 1
        for succ in adj.get(node, []):
            if color[succ] == 1:
                # Found cycle — trace back
                cycle = [succ]
                cur = node
                while cur != succ:
                    cycle.append(cur)
                    cur = parent[cur]
                cycle.append(succ)
                cycle.reverse()
                return cycle
            if color[succ] == 0:
                parent[succ] = node
                result = dfs(succ)
                if result:
                    return result
        color[node] = 2
        return None

    for tid in sorted(task_ids):
        if color[tid] == 0:
            cycle = dfs(tid)
            if cycle:
                return cycle

    # Fallback — return nodes still in-degree > 0 (part of cycle by Kahn's)
    return [tid for tid, deg in in_degree.items() if deg > 0]


def _format_cycle(cycle: List[str]) -> str:
    """
    Returns human-readable cycle description.
    e.g. ["A", "B", "C"] → "Task A → Task B → Task C → Task A"
    """
    if not cycle:
        return "(unknown cycle)"
    path = " → ".join(f"Task {tid}" for tid in cycle)
    return f"{path} → Task {cycle[0]}"
