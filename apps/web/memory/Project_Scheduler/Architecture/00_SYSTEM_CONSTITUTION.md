# System Constitution — Enterprise PPM Scheduler
**Version:** 1.0  
**Rule:** This document is included in EVERY Claude Code session. It is the supreme reference. If any implementation detail in a phase-specific document contradicts this constitution, this document wins.

---

## 1. Identity & Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Client | Next.js (App Router), React, Tailwind CSS, Zustand | Renders UI, manages optimistic state |
| Orchestrator | FastAPI (Python) | Auth, validation, financial handshake, routes to engine |
| Execution Engine | Standalone Python scripts | Deterministic CPM math, resource leveling |
| Database | MongoDB | Persistent store, ACID transactions via `bulkWrite` |
| AI Services | Gemini / LLM API (async) | Predictions, NLP extraction — never blocks main flow |

**Absolute Rule:** The PPM Scheduler has ZERO write access to legacy `work_orders` and `payment_certificates` collections. Read-only `$lookup` aggregations only.

---

## 2. System Laws (Invariants That Must Never Be Violated)

These are non-negotiable truths enforced at every layer:

### 2.1 Schedule Invariants (Post-Calculation)
- `scheduled_finish >= scheduled_start` for every task, always.
- `milestone duration == 0`. Non-milestone duration > 0. Zero-duration non-milestones are validation errors.
- No task may start before ALL its hard predecessors are satisfied.
- The critical path is continuous from project start to project finish.
- `total_slack` is mathematically consistent: `Late Start - Early Start == Late Finish - Early Finish`.
- `percent_complete` is bounded: `0 <= value <= 100`.
- Parent rollup rules are deterministic (see §4).

### 2.2 Data Integrity Invariants
- The dependency graph is a DAG. Circular dependencies are rejected BEFORE CPM runs. Validation via topological sort.
- Baseline data is immutable once locked. No API endpoint may modify `schedule_baselines` documents after `locked_at` is set. Enforced at DB middleware level.
- Soft deletes only for tasks with financial linkage (`wo_value > 0`). Hard deletes only for tasks with zero financial linkage and zero children.
- Every write to `project_schedules` increments the `version` field (optimistic locking).

### 2.3 Financial Invariants
- Financial columns (`wo_value`, `wo_retention_value`, `payment_value`, `weightage`) are NEVER persisted in `project_schedules`. They are computed at read-time via aggregation pipelines.
- Exception: `project_total_baseline_cost` is cached at project level and refreshed on baseline lock.
- Cost Variance = `wo_value - baseline_cost`. Computed in API memory, returned in response, never stored.

---

## 3. Truth Priority Hierarchy

When multiple data sources conflict, the winner is determined by this strict hierarchy (highest priority first):

```
1. Actuals (DPR / Mobile input)     — What physically happened on site
2. Manual Admin Overrides            — Explicit human decisions
3. CPM Engine Output                 — Mathematically calculated schedule
4. AI Suggestions                    — Predictions (always require confirmation)
```

**Rule:** AI never auto-commits. Every AI output (duration prediction, category suggestion, MoM extraction) passes through a human confirmation step before writing to the schedule.

---

## 4. Canonical Calculation Pipeline

When ANY schedule change occurs (drag, DPR update, Kanban move, import), the engine executes this pipeline in this EXACT order. Order is non-negotiable.

