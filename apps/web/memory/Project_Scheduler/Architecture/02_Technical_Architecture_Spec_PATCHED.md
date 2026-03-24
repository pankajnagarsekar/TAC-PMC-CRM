# Technical Architecture Specification (PATCHED)
**Module:** Enterprise PPM Scheduler  
**Stack Environment:** Next.js (Frontend), FastAPI/Python (Backend), MongoDB (Database)  
**Architecture Pattern:** 3-Layer Orchestration (Client UI → API Gateway/Intelligence → Deterministic Execution Engine)  
**Patch Notes:** Tier 1 gap fixes marked with `[GAP-FIX]`.

---

## 1. High-Level System Architecture

The PPM Scheduler operates on a strict separation of concerns.

- **Layer 1: The Client (Next.js/React):** Renders Gantt, Kanban, BI dashboards. Uses optimistic UI updates. Owns the "tentative UI state" — what the user sees while the engine hasn't yet confirmed.
- **Layer 2: The Orchestrator (FastAPI):** Auth, RBAC enforcement, request validation, financial aggregation, routes heavy math to Layer 3. Owns the "confirmed state" — the persisted DB truth.
- **Layer 3: The Execution Engine (Python Scripts):** Standalone deterministic scripts. Takes JSON in, returns JSON out. Zero side effects. Zero DB access. The Orchestrator handles all persistence.

### `[GAP-FIX]` UI-State vs Engine-State Separation
The system explicitly distinguishes two state domains:
- **Tentative State (Frontend):** The optimistic projection shown to the user immediately after a drag/edit. Marked visually with a subtle "calculating..." indicator on affected tasks.
- **Confirmed State (Backend):** The mathematically validated output from the engine, persisted in MongoDB. When the API response arrives, the frontend snaps from tentative to confirmed. If they differ, the confirmed state wins and the UI adjusts.

### `[GAP-FIX]` System Consistency Model
After any user action triggers a recalculation:
- The system enters `consistency_state: "pending"` for that project.
- The CPM pipeline (Constitution §4) executes.
- Upon successful persist: `consistency_state: "converged"`.
- `max_convergence_time: 10 seconds`. If convergence is not achieved within 10s, the system returns a partial result with appropriate warnings and the previous confirmed state is preserved.

---

## 2. Frontend Architecture (Next.js & React)

### 2.1. State Management
- **Global Store:** `Zustand` for `ScheduleState`.
- **Optimistic Updates:** When user drags a Kanban card to "Done", UI immediately updates to 100% and shifts Gantt bar. API call happens in background. If API fails, UI rolls back.
- **`[GAP-FIX]` Undo System:** The store maintains a stack of up to 50 previous states. `Ctrl+Z` pops the stack and restores the previous state. Undo only affects local UI state — it fires a new API request with the reverted values, which triggers a fresh CPM run. Undo is per-user, per-session (not global).

### 2.2. Visualization Libraries
- **Gantt Chart:** Virtualized rendering via `@tanstack/react-virtual` or `dhtmlxGantt`. Must handle 10,000+ tasks.
- **BI Dashboards:** `Recharts` subscribing to `ScheduleState`. Instant re-render on CPM recalc.

### 2.3. `[GAP-FIX]` Cross-View Consistency Contract
All views (Grid, Gantt, Kanban, Dashboard) read from the SAME Zustand store instance. No view maintains independent state. When the store updates (via optimistic action or API reconciliation), all mounted views re-render automatically. This guarantees that a Kanban move is instantly reflected in the Gantt chart and vice versa.

Sequence:
1. User action in ANY view → dispatches store action.
2. Store mutates immediately (optimistic).
3. ALL subscribed views re-render from same store.
4. API response arrives → store reconciles.
5. ALL views re-render again with confirmed state.

### 2.4. `[GAP-FIX]` Search, Filter & Bulk Operations
- **Search:** Full-text search across `task_name`, `wbs_code`, `category_code`. Filters the visible task list in all views simultaneously.
- **Filters:** By `task_status`, `is_critical`, `assigned_resources`, `category_code`, date ranges. Filters are additive (AND logic).
- **Bulk Operations:** Multi-select rows in Grid → bulk edit `assigned_resources`, `category_code`, `task_status`. Bulk dependency assignment via selected tasks. All bulk operations fire a single API request with an array of changes and a single CPM recalculation.

