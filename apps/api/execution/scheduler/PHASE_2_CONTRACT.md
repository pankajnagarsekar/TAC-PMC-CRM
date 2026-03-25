# Phase 2 Contract: Enterprise PPM Scheduler API (Hardened)

**Date:** 2026-03-25  
**Status:** COMPLETE & VERIFIED  
**Scope:** Layer 2 (Orchestration) + Layer 3 (CPM Engine) Integration

---

## 1. API Endpoint Specifications

All endpoints require valid authentication via `get_current_user` and participate in atomic MongoDB transactions.

### `POST /api/scheduler/{project_id}/calculate`
**Purpose:** Re-calculates critical path and schedule dates after a task change (drag/drop, duration edit, etc.).
- **Inbound:** `ScheduleChangeRequest` (§7.1)
- **Logic:**
    - Fetches current WBS state + Calendar.
    - Merges inbound `changes` into the target task.
    - Marks `deleted_task_ids` as `is_deleted: true`.
    - Validates DAG (circular dependency check).
    - Runs CPM Forward/Backward passes skipping inactive/deleted tasks.
    - Applies Parent Rollup logic (Children → Summary tasks).
    - Checks Invariants (scheduled_start <= scheduled_finish, etc.).
    - Persists all changes + Audit Log in single transaction.
- **Outbound:** `CalculationResponse` (§7.4)

### `POST /api/scheduler/{project_id}/baseline/lock`
**Purpose:** Snapshots current scheduled dates to immutable baseline fields.
- **Logic:**
    - Copies `scheduled_*` to `baseline_*`.
    - Refreshes `total_baseline_cost_cache` in Metadata.
    - Records `AuditAction.BASELINE_LOCKED`.
- **Outbound:** `{"status": "success", "total_baseline_cost_cache": float}`

### `GET /api/scheduler/{project_id}/financials`
**Purpose:** Fetches read-only Work Order and Payment values for the schedule grid.
- **Logic:** Runs high-performance MongoDB `$lookup` aggregation pipelines against legacy collections.
- **Outbound:** List of merged task-financial objects.

---

## 2. Hardened Invariants & Behavioral Edge Cases

1.  **Optimistic Locking:** Every write increments the `version` field. Mismatch triggers `409 Conflict`.
2.  **Idempotency:** `idempotency_key` is mandatory. API caches results for 5 minutes.
3.  **WBS Stability:** `external_ref_id` is the primary key for all external joins (Work Orders). `wbs_code` is volatile and recalculated on reorder.
4.  **Deleted Tasks:** Never physically removed. Filtered via `is_deleted: true` and `is_active: false`.
5.  **Circular Dependencies:** Detected via topological sort. 400 error returned with failure path (e.g. "Task A -> Task B -> Task A").

---

## 3. Implementation Checklist for Phase 3 (Frontend)

- [ ] **Store Integration:** `useScheduleStore` must send `idempotency_key` (UUID) with every change.
- [ ] **Optimistic UI:** Grid must update immediately then reconcile with `CalculationResponse`.
- [ ] **Error Handling:** On 400/409, the UI must "snap back" the dragged bar to previous state.
- [ ] **Financials:** Poll/Fetch financials separately if required, or merge into the primary grid load.

---

## 4. Verification Proof
- **Integration Tests:** `apps/api/execution/scheduler/tests/test_api_integration.py`
- **Result:** [GREEN] 2/2 Passed.

---
**Handoff to Phase 3:** Use `execution.scheduler.models.shared_types` for all shared Enums (TaskStatus, TaskMode, DependencyType).
