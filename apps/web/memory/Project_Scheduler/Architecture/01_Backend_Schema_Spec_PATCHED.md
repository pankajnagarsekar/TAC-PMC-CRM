# Backend Database Schema & Financial Integrity Specification (PATCHED)
**Module:** Enterprise PPM Scheduler  
**Database Environment:** MongoDB  
**Constraint:** Strict Read-Only relationship with legacy Financial Modules (Work Orders & Payment Certificates).  
**Patch Notes:** This document incorporates all Tier 1 gap resolutions from the gap analysis. Changes are marked with `[GAP-FIX]` tags for traceability.

---

## 1. Core Database Schema (MongoDB Collections)

### 1.1. Collection: `project_calendars`
*Purpose: Defines the constraints for the CPM engine.*

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | ObjectId, Index | |
| `work_days` | Array of Integers | e.g., `[1,2,3,4,5,6]` for Mon-Sat |
| `shift_start` | String | e.g., "09:00" |
| `shift_end` | String | e.g., "18:00" |
| `holidays` | Array of Dates | Skipped by CPM engine |
| `updated_at` | Timestamp | |

**`[GAP-FIX]` Resource-Level Calendars:**  
The project calendar is the DEFAULT. Individual resources may override it via the `enterprise_resources.calendar_override` field (see §1.2). When a task has an assigned resource with a calendar override, the CPM engine uses the resource calendar for that task's date calculations.

---

### 1.2. Collection: `enterprise_resources`
*Purpose: Global pool for Capacity Planning and AI Allocation.*

| Field | Type | Notes |
|-------|------|-------|
| `resource_id` | ObjectId, PK | |
| `type` | Enum | "Personnel", "Vendor", "Machinery" |
| `name` | String | |
| `max_capacity_per_day` | Integer | Hours |
| `cost_rate_per_hour` | Decimal128 | `[GAP-FIX]` Required for earned value accuracy |
| `cost_rate_type` | Enum | `[GAP-FIX]` "hourly", "daily", "fixed" |
| `skills` | Array of Strings | Used by AI for auto-allocation |
| `active_assignments` | Array of ObjectIds | Links to tasks across ALL projects |
| `calendar_override` | Object (Nullable) | `[GAP-FIX]` `{ work_days: [], holidays: [] }` — overrides project calendar for this resource |
| `priority_rank` | Integer | `[GAP-FIX]` Used by resource leveling to break ties. Lower = higher priority. |

---

### 1.3. Collection: `project_schedules` (The Master Grid)
*Purpose: The central node for all project activities. Every task is a document here.*

