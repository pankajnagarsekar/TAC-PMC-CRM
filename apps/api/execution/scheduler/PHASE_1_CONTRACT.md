# Phase 1 Contract: Foundation & Database

**Date:** 2026-03-25 (Retroactive Documentation)  
**Status:** COMPLETE  
**Scope:** Layer 1 (Data Persistence) + Financial Handshake Pipelines

---

## 1. MongoDB Collection Schemas

The following collections are established. All use `PyObjectId` (string-validated ObjectId) for cross-service compatibility.

### `project_schedules`
The primary storage for the Work Breakdown Structure (WBS).
- **Core Fields:** `project_id`, `wbs_code`, `external_ref_id` (Immutable Stable Key), `task_name`, `task_mode` (Auto/Manual).
- **CPM Fields:** `scheduled_start`, `scheduled_finish`, `scheduled_duration`, `total_slack`, `is_critical`.
- **Baseline Fields:** `baseline_start`, `baseline_finish`, `baseline_duration`, `baseline_cost`.
- **Logic:** Participates in `transaction_session` writes.

### `project_metadata`
Project-level configuration and state.
- **Fields:** `project_id`, `project_name`, `system_state` (draft/active/locked), `last_calculation_version`.
- **Cache:** `total_baseline_cost_cache` (Critical for weightage calculations).

### `project_calendars`
- **Fields:** `project_id`, `work_days` (default [0,1,2,3,4,5] for Goa 6-day week), `holidays` (List of dates).

### `project_audit_logs` (Added in Phase 2)
- **Fields:** `project_id`, `timestamp`, `user_id`, `action` (Enum), `changes` (Dict/Diff).

---

## 2. Financial Handshake Pipelines

These are **READ-ONLY** MongoDB aggregation pipelines. They join the Scheduler with legacy ERP collections (`work_orders`, `payment_certificates`).

### `build_wo_value_pipeline`
- **Inbound:** `project_id`, optional `task_external_ref_ids`.
- **Logic:** Joins `project_schedules.external_ref_id` with `work_orders.schedule_task_id`.
- **Outbound:** `wo_value` (Grand Total), `wo_retention_value`.

### `build_payment_value_pipeline`
- **Logic:** Joins with `payment_certificates` collection.
- **Outbound:** `payment_value` (Approved + Paid certificates total).

### `build_parent_rollup_pipeline`
- **Logic:** Recursively (or via hierarchy logic) sums child financial values up to summary tasks.
- **Constraint:** Zero writes. Validated by `assert_pipeline_is_readonly`.

---

## 3. Shared Type System (`shared_types.py`)

This is the **Living Types** file. It must be updated whenever a system invariant changes.
- **TaskStatus:** `draft`, `not_started`, `in_progress`, `completed`, `closed`.
- **ChangeSource:** `gantt_drag`, `kanban_drop`, `grid_edit`, `import`, `api`, `ai_suggestion`.
- **DependencyType:** `FS`, `SS`, `FF`, `SF`.
- **ConstraintType:** `ASAP`, `ALAP`, `SNET`, `SNLT`, `FNET`, `FNLT`, `MSO`, `MFO`.

---

## 4. Compliance & Rules
1.  **Stable Keys:** All financial joins MUST use `external_ref_id`.
2.  **Immutability:** Financial values are NEVER stored in `project_schedules`. They are computed on-the-fly.
3.  **Audit:** Every modification in Layer 2+ must trigger an audit record in Layer 1.
