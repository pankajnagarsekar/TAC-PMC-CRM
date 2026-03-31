# Implementation & Execution Plan (PATCHED)
**Module:** Enterprise PPM Scheduler  
**Timeline:** 12-Week Phased Rollout  
**Strategy:** "Parallel Build, Hard Cutover." Built in parallel to existing CRM. Legacy "Payment Schedule" deprecated at final cutover.  
**Patch Notes:** Tier 1 gap fixes marked with `[GAP-FIX]`.

---

## Phase 1: Foundation & Database Isolation (Weeks 1-2)
*Objective: Establish data models, validation layer, and read-only financial pipelines.*

### Week 1: Schema Implementation
- Create MongoDB collections: `project_calendars`, `enterprise_resources`, `project_schedules`, `schedule_baselines`.
- `[GAP-FIX]` Create new collections: `audit_log`, `project_metadata`.
- Establish indexing per Backend Schema Spec §5 (compound indexes on `project_id` + `wbs_code`, `project_id` + `sort_index`, unique on `external_ref_id`, etc.).
- `[GAP-FIX]` Implement Pydantic models with ALL validators:
  - `scheduled_finish >= scheduled_start`
  - Milestone duration == 0 enforcement
  - `percent_complete` bounded 0-100
  - Task state machine transition validation
  - Constraint type/date consistency
- `[GAP-FIX]` Implement `external_ref_id` generation (UUID, immutable after creation).
- `[GAP-FIX]` Implement `sort_index` gap-based ordering.
- `[GAP-FIX]` Implement optimistic locking (`version` field increment on every write).
- `[GAP-FIX]` Implement baseline immutability middleware (reject any update/delete on `schedule_baselines` where `is_immutable == true`).

### Week 2: The Financial "Handshake"
- Write read-only `$lookup` aggregation pipelines in FastAPI:
  - WO Value aggregation (join on `external_ref_id`, not `task_id`)
  - WO Retention Value aggregation
  - Payment Value aggregation
  - Parent/summary task rollup aggregation for financial totals
- `[GAP-FIX]` Implement `project_total_baseline_cost` cache refresh logic in `project_metadata`.
- `[GAP-FIX]` Implement earned value calculation functions (PV, EV, AC, SPI, CPI) as in-memory compute utilities.
- Unit test: verify ZERO write operations to legacy collections.
- `[GAP-FIX]` Unit test: financial aggregation graceful failure (returns null/empty when legacy DB unavailable).

---

## Phase 2: The Core Execution Engine (Weeks 3-5)
*Objective: Build the deterministic Python math engine.*

### Week 3: CPM Engine Core
- Develop `calculate_critical_path.py`.
- `[GAP-FIX]` Implement DAG validation via topological sort BEFORE any CPM math. Reject circular dependencies with cycle path in error response.
- Implement Forward Pass (Early Start / Early Finish).
- Implement Backward Pass (Late Start / Late Finish).
- Implement Holiday/Shift calendar skipping for 6-day Goa work week.
- `[GAP-FIX]` Implement resource-level calendar support (override project calendar when resource has `calendar_override`).
- `[GAP-FIX]` Implement post-calculation invariant checker:
  - No `finish < start`
  - No negative durations
  - Slack consistency (`LS - ES == LF - EF`)
  - Critical path continuity
  - All hard predecessors satisfied

### Week 4: Advanced Predecessors, Constraints & Risk Math
- Build parsers for FS, SS, FF, SF dependencies with Lead/Lag modifiers (e.g., `4FF-2d`).
- `[GAP-FIX]` Implement hard vs soft dependency handling. Hard = enforced. Soft = calculated but violations produce warnings, not errors.
- `[GAP-FIX]` Implement constraint system: ASAP, ALAP, SNET, SNLT, FNET, FNLT, MSO, MFO. Constraints modify CPM output as bounds.
- Implement Total Slack calculation.
- `[GAP-FIX]` Implement Deadline Variance calculation (`scheduled_finish - deadline`) and `is_deadline_breached` flag.
- `[GAP-FIX]` Implement parent rollup engine: `scheduled_start = MIN(children)`, `scheduled_finish = MAX(children)`, `percent_complete = weighted by baseline_cost` (Constitution §6).
- Build test cases for: all constraint types, soft dependency violations, deadline breaches, weighted rollup accuracy.