| Field | Type | Notes |
|-------|------|-------|
| **System** | | |
| `task_id` | ObjectId, PK | |
| `project_id` | ObjectId, Index | |
| `parent_id` | ObjectId, Nullable | Creates WBS hierarchy |
| `version` | Integer | Optimistic locking — incremented on every write |
| `external_ref_id` | String, Immutable | `[GAP-FIX]` Stable reference that never changes. Used for WO/PC linkage and imports. Generated once on creation, never modified. |
| `sort_index` | Float | `[GAP-FIX]` Gap-based ordering for stable WBS display. New tasks get `(prev.sort_index + next.sort_index) / 2`. |
| `created_at` | Timestamp | |
| `updated_at` | Timestamp | |
| **Identity** | | |
| `wbs_code` | String | e.g., "1.1.2". Recalculated on reorder. NOT stable — use `external_ref_id` for linkage. |
| `category_code` | String | e.g., "CIV" |
| `task_name` | String | |
| `task_mode` | Enum | "Auto", "Manual" |
| `is_milestone` | Boolean | If true, duration must == 0 |
| `is_active` | Boolean | Soft-disable for what-if toggling |
| `is_summary` | Boolean | `[GAP-FIX]` True for parent/summary tasks |
| `summary_type` | Enum, Nullable | `[GAP-FIX]` "auto" (rollup enforced) or "manual" (admin can override). Null for leaf tasks. |
| `task_status` | Enum | `[GAP-FIX]` "draft", "not_started", "in_progress", "completed", "closed". Governed by state machine (see Constitution §5). |
| **The Contract (Baseline)** | | |
| `baseline_start` | Date | |
| `baseline_finish` | Date | |
| `baseline_duration` | Integer | Working days |
| `baseline_cost` | Decimal128 | |
| `deadline` | Date, Nullable | |
| `deadline_variance_days` | Integer, Nullable | `[GAP-FIX]` `scheduled_finish - deadline` in working days. Positive = breached. |
| `is_deadline_breached` | Boolean | `[GAP-FIX]` True if `deadline_variance_days > 0`. Persisted for alerting and audit. |
| **Constraints** | | |
| `constraint_type` | Enum, Nullable | `[GAP-FIX]` "ASAP", "ALAP", "SNET" (Start No Earlier Than), "SNLT" (Start No Later Than), "FNET" (Finish No Earlier Than), "FNLT" (Finish No Later Than), "MSO" (Must Start On), "MFO" (Must Finish On). Default: "ASAP". |
| `constraint_date` | Date, Nullable | `[GAP-FIX]` Required when constraint_type is not ASAP/ALAP. |
| **Dependencies** | | |
| `predecessors` | Array of Objects | See Predecessor Schema below |
| **The Schedule (CPM Engine Driven)** | | |
| `scheduled_start` | Date | |
| `scheduled_finish` | Date | |
| `scheduled_duration` | Integer | Working days |
| `early_start` | Date | `[GAP-FIX]` Persisted from engine output |
| `early_finish` | Date | `[GAP-FIX]` Persisted from engine output |
| `late_start` | Date | `[GAP-FIX]` Persisted from engine output |
| `late_finish` | Date | `[GAP-FIX]` Persisted from engine output |
| **Execution (Live Updates)** | | |
| `actual_start` | Date, Nullable | |
| `actual_finish` | Date, Nullable | |
| `percent_complete` | Integer | 0-100, validated |
| `assigned_resources` | Array of ObjectIds | `[GAP-FIX]` Changed from single `assigned_resource_id` to array. Supports multiple workers per task. |
| **Analytics** | | |
| `total_slack` | Integer | Days. Can be negative when deadline is breached. |
| `is_critical` | Boolean | |
| `ai_status_flag` | String | |
| `ai_suggested_duration` | Integer, Nullable | `[GAP-FIX]` Stores what AI predicted. Compared against actual for feedback loop learning. |
| `ai_confidence_score` | Float, Nullable | `[GAP-FIX]` 0.0 - 1.0. Displayed to admin during AI suggestion review. |
| **Audit** | | |
| `last_change_source` | Enum | `[GAP-FIX]` "gantt_drag", "kanban_drop", "grid_edit", "dpr_sync", "import", "api", "ai_suggestion", "engine_recalc" |
| `last_change_by` | ObjectId | `[GAP-FIX]` User who triggered the change |
| `last_change_at` | Timestamp | `[GAP-FIX]` |

#### Predecessor Schema (within `predecessors` array)

```json
{
  "task_id": "ObjectId (required)",
  "project_id": "ObjectId (nullable)",       // [GAP-FIX] Null = same project. Set for cross-project deps.
  "is_external": "Boolean (default: false)",  // [GAP-FIX] True when project_id differs from current.
  "type": "FS | SS | FF | SF",
  "lag_days": "Integer (default: 0, can be negative for lead)",
  "strength": "hard | soft"                  // [GAP-FIX] Hard = engine enforces. Soft = engine warns but allows violation.
}
```

---

### 1.4. Collection: `schedule_baselines` (The Snapshots)
*Purpose: Stores up to 11 historical snapshots for Variance tracking.*

| Field | Type | Notes |
|-------|------|-------|
| `snapshot_id` | ObjectId, PK | |
| `project_id` | ObjectId | |
| `baseline_number` | Integer | 1-11 |
| `snapshot_data` | Array | All frozen task objects at time of locking |
| `financial_snapshot` | Object | `[GAP-FIX]` `{ project_total_baseline_cost, total_wo_value, total_payment_value }` captured at lock time for accurate historical S-Curve comparison |
| `locked_by` | ObjectId (User) | |
| `locked_at` | Timestamp | |
| `is_immutable` | Boolean | `[GAP-FIX]` Always `true` after creation. DB middleware rejects any update/delete operations on documents where `is_immutable == true`. |

---

### 1.5. Collection: `audit_log` `[GAP-FIX — New Collection]`
*Purpose: Tracks all changes for accountability, debugging, and compliance.*