### 2.5. `[GAP-FIX]` Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+Z` | Undo last action |
| `Ctrl+S` | Force save (triggers immediate API sync) |
| `Tab` / `Shift+Tab` | Navigate grid cells |
| `Enter` | Open TaskDrawer for selected task |
| `Delete` | Delete selected task (with confirmation) |
| `Ctrl+Click` | Multi-select tasks for bulk operations |
| `Ctrl+Shift+C` | Toggle critical path highlight |

---

## 3. Backend & API Layer (FastAPI)

### 3.1. Route Structure

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/scheduler/{project_id}/calculate` | Triggers CPM Engine (full pipeline from Constitution §4) |
| `POST` | `/api/scheduler/{project_id}/baseline/lock` | Creates locked snapshot |
| `GET` | `/api/scheduler/{project_id}/financials` | Read-only financial handshake |
| `GET` | `/api/scheduler/{project_id}/schedule` | Full schedule with financial overlay (Constitution §7.4 response) |
| `PATCH` | `/api/scheduler/{project_id}/tasks/{task_id}` | Single task update (triggers recalc) |
| `POST` | `/api/scheduler/{project_id}/tasks/bulk` | `[GAP-FIX]` Bulk task update |
| `GET` | `/api/scheduler/{project_id}/audit` | `[GAP-FIX]` Audit log for project |
| `POST` | `/api/scheduler/{project_id}/import` | Import .mpp / Excel |
| `GET` | `/api/scheduler/{project_id}/export` | `[GAP-FIX]` Export to Excel/PDF |
| `GET` | `/api/portfolio/summary` | Portfolio-level aggregation |

### 3.2. Concurrency & Transaction Management
- **Atomic Updates:** CPM engine returns new dates for N dependent tasks → API uses MongoDB `bulkWrite` in a single ACID transaction. All N tasks update simultaneously.
- **`[GAP-FIX]` Backpressure & Debouncing:** If multiple recalculation requests arrive within 300ms for the same project, they are collapsed into a single engine run using the latest state. A server-side queue (in-memory per project) ensures only one CPM run executes at a time per project. Subsequent requests wait for the current run to complete, then trigger a fresh run if the state has changed.
- **`[GAP-FIX]` Idempotency:** Every mutating request includes an `idempotency_key` header. Responses cached for 5 minutes by key. Duplicate requests return cached response.

### 3.3. `[GAP-FIX]` RBAC Middleware
Every request passes through role-based access control middleware:
1. Extract user role from auth token.
2. Check route-level permission (e.g., only Admin/PM can POST /calculate).
3. Check resource-level permission (e.g., Supervisor can only PATCH tasks they are assigned to).
4. Check field-level permission (e.g., strip `wo_retention_value` and `baseline_cost` from Client responses).
5. Reject with 403 if any check fails.

Role definitions per Constitution §12.

### 3.4. `[GAP-FIX]` Error Response Contract
All API errors follow a consistent format:
```json
{
  "error": {
    "code": "CIRCULAR_DEPENDENCY | VERSION_CONFLICT | INVALID_STATE_TRANSITION | VALIDATION_FAILED | ENGINE_TIMEOUT | TRANSACTION_FAILED",
    "message": "Human-readable description",
    "details": {
      "task_id": "ObjectId (if task-specific)",
      "cycle_path": ["TaskA", "TaskB", "TaskC", "TaskA"],
      "expected_version": 5,
      "actual_version": 6,
      "invalid_fields": [{"field": "percent_complete", "value": 150, "constraint": "0-100"}]
    }
  }
}
```

---

## 4. The Execution Engine (Layer 3 — Deterministic Python)

This is the core "Math Engine." It runs independently of the web server. **It has ZERO access to the database.** It receives JSON, processes it, and returns JSON. The Orchestrator handles all I/O.

### 4.1. CPM Engine (`calculate_critical_path.py`)

**Input:** JSON matching Constitution §7.2 contract.

**Process (Constitution §4, Steps 1-6):**
1. **DAG Validation:** Topological sort. Reject cycles with error identifying the full cycle path.
2. **Constraint Resolution:** Apply constraint_type to bound date calculations.
3. **Forward Pass:** Calculate Early Start / Early Finish for every task, respecting calendars, holidays, and predecessor logic.
   - For each dependency type:
     - `FS + lag`: Successor ES = Predecessor EF + lag
     - `SS + lag`: Successor ES = Predecessor ES + lag
     - `FF + lag`: Successor EF = Predecessor EF + lag → derive ES from EF - duration
     - `SF + lag`: Successor EF = Predecessor ES + lag → derive ES from EF - duration
   - `[GAP-FIX]` Soft dependencies: calculated but violations produce warnings, not errors.
   - `[GAP-FIX]` Multiple predecessors: the LATEST (most restrictive) date wins. This is not configurable — it's how CPM works.
4. **Backward Pass:** Calculate Late Start / Late Finish.
5. **Float Calculation:** `Total Slack = LS - ES` (equivalently `LF - EF`).
6. **Critical Path:** Flag tasks where `Slack == 0`. The critical path must form a continuous chain from project start to project end.
7. **Deadline Variance:** For tasks with `deadline` set: `deadline_variance_days = scheduled_finish - deadline`. Flag `is_deadline_breached = true` if positive.

**`[GAP-FIX]` Post-Calculation Invariant Check:**
Before returning results, verify:
- No `scheduled_finish < scheduled_start`
- No negative durations
- All hard predecessors satisfied (no task starts before all hard predecessors complete, per relationship type)
- Critical path is continuous
- Slack values are self-consistent
- All milestone durations == 0

If ANY invariant fails → return `status: "failure"` with details. Do NOT return a partial invalid schedule.

**Output:** JSON matching Constitution §7.3 contract.

### 4.2. `[GAP-FIX]` Parent Rollup Engine
After CPM runs on leaf tasks, compute summary task values per Constitution §6:
- `scheduled_start = MIN(child.scheduled_start)`
- `scheduled_finish = MAX(child.scheduled_finish)`
- `percent_complete = weighted average by baseline_cost`
- Only for `summary_type == "auto"`. Manual summaries are skipped.

### 4.3. Resource Leveling Engine (`resource_capacity.py`)

**Trigger:** Runs after CPM when resource leveling is enabled, or manually via admin action, or nightly cron.

**Process:**
1. Cross-reference `enterprise_resources` pool against `project_schedules` across all active projects.
2. For each resource, for each working day: sum assigned task hours.
3. If any day exceeds `max_capacity_per_day` → overallocation detected.
4. **`[GAP-FIX]` Resolution Algorithm (Deterministic):**
   - Sort conflicting tasks by: (a) `is_critical` (critical path tasks never delayed), (b) `project_priority` (from `project_metadata`), (c) `task_priority` (lower number = higher priority), (d) `sort_index` (FIFO tiebreaker).
   - Delay the lowest-priority task to the next available slot.
   - Re-run affected subgraph of CPM to recalculate downstream dates.
   - Repeat until no overallocations remain or max iterations (100) reached.
5. **`[GAP-FIX]` Resource calendars:** If a resource has `calendar_override`, use that instead of the project calendar for tasks assigned to that resource.

---

## 5. AI & Intelligence Integration Layer

AI capabilities are integrated as **asynchronous background tasks**. They NEVER block standard UI interactions.

### 5.1. Predictive AI (Auto-Duration & Categorization)
- Triggered during `.mpp` or Excel import.
- Sends WBS task descriptions to LLM (Gemini).
- LLM cross-references historical data to output estimated working days and Category Code.
- **`[GAP-FIX]` Confidence Score:** Every AI suggestion includes a confidence score (0.0 - 1.0). Displayed to admin in the import review UI. Low-confidence suggestions (< 0.5) are visually flagged.
- **`[GAP-FIX]` Feedback Loop:** The system stores `ai_suggested_duration` alongside the final `scheduled_duration`. Over time, this data trains better predictions. Admin can view AI accuracy metrics in settings.
- **`[GAP-FIX]` Validation Layer:** AI-generated tasks are validated against:
  - Duplicate task name detection (fuzzy match)
  - Circular dependency prevention
  - Resource existence verification

### 5.2. NLP Extraction (Minutes of Meeting)
- Admin submits meeting notes into Task Drawer's MoM tab.
- Async worker passes text to LLM with strict JSON output rules.
- LLM extracts: Action Items, assignees, deadlines.
- **`[GAP-FIX]` Human Approval Workflow:**
  1. Extracted items shown in preview with diff view (what will be created).
  2. Admin can accept/reject individual items.
  3. Impact preview: shows which tasks will be created and where in the WBS.
  4. Only confirmed items are created as child tasks.
  5. All auto-created tasks start in `draft` status.

### 5.3. `[GAP-FIX]` Graceful AI Degradation
| AI Service Status | System Behavior |
|-------------------|----------------|
| Available | Full AI features (suggestions, MoM, predictions) |
| Slow (>5s response) | Show "AI processing..." with cancel button. Core features work normally. |
| Unavailable | All AI features disabled. Import proceeds without auto-categorization. MoM shows "AI unavailable, please enter tasks manually." Dashboard shows "AI insights unavailable." Zero impact on scheduling, Gantt, Kanban, or financials. |

---

## 6. `[GAP-FIX]` Notification System

### 6.1. Event Types & Delivery

| Event | Priority | Delivery | Recipients |
|-------|----------|----------|------------|
| Critical path shift | HIGH | In-app + Email | PM, Admin |
| Deadline breach | HIGH | In-app + Email | PM, Admin, assigned resource |
| Budget overrun (cost variance > 10%) | HIGH | In-app + Email | PM, Admin |
| Resource overallocation | MEDIUM | In-app | PM |
| Task completed | LOW | In-app | PM |
| DPR submitted | LOW | In-app | PM |
| AI suggestion ready | LOW | In-app | PM, Admin |

### 6.2. Batching Rules
- HIGH priority: delivered immediately.
- MEDIUM priority: batched every 15 minutes.
- LOW priority: batched every hour OR delivered in daily digest email.

---

## 7. `[GAP-FIX]` Data Loading Strategy (Backend Pagination)

### 7.1. Schedule Endpoint Response Strategy

| Project Size | Strategy |
|-------------|----------|
| ≤ 1,000 tasks | Full payload in single response |
| 1,001 - 5,000 tasks | Tree-based lazy loading: send top 2 WBS levels initially. Expand children on demand. |
| 5,001 - 10,000 tasks | Same as above + server-side filtering. Only send tasks matching current view/filter. |

### 7.2. Lazy Loading Contract
```json
// Initial load: top 2 levels
GET /api/scheduler/{project_id}/schedule?depth=2