### Week 5: Resource Leveling API & Integration
- Develop `resource_capacity.py`:
  - Calculate daily loads across `enterprise_resources` pool.
  - `[GAP-FIX]` Deterministic resolution algorithm: critical path first → project priority → task priority → sort_index (FIFO).
  - `[GAP-FIX]` Support resource-level calendars.
  - `[GAP-FIX]` After leveling shifts dates → re-run affected CPM subgraph.
- Expose `/calculate` and `/baseline/lock` endpoints in FastAPI:
  - `/calculate` runs the FULL Constitution §4 pipeline in exact order.
  - Wrapped in MongoDB ACID transaction (`bulkWrite`).
  - `[GAP-FIX]` Include idempotency key handling.
  - `[GAP-FIX]` Include server-side debouncing (collapse multiple requests within 300ms).
  - `[GAP-FIX]` Include error response contract (Constitution-compliant error format).
- `[GAP-FIX]` Implement audit logging: every recalculation writes to `audit_log` with `calculation_version`, affected task IDs, and change_source.

---

## Phase 3: The Frontend Grid & Canvas (Weeks 6-8)
*Objective: Build the high-performance Next.js interface.*

### Week 6: State & The Master Grid
- Initialize the `Zustand` global schedule store (`useScheduleStore`):
  - `taskMap`, `dependencyGraph`, `activeFilters`, `selectedTasks`
  - `[GAP-FIX]` `undoStack` (max 50 entries)
  - `[GAP-FIX]` `pendingCalculation` flag
  - `[GAP-FIX]` `lastConfirmedVersion` tracking
- Implement optimistic update action (Constitution §7.1 contract).
- Implement reconciliation action (ingest §7.3 response, snap to engine truth).
- `[GAP-FIX]` Implement undo action (`Ctrl+Z`).
- `[GAP-FIX]` Implement version conflict handling (409 → full refresh).
- Build virtualized `<SchedulerGrid />` component:
  - `@tanstack/react-virtual` for 10,000-row support.
  - Inline editing for task_name, task_mode, percent_complete.
  - Collapsible WBS hierarchy.
  - `[GAP-FIX]` Role-based column visibility.
  - `[GAP-FIX]` Search bar + filter dropdowns.
  - `[GAP-FIX]` Bulk selection + bulk toolbar.

### Week 7: The Interactive Gantt Canvas
- Build `<GanttChart />` visualization layer.
- Implement drag-and-drop: bar stretching (duration) and moving (start dates).
- Link Gantt drag events to Zustand store's optimistic update action.
- Implement dependency SVG line rendering.
- Implement click-drag dependency creation (finish dot → start dot).
- `[GAP-FIX]` Implement drag guardrails:
  - Prevent drag before hard predecessor (red snap-back).
  - Warn on critical path drag (amber overlay).
  - Parent drag moves children proportionally.
- `[GAP-FIX]` Implement dependency rendering limits (>200 → show critical path only, with toggle).
- `[GAP-FIX]` Implement deadline markers (red diamonds, filled if breached).
- Implement baseline overlay (grey bars) and critical path highlight (red bars/lines).

### Week 8: Task Drawer & Kanban
- Build `<KanbanBoard />`:
  - Columns matching Constitution §5 states.
  - `@hello-pangea/dnd` drag-and-drop.
  - `[GAP-FIX]` State machine enforcement on drops (invalid transitions → snap back + toast).
- Build `<TaskDrawer />` with 5 tabs:
  - Details & Dependencies (with `[GAP-FIX]` hard/soft toggle, constraint type dropdown).
  - MoM AI Chat (stub AI call, `[GAP-FIX]` confidence scores, per-item accept/reject).
  - Financials Read-Only (`[GAP-FIX]` role-based field visibility, graceful failure).
  - Work Logs.
  - `[GAP-FIX]` Audit History (chronological change log).
- `[GAP-FIX]` Implement keyboard shortcuts (Ctrl+Z, Tab navigation, Enter, Delete, Ctrl+Click, Ctrl+Shift+C).
- `[GAP-FIX]` Verify cross-view consistency: change in Kanban instantly reflected in Grid and Gantt (single Zustand store).

---

## Phase 4: AI Integration & Enterprise PPM (Weeks 9-10)
*Objective: Inject predictive intelligence and portfolio-level features.*