| Field | Type | Notes |
|-------|------|-------|
| `log_id` | ObjectId, PK | |
| `project_id` | ObjectId, Index | |
| `task_id` | ObjectId, Nullable, Index | Null for project-level events |
| `action` | Enum | "task_created", "task_updated", "task_deleted", "baseline_locked", "schedule_recalculated", "dependency_added", "dependency_removed", "resource_assigned", "import_completed" |
| `actor_id` | ObjectId | User or system account |
| `actor_role` | String | Role at time of action |
| `timestamp` | Timestamp, Index | |
| `change_source` | Enum | Same as `last_change_source` |
| `before_state` | Object, Nullable | Snapshot of changed fields before modification |
| `after_state` | Object | Snapshot of changed fields after modification |
| `change_reason` | String, Nullable | `[GAP-FIX]` Optional field for admin to note WHY (delay, rework, scope change, weather, vendor issue) |
| `calculation_version` | UUID, Nullable | Links to specific engine run if change was triggered by recalculation |

**Retention:** Audit logs are retained for the lifetime of the project + 2 years. Archival to cold storage after project closure.

---

### 1.6. Collection: `project_metadata` `[GAP-FIX — New Collection]`
*Purpose: Project-level settings and cached values.*

| Field | Type | Notes |
|-------|------|-------|
| `project_id` | ObjectId, PK | |
| `project_name` | String | |
| `project_status` | Enum | "draft", "planning", "active", "substantially_complete", "closed" |
| `project_priority` | Integer | Used in resource leveling tie-breaking across projects |
| `total_baseline_cost_cache` | Decimal128 | Refreshed on baseline lock. Used for weightage calculation without full re-aggregation. |
| `last_calculation_version` | UUID | Tracks the most recent successful CPM run |
| `last_calculated_at` | Timestamp | |
| `system_state` | Enum | "draft" (pre-first-calc), "initialized" (post-first-CPM), "active" (live updates), "locked" (baseline enforced) |
| `created_at` | Timestamp | |
| `created_by` | ObjectId | |

---

## 2. Financial Integrity Specification (The "Handshake")

**ABSOLUTE RULE:** The PPM Scheduler **cannot** create, edit, or delete a Work Order (WO) or Payment Certificate (PC). It acts solely as an aggregator and consumer of this data.

### 2.1. WO & Retention Value Aggregation (Read-Only)
When the Master Grid is loaded, the backend runs a `$lookup` aggregation against the legacy `work_orders` collection.

- **Join Condition:** Matches WO `task_id` to Scheduler `external_ref_id` (using the stable immutable reference, NOT `task_id` or `wbs_code`).
- **Output Field:** `wo_value` (Sum of approved WOs for that task).
- **Output Field:** `wo_retention_value` (Sum of retention held back on those WOs).
- If task is a Parent/Summary task, the pipeline groups and sums all child `wo_values`.

### 2.2. Payment Value Aggregation (Read-Only)
Backend runs a `$lookup` against the legacy `payment_certificates` collection.

- **Join Condition:** Matches PC `task_id` to Scheduler `external_ref_id`.
- **Output Field:** `payment_value` (Sum of all 'Approved' and 'Paid' certificates).

### 2.3. The Cost Variance & Weightage Engine
Calculated in memory during the API request (not saved to DB to prevent data desync):

- **Weightage (%):** `(Task Baseline Cost / Project Total Baseline Cost Cache) * 100`
  - Uses the cached `total_baseline_cost_cache` from `project_metadata` to avoid expensive re-aggregation on every request.
- **Cost Variance:** `WO Value - Baseline Cost`
  - If Variance > 0: API appends `"overrun"` flag.
  - If Variance < 0: API appends `"underrun"` flag.
  - If Variance == 0: API appends `"on_budget"` flag.

### 2.4. Earned Value Calculations (Read-Only, In-Memory)
`[GAP-FIX]` These formulas power the BI dashboards. Calculated per API request, never persisted:

- **Planned Value (PV):** `SUM(baseline_cost)` for all tasks where `baseline_finish <= reporting_date`
- **Earned Value (EV):** `SUM(percent_complete / 100 * baseline_cost)` for all tasks
- **Actual Cost (AC):** `SUM(wo_value)` for all tasks (from WO aggregation)
- **Schedule Performance Index (SPI):** `EV / PV`
- **Cost Performance Index (CPI):** `EV / AC`
- **Cost Loading:** Linear distribution: `daily_cost = baseline_cost / scheduled_duration` across each working day of the task.

---

## 3. Concurrency & Idempotency Rules