// Expand children of specific parent
GET /api/scheduler/{project_id}/schedule?parent_id={task_id}&depth=1
```

### 7.3. `[GAP-FIX]` Cold Start Strategy
On first project load (before any CPM run):
- System state = "draft"
- Gantt shows task bars at baseline positions (if set) or at today's date (if no baseline)
- Dashboard shows empty charts with "Run first calculation to populate" message
- All schedule-derived fields (slack, critical path) show "—"

---

## 8. `[GAP-FIX]` Import & Export System

### 8.1. Import Pipeline (.mpp / Excel)
1. Parse file → extract task rows.
2. Validate: required fields present, data types correct.
3. **Partial failure handling:** If 100 tasks imported and 10 are invalid, the valid 90 are staged (not committed). Admin reviews a validation report showing: valid rows (green), invalid rows (red) with specific error per row.
4. Admin can fix invalid rows in-UI or exclude them.
5. On confirm: valid tasks are bulk-inserted, CPM runs.
6. **Field mapping:** Configurable mapping UI: source column → target field. System auto-detects common patterns (e.g., "Task Name" → `task_name`, "Duration" → `scheduled_duration`).

### 8.2. Export
- **Excel:** Full project schedule with all visible columns. Respects current filter/search.
- **PDF:** Gantt chart as rendered image + summary table.
- **CSV:** Raw data export for external tools.