```
Step 1: INPUT VALIDATION
        → Reject circular dependencies (DAG check)
        → Reject invalid states (finish < start, negative durations)
        → Enforce task state machine transitions
        
Step 2: APPLY MANUAL OVERRIDES
        → Tasks in "Manual" mode keep user-set dates
        → Tasks in "Auto" mode proceed to CPM

Step 3: RESOLVE CONSTRAINTS
        → Apply constraint_type (ASAP, ALAP, SNET, FNLT, etc.)
        → Constraints bound the CPM output, not replace it

Step 4: RUN CPM (Forward Pass → Backward Pass)
        → Calculate Early Start / Early Finish (forward)
        → Calculate Late Start / Late Finish (backward)
        → Derive Total Slack = LS - ES
        → Flag critical path (slack == 0)

Step 5: APPLY RESOURCE LEVELING (if enabled)
        → Detect overallocations across enterprise resource pool
        → Delay lower-priority tasks per priority rules
        → Re-run affected subgraph of CPM if dates shifted

Step 6: COMPUTE DERIVED ANALYTICS
        → Parent rollups (dates, costs, weighted % complete)
        → Deadline variance = scheduled_finish - deadline
        → Deadline breach flag = (deadline_variance > 0)

Step 7: PERSIST (Atomic)
        → bulkWrite all affected tasks in single MongoDB transaction
        → Increment version on every modified document
        → If transaction fails → full rollback, return error to client

Step 8: NOTIFY CLIENT
        → Return full recalculated task set for affected subgraph
        → Client reconciles optimistic state with engine truth
        → If engine truth differs from optimistic → UI snaps to engine state
```

---

## 5. Task State Machine

Tasks follow a strict state model. Invalid transitions are rejected by the API.

```
                    ┌──────────────┐
                    │    DRAFT     │  (pre-calculation, no scheduled dates)
                    └──────┬───────┘
                           │ first CPM run
                           ▼
                    ┌──────────────┐
          ┌────────│   NOT_STARTED │◄────────────┐
          │        └──────┬───────┘              │
          │               │ actual_start set     │ reopen
          │               ▼                      │ (resets actual_finish,
          │        ┌──────────────┐              │  sets % < 100)
          │        │ IN_PROGRESS  │──────────────┘
          │        └──────┬───────┘
          │               │ % complete = 100
          │               │ AND actual_finish set
          │               ▼
          │        ┌──────────────┐
          │        │   COMPLETED  │
          │        └──────┬───────┘
          │               │ admin approval
          │               ▼
          │        ┌──────────────┐
          └───────►│    CLOSED    │  (immutable — no further edits)
                   └──────────────┘
```

**Transition Rules:**
- `NOT_STARTED → IN_PROGRESS`: requires `actual_start` date.
- `IN_PROGRESS → COMPLETED`: requires `percent_complete == 100` AND `actual_finish` date.
- `COMPLETED → IN_PROGRESS` (reopen): resets `actual_finish` to null, sets `percent_complete < 100`.
- `CLOSED`: terminal state. Task and its financials are frozen.
- `DRAFT → NOT_STARTED`: happens automatically on first successful CPM run.

---

## 6. Parent (Summary) Task Rollup Rules

| Field | Rollup Rule |
|-------|-------------|
| `scheduled_start` | `MIN(child.scheduled_start)` |
| `scheduled_finish` | `MAX(child.scheduled_finish)` |
| `scheduled_duration` | `scheduled_finish - scheduled_start` (working days) |
| `baseline_start` | `MIN(child.baseline_start)` |
| `baseline_finish` | `MAX(child.baseline_finish)` |
| `baseline_cost` | `SUM(child.baseline_cost)` |
| `percent_complete` | **Weighted by baseline_cost**: `SUM(child.percent_complete * child.baseline_cost) / SUM(child.baseline_cost)`. If all children have zero cost, fall back to simple average. |
| `actual_start` | `MIN(child.actual_start)` where not null |
| `actual_finish` | `MAX(child.actual_finish)` only if ALL children have `actual_finish` set; otherwise null |

**Summary Type:**
- `auto`: Rollup rules above are enforced. Parent fields are read-only and recalculated on every engine run.
- `manual`: Admin can override any field. System flags divergence from calculated values but does not auto-correct.

---

## 7. Data Contracts Between Layers

### 7.1 Frontend → API (Schedule Change Request)
```json
{
  "task_id": "ObjectId",
  "project_id": "ObjectId",
  "changes": {
    "scheduled_start": "ISO8601 | null",
    "scheduled_finish": "ISO8601 | null",
    "scheduled_duration": "integer | null",
    "percent_complete": "integer | null",
    "actual_start": "ISO8601 | null",
    "actual_finish": "ISO8601 | null",
    "predecessors": "Array | null",
    "assigned_resources": "Array<ObjectId> | null",
    "task_mode": "Auto | Manual | null"
  },
  "version": "integer (optimistic lock)",
  "trigger_source": "gantt_drag | kanban_drop | grid_edit | dpr_sync | import | api"
}
```

