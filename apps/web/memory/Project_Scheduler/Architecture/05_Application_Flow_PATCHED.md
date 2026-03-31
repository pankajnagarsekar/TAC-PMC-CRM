# Application Flow Document (PATCHED)
**Module:** Enterprise PPM Scheduler  
**Patch Notes:** Tier 1 gap fixes marked with `[GAP-FIX]`.

---

## 1. Global Initialization Flow

1. **Project Setup:** Admin creates a new project workspace. System creates `project_metadata` with `system_state: "draft"`.
2. **Calendar Configuration:** Admin defines global working days (e.g., 6-day week), standard shift hours, and uploads Holiday Registry.
3. **Resource Pool Linking:** Project is connected to Enterprise Resource Pool. `[GAP-FIX]` Admin can set resource-level calendar overrides for resources with different schedules (e.g., a vendor working 5-day weeks on a 6-day project).
4. **`[GAP-FIX]` System State: DRAFT.** At this point, Gantt shows empty timeline. Dashboard shows "Run first calculation to populate." All schedule-derived fields (slack, critical path) show "—".

---

## 2. Task Ingestion & Baseline Flow

1. **Ingestion:** Admin imports `.mpp` / Excel WBS list or creates tasks manually.
   - **`[GAP-FIX]` Import Pipeline:** File parsed → field mapping UI → validation report. Invalid rows shown with errors. Admin fixes or excludes. Valid rows staged. Only committed on explicit confirm.
   - **`[GAP-FIX]` Each imported task receives an immutable `external_ref_id`** that never changes, even if task is reordered or WBS code changes. Used for financial linkage.
2. **AI Processing (if available):** AI agent scans imported list, suggests Category Codes and durations.
   - `[GAP-FIX]` Each suggestion includes confidence score. Low-confidence items visually flagged.
   - `[GAP-FIX]` Admin reviews all suggestions. Accept/reject per item. AI never auto-commits.
   - `[GAP-FIX]` If AI unavailable: import proceeds normally without suggestions. Zero impact on core flow.
3. **Logic Mapping:** Admin defines Predecessors (e.g., Task 4 depends on Task 2 FS + 3 days) and assigns Resources.
   - `[GAP-FIX]` Admin specifies hard vs soft for each dependency.
   - `[GAP-FIX]` Admin sets constraint_type if needed (SNET, FNLT, etc.).
   - `[GAP-FIX]` Tasks can reference predecessors in OTHER projects (cross-project dependencies with `is_external: true`).
4. **Engine Calculation:** Triggered explicitly by admin or automatically on first run.
   - **`[GAP-FIX]` Full pipeline executes in Constitution §4 order:**
     1. DAG validation (reject circular dependencies with error identifying cycle).
     2. Apply manual overrides (Manual mode tasks keep user-set dates).
     3. Resolve constraints (ASAP/ALAP/SNET/etc.).
     4. CPM Forward/Backward pass.
     5. Resource leveling (if enabled).
     6. Parent rollups (weighted % complete by baseline_cost).
     7. Deadline variance calculation.
     8. Atomic persist via bulkWrite transaction.
   - **`[GAP-FIX]` Post-calculation invariant check:** All invariants from Constitution §2.1 verified. If any fails → calculation rejected, previous state preserved, error returned.
   - **`[GAP-FIX]` System state transitions: "draft" → "initialized" on first successful CPM run.**
5. **Lock Baseline:** Admin approves schedule and clicks "Lock Baseline."
   - Baseline columns populated and frozen.
   - `[GAP-FIX]` Financial snapshot captured at lock time (total_wo_value, total_payment_value).
   - `[GAP-FIX]` Baseline document marked `is_immutable: true`. No API can modify it after this point.
   - `[GAP-FIX]` `project_total_baseline_cost` cached in `project_metadata` for efficient weightage calculation.
   - **`[GAP-FIX]` System state transitions to "active."**

---

## 3. The Daily Execution Loop (Live Sync)

1. **Mobile Input:** Site Supervisor submits DPR updating `percent_complete` and `actual_start`/`actual_finish`.
   - `[GAP-FIX]` Task state machine enforced: if `actual_start` is set and task was "not_started", it transitions to "in_progress". If `percent_complete = 100` and `actual_finish` is set, task transitions to "completed".
   - `[GAP-FIX]` Invalid transitions rejected (e.g., cannot mark "completed" without `actual_finish`).
2. **Web/Kanban Input:** Admin drags tasks across Kanban board, types MoMs into Task Panel.
   - `[GAP-FIX]` Kanban drops enforce state machine. Invalid transitions → card snaps back with toast error.
   - `[GAP-FIX]` MoM extraction: AI extracts action items → preview → admin confirms → child tasks created in "draft" status.