### 3.1. Optimistic Locking
All updates to `project_schedules` use the `version` field. If two users submit changes to the same task simultaneously, the second request fails with a version conflict error (HTTP 409). Frontend must refresh and retry.

### 3.2. Transaction Blocks
The CPM engine's recalculation (Forward/Backward Pass) is executed within a single MongoDB ACID Transaction via `bulkWrite`. If the calculation fails midway, ALL date changes are rolled back. The schedule is never left in a fragmented or mathematically impossible state.

### 3.3. Idempotency Keys `[GAP-FIX]`
Every write request from the frontend includes an `idempotency_key` (UUID). The API caches the response for a given key for 5 minutes. If the same key is received again (e.g., from a network retry), the cached response is returned without re-executing the calculation.

### 3.4. Soft Delete Strategy `[GAP-FIX]`

| Condition | Delete Behavior |
|-----------|----------------|
| Task has `wo_value > 0` or linked financials | Soft delete only (`is_active = false`). Task remains in DB for financial integrity. |
| Task has children | Must delete or reassign all children first. Cascade delete only with explicit admin confirmation. |
| Task is on critical path | Warning prompt before delete. Recalculation triggered after. |
| Task has no financials, no children | Hard delete allowed. Audit log entry created. |

### 3.5. Deletion Cascade Rules `[GAP-FIX]`

When a task is deleted:
1. All predecessor references TO this task are removed from other tasks.
2. All successor references FROM this task are removed.
3. If task had children and cascade was confirmed: children are also deleted following the same rules.
4. CPM recalculation is triggered for all affected tasks.
5. Audit log records the full before-state of the deleted task and all affected dependencies.

---

## 4. Validation Rules (Enforced at API Layer) `[GAP-FIX — New Section]`

### 4.1. Pre-Save Validators
These run before any write to `project_schedules`:

- `scheduled_finish >= scheduled_start` (always)
- `is_milestone == true` implies `scheduled_duration == 0`
- `is_milestone == false` implies `scheduled_duration > 0`
- `0 <= percent_complete <= 100`
- `actual_finish >= actual_start` (when both are set)
- `task_status` transitions follow the state machine (see Constitution §5)
- `constraint_date` is required when `constraint_type` is not ASAP/ALAP

### 4.2. Pre-Calculation Validators
These run before the CPM engine executes:

- **DAG Check:** Topological sort of the dependency graph. If cycle detected, reject with error identifying the cycle path (e.g., "Circular dependency: Task A → Task B → Task C → Task A").
- **Orphan Check:** No task references a predecessor `task_id` that doesn't exist in the project.
- **External Dependency Check:** If `is_external == true`, verify the referenced `project_id` and `task_id` exist and are accessible.

### 4.3. Post-Calculation Invariant Check
After CPM runs and before persisting results:

- No task starts before all its hard predecessors are satisfied.
- No negative durations exist.
- Critical path is continuous from first task to last.
- Slack consistency: `total_slack == late_start - early_start` for every task.
- All summary task rollups are mathematically consistent with their children.

If any invariant fails, the entire calculation is rejected, the previous valid state is preserved, and the error is logged and returned to the client.

---

## 5. Index Strategy `[GAP-FIX — New Section]`

### 5.1. Primary Indexes

| Collection | Index | Type | Purpose |
|-----------|-------|------|---------|
| `project_schedules` | `{ project_id: 1, wbs_code: 1 }` | Compound | Grid queries |
| `project_schedules` | `{ project_id: 1, sort_index: 1 }` | Compound | Ordered display |
| `project_schedules` | `{ task_id: 1 }` | Single | Direct lookup |
| `project_schedules` | `{ parent_id: 1 }` | Single | Hierarchy traversal |
| `project_schedules` | `{ external_ref_id: 1 }` | Unique | Financial linkage |
| `project_schedules` | `{ project_id: 1, is_critical: 1 }` | Compound | Critical path queries |
| `project_schedules` | `{ assigned_resources: 1 }` | Multikey | Resource utilization |
| `enterprise_resources` | `{ resource_id: 1 }` | Single | Direct lookup |
| `schedule_baselines` | `{ project_id: 1, baseline_number: 1 }` | Compound, Unique | Baseline retrieval |
| `audit_log` | `{ project_id: 1, timestamp: -1 }` | Compound | Recent activity |
| `audit_log` | `{ task_id: 1, timestamp: -1 }` | Compound | Task history |
| `project_calendars` | `{ project_id: 1 }` | Single, Unique | Calendar lookup |