### 7.2 API → Engine (Calculation Request)
```json
{
  "project_id": "ObjectId",
  "calendar": { "work_days": [1,2,3,4,5,6], "holidays": ["ISO8601"], "shift_start": "09:00", "shift_end": "18:00" },
  "tasks": [
    {
      "task_id": "ObjectId",
      "task_mode": "Auto | Manual",
      "predecessors": [{ "task_id": "ObjectId", "project_id": "ObjectId | null", "type": "FS|SS|FF|SF", "lag_days": 0, "is_external": false, "strength": "hard|soft" }],
      "constraint_type": "ASAP | ALAP | SNET | SNLT | FNET | FNLT | MSO | MFO",
      "constraint_date": "ISO8601 | null",
      "scheduled_start": "ISO8601",
      "scheduled_finish": "ISO8601",
      "scheduled_duration": "integer (working days)",
      "actual_start": "ISO8601 | null",
      "actual_finish": "ISO8601 | null",
      "percent_complete": "integer",
      "is_milestone": "boolean",
      "deadline": "ISO8601 | null",
      "parent_id": "ObjectId | null",
      "is_summary": "boolean",
      "summary_type": "auto | manual"
    }
  ],
  "resource_calendars": [{ "resource_id": "ObjectId", "work_days": [1,2,3,4,5], "holidays": ["ISO8601"] }]
}
```

### 7.3 Engine → API (Calculation Response)
```json
{
  "project_id": "ObjectId",
  "calculation_version": "UUID",
  "calculated_at": "ISO8601",
  "status": "success | partial_failure | failure",
  "errors": [{ "task_id": "ObjectId", "error": "string" }],
  "tasks": [
    {
      "task_id": "ObjectId",
      "scheduled_start": "ISO8601",
      "scheduled_finish": "ISO8601",
      "scheduled_duration": "integer",
      "early_start": "ISO8601",
      "early_finish": "ISO8601",
      "late_start": "ISO8601",
      "late_finish": "ISO8601",
      "total_slack": "integer (days, can be negative)",
      "is_critical": "boolean",
      "deadline_variance_days": "integer | null",
      "is_deadline_breached": "boolean"
    }
  ],
  "critical_path": ["ObjectId (ordered task chain)"],
  "warnings": [{ "type": "resource_overallocation | soft_dependency_violated | constraint_conflict", "detail": "string" }]
}
```

### 7.4 API → Frontend (Full Schedule Response)
The engine response merged with financial aggregations and UI metadata:
```json
{
  "project_id": "ObjectId",
  "schedule_version": "integer",
  "calculation_version": "UUID",
  "system_state": "draft | initialized | active | locked",
  "tasks": [
    {
      "...all task fields from project_schedules...",
      "...all engine output fields...",
      "wo_value": "Decimal (aggregated, read-only)",
      "wo_retention_value": "Decimal (aggregated, read-only)",
      "payment_value": "Decimal (aggregated, read-only)",
      "weightage_percent": "Decimal (computed)",
      "cost_variance": "Decimal (computed)",
      "cost_variance_flag": "on_budget | overrun | underrun"
    }
  ]
}
```

---

## 8. Project Lifecycle States

```
DRAFT → PLANNING → ACTIVE → SUBSTANTIALLY_COMPLETE → CLOSED
```

| State | What's Allowed | What's Locked |
|-------|---------------|---------------|
| `DRAFT` | Everything editable, no CPM yet | Nothing |
| `PLANNING` | Edit tasks, run CPM, set baselines | Nothing |
| `ACTIVE` | DPR updates, schedule changes, re-baseline | Baseline 0 (original contract) |
| `SUBSTANTIALLY_COMPLETE` | Close-out tasks, final DPRs | No new tasks, no dependency changes |
| `CLOSED` | View-only | Everything |