### Week 9: AI Microservices
- Connect AI API (Gemini/LLM) to FastAPI backend.
- Build async worker for `.mpp`/Excel ingestion:
  - Auto-categorization + duration prediction.
  - `[GAP-FIX]` Return confidence scores per suggestion.
  - `[GAP-FIX]` Store `ai_suggested_duration` alongside final values for feedback loop.
  - `[GAP-FIX]` Validate AI output: check for duplicates, circular dependencies, resource existence.
- Build MoM parser:
  - Extract Action Items into JSON.
  - `[GAP-FIX]` Preview UI with per-item accept/reject and impact preview (where in WBS hierarchy).
  - `[GAP-FIX]` Confirmed items created in "draft" status.
- `[GAP-FIX]` Implement graceful AI degradation: all core features work without AI. Import proceeds without suggestions. MoM shows manual fallback UI.

### Week 10: Portfolio & Baselines
- Build "Master Project" Portfolio dashboard:
  - Summary tasks from multiple project IDs.
  - `[GAP-FIX]` Cross-project dependency visualization.
  - `[GAP-FIX]` Resource heatmap across portfolio.
- Implement Gantt baseline overlay UI (grey bars from `schedule_baselines` snapshots).
- `[GAP-FIX]` Implement baseline comparison engine:
  - Given two baseline numbers, compute schedule_variance_days and cost_variance_percent per task.
- `[GAP-FIX]` Complete baseline lock endpoint:
  - Captures financial snapshot at lock time.
  - Sets `is_immutable: true`.
  - Caches `project_total_baseline_cost`.
- `[GAP-FIX]` Implement notification system:
  - HIGH priority (critical path shift, deadline breach, budget overrun >10%): immediate in-app + email.
  - MEDIUM priority (resource overallocation): batched every 15 min.
  - LOW priority (task completed, DPR submitted): hourly batch or daily digest.

---

## Phase 5: Native BI & Final Cutover (Weeks 11-12)

### Week 11: Reactive Dashboards
- Build `<SCurveChart />` using Recharts:
  - PV, EV, AC series using Constitution §9 formulas exactly.
  - `[GAP-FIX]` Baseline overlay as dashed line.
- Build `<CashFlowChart />`:
  - Future months bar chart.
  - `[GAP-FIX]` Actual vs Forecast overlay.
- `[GAP-FIX]` Build `<KPICards />`: SPI, CPI, Schedule Variance, Cost Variance.
- `[GAP-FIX]` Build `<ResourceHeatmap />`: weekly resource utilization grid.
- Wire all charts to subscribe to Zustand store for instant re-rendering on Gantt manipulation.
- `[GAP-FIX]` Implement dashboard empty states per project system_state.
- `[GAP-FIX]` Implement data export: Excel (full schedule), PDF (Gantt + summary), CSV.

### Week 12: Testing & Hard Cutover
- **Stress Testing:**
  - `[GAP-FIX]` Load test with 5,000 WBS rows and 7,000 dependencies (increased from original 2k/3.5k).
  - API recalculation must complete in under 5 seconds.
  - Frontend initial paint in under 2 seconds (virtualized).
  - `[GAP-FIX]` Concurrent user test: 10 simultaneous edits resolve without data corruption.
  - `[GAP-FIX]` Edge case test suite: circular dependency attempts, all constraint types, maximum dependency depth, deadline breaches, weighted rollup accuracy, all state machine transitions.
- **`[GAP-FIX]` Validation Testing:**
  - Post-calculation invariant verification on stress test data.
  - Financial aggregation accuracy (migrated data matches legacy totals).
  - RBAC enforcement: verify Client cannot see retention values, Supervisor cannot edit unassigned tasks.
- **Migration:**
  - Run one-time script to map legacy "Payment Schedule" data to `project_schedules`.
  - `[GAP-FIX]` Generate validation report comparing legacy totals vs migrated totals for every project.
  - `[GAP-FIX]` Prepare rollback script (can revert to legacy format within 48 hours).
  - `[GAP-FIX]` Enable dual-read verification: both old and new systems serve data for 1 week, diff report catches discrepancies.
- **Launch:**
  - Update Next.js routing: deprecate old module URL, point to `/admin/scheduler`.
  - `[GAP-FIX]` Monitor: track calculation times, error rates, failed transactions for first 2 weeks post-launch.
  - `[GAP-FIX]` After 1-week verification period with no critical issues: decommission legacy module.