3. **Instant Recalculation:** Any change triggers the full Constitution §4 pipeline.
   - `[GAP-FIX]` Frontend shows optimistic update immediately. "Calculating..." indicator on affected tasks.
   - `[GAP-FIX]` Server-side backpressure: multiple changes within 300ms are collapsed into a single engine run.
   - `[GAP-FIX]` Engine response reconciles with optimistic state. If different, UI snaps to engine truth.
4. **Schedule Shift:** If task finishes early → Slack increases. If task delays beyond Slack → Critical Path shifts, subsequent dates pushed.
   - `[GAP-FIX]` Deadline variance recalculated. `is_deadline_breached` updated.
   - `[GAP-FIX]` If critical path shifts: HIGH priority notification sent to PM/Admin.
5. **`[GAP-FIX]` Audit Trail:** Every change logged to `audit_log` with: actor, timestamp, change_source, before/after state, optional change_reason.
6. **`[GAP-FIX]` Undo:** Admin can `Ctrl+Z` to undo last action. Undo fires a new API request with reverted values and triggers fresh CPM run.

---

## 4. Financial & Risk Handshake Flow (Read-Only Integration)

1. **WO/PC Trigger:** When a Work Order or Payment Certificate is approved in legacy modules, the Master Grid silently fetches new financial totals via `$lookup` aggregation.
   - `[GAP-FIX]` Financial join uses `external_ref_id` (immutable) NOT `task_id` or `wbs_code` (which can change).
   - `[GAP-FIX]` If financial aggregation fails (legacy DB issue): schedule loads normally, financial columns show "—" with retry button. Core scheduling is never blocked by financial data unavailability.
2. **Variance Check:** Engine compares "WO Value" against "Baseline Cost".
   - If WO exceeds budget → `cost_variance_flag: "overrun"`. Cell turns red.
   - `[GAP-FIX]` If budget overrun exceeds 10% of baseline_cost → HIGH priority notification to PM/Admin.
3. **Dashboard Redraw:** BI S-Curves, Cash Flow Forecasters, KPI Cards instantly redraw.
   - `[GAP-FIX]` S-Curve uses three series: PV, EV, AC (formulas from Constitution §9).
   - `[GAP-FIX]` KPI cards show SPI, CPI, Schedule Variance, Cost Variance with color-coded health indicators.
   - `[GAP-FIX]` Cash Flow chart overlays actual past spend against future forecast.

---

## 5. `[GAP-FIX]` Portfolio Management Flow

1. **Portfolio View:** Admin opens Portfolio dashboard showing summary-level data from multiple projects.
2. **Cross-Project Gantt:** Top-level milestones from all portfolio projects shown on a single timeline. External dependencies visualized as dashed lines between projects.
3. **Resource Heatmap:** Shows resource utilization across all projects. Click red cells to see conflicting task assignments.
4. **Project Priority:** Admin sets project priority (used by resource leveling to resolve cross-project conflicts).

---

## 6. `[GAP-FIX]` Project Closure Flow

1. **Substantially Complete:** Admin marks project as "substantially_complete". No new tasks can be created. No dependency changes allowed. Only task completion and final DPR updates permitted.
2. **Final Reconciliation:** System generates a closure report comparing final actuals against baseline: total schedule variance, total cost variance, SPI, CPI, list of breached deadlines.
3. **Close:** Admin marks project as "closed". All data becomes view-only. Audit log preserved for project lifetime + 2 years.

---

## 7. `[GAP-FIX]` Error & Edge Case Flows

### 7.1. Circular Dependency Attempt
**Trigger:** Admin creates a dependency that would form a cycle.
**Flow:** API runs DAG check → detects cycle → returns error with cycle path (e.g., "A → B → C → A") → Frontend shows toast with cycle path → Dependency is NOT created → Schedule unchanged.

### 7.2. Version Conflict
**Trigger:** Two users edit the same task simultaneously.
**Flow:** First save succeeds. Second save receives HTTP 409 (version conflict) → Frontend fetches latest schedule → Replaces local state → Toast: "Another user edited this task. Schedule refreshed." → User can re-apply their change.

### 7.3. Engine Timeout
**Trigger:** CPM calculation exceeds 10 second limit (very large project).
**Flow:** Engine returns `status: "failure"` with timeout error → Previous valid schedule preserved → Frontend rolls back optimistic state → Toast: "Calculation timed out. Try breaking the project into smaller sub-projects."

### 7.4. Invalid State Transition
**Trigger:** Supervisor tries to mark task "completed" without setting `actual_finish`.
**Flow:** API validator rejects → HTTP 422 with specific error → Frontend toast: "Cannot complete task without Actual Finish date." → Task state unchanged.