---

## 9. Earned Value Formulas

These are the EXACT formulas the BI dashboards must use:

| Metric | Formula | Source |
|--------|---------|--------|
| **Planned Value (PV)** | `SUM(baseline_cost)` for tasks with `baseline_finish <= reporting_date` | Baseline snapshot |
| **Earned Value (EV)** | `SUM(percent_complete / 100 * baseline_cost)` for all tasks | Live schedule + baseline |
| **Actual Cost (AC)** | `SUM(wo_value)` for all tasks | Legacy WO aggregation |
| **Schedule Variance (SV)** | `EV - PV` | Computed |
| **Cost Variance (CV)** | `EV - AC` | Computed |
| **SPI** | `EV / PV` (>1 = ahead, <1 = behind) | Computed |
| **CPI** | `EV / AC` (>1 = under budget, <1 = over budget) | Computed |

**Cost Loading Strategy:** Linear distribution across task duration unless explicitly overridden. For S-Curve time-phased calculations: `daily_planned_cost = baseline_cost / scheduled_duration` spread across each working day of the task.

---

## 10. Hard System Limits

| Parameter | Limit | Behavior When Exceeded |
|-----------|-------|----------------------|
| Max tasks per project | 10,000 | API rejects creation, suggests splitting into portfolio |
| Max dependencies per task | 50 | API rejects, UI warns at 30 |
| Max concurrent users per project | 25 | Queue-based update serialization activates |
| Max baselines per project | 11 | UI disables "Lock Baseline" button |
| Max projects in portfolio view | 50 | Pagination required |
| CPM calculation timeout | 10 seconds | Returns partial result + error flag |
| API request timeout | 30 seconds | 504 with retry guidance |

---

## 11. Error Recovery Rules

| Failure | System Behavior |
|---------|----------------|
| CPM engine crashes mid-calculation | Transaction rolled back. Last valid schedule state preserved. Toast error to user. |
| API timeout during save | Frontend retains optimistic state. Retry with idempotency key. After 3 retries → rollback optimistic state, show error. |
| MongoDB transaction failure | Full rollback. No partial schedule states ever persisted. |
| AI service unavailable | All AI features degrade gracefully. Import works without auto-categorization. MoM extraction shows "AI unavailable" message. Core scheduling unaffected. |
| Financial aggregation fails | Schedule loads normally. Financial columns show "—" with refresh button. |
| Duplicate API request (same idempotency key) | Return cached response from first request. No re-execution. |

---

## 12. Security Model (RBAC)

| Role | Grid | Gantt Drag | Kanban | Baselines | Financials | AI | Admin Panel |
|------|------|-----------|--------|-----------|------------|-----|-------------|
| **Super Admin** | Full edit | Yes | Yes | Lock/unlock | View | Full | Yes |
| **Project Manager** | Full edit | Yes | Yes | Lock only | View | Full | No |
| **Supervisor** | Edit assigned tasks only | No | Move own tasks | No | No | MoM only | No |
| **Client** | View-only (filtered) | No | No | No | View (no retention) | No | No |
| **Viewer** | View-only | No | No | No | No | No | No |

**Field-Level Security:** Clients never see `wo_retention_value`, `baseline_cost`, or `cost_variance`. API strips these fields based on role before response.

---

## 13. Unit & Precision Standards

| Domain | Internal Unit | Display Unit | Precision |
|--------|--------------|-------------|-----------|
| Duration | Working days (integer) | Days | No decimals |
| Time | ISO8601 UTC | Local timezone (per project calendar) | Day-level (no hours in MVP) |
| Cost | Decimal128 (paise/cents) | ₹ / $ with 2 decimal display | 2 decimal places. Rounding: HALF_UP |
| Percentage | Integer (0-100) | `%` | No decimals |
| Slack | Integer (working days) | Days (can be negative) | No decimals |

**Rounding Propagation Rule:** Rounding happens ONLY at display layer. All intermediate calculations use full Decimal128 precision. Parent rollups use unrounded child values, then round the final parent value for display.
