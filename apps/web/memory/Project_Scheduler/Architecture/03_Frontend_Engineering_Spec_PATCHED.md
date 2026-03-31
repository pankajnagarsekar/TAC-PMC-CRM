# Frontend Engineering Specification (PATCHED)
**Module:** Enterprise PPM Scheduler  
**Framework:** Next.js (App Router), React, Tailwind CSS  
**State Management:** Zustand  
**Visualization Libraries:** Recharts (BI), DhtmlxGantt or Custom Canvas/SVG (Gantt)  
**Patch Notes:** Tier 1 gap fixes marked with `[GAP-FIX]`.

---

## 1. UI/UX Architecture & Layout

The Scheduler lives as a dedicated workspace within the CRM, replacing the legacy "Payment Schedule" view.

- **Canvas Layout:** Full-bleed interface to maximize screen real estate.
- **View Toggles:** Sticky top nav switching between: `Gantt View`, `Kanban View`, `Dashboard View`, `Portfolio View`.
- **"Deep-Dive" Drawer:** Right-side sliding panel that pushes canvas left (not a modal overlay).
- **`[GAP-FIX]` System State Banner:** When `project.system_state == "draft"` (pre-first-calculation), a persistent banner reads: "Schedule not yet calculated. Define tasks and run your first calculation." Gantt/Dashboard show placeholder content until first CPM run.

---

## 2. Core Interactive Components

### 2.1. The Master Grid & Gantt Chart (`<SchedulerGrid />` & `<GanttChart />`)

**Left Pane (Master Grid):**
- Spreadsheet-like with inline editing for `task_name`, `task_mode`, `percent_complete`, `assigned_resources`, `constraint_type`.
- **Collapsible WBS:** Chevron to expand/collapse children.
- **Virtualization:** `@tanstack/react-virtual` for viewport-only rendering. Must handle 10,000 rows.
- **`[GAP-FIX]` Role-Based Column Visibility:** Columns containing `wo_retention_value`, `baseline_cost`, or `cost_variance` are hidden for Client role users. Controlled by RBAC middleware response (fields stripped server-side) AND client-side column config (defense in depth).
- **`[GAP-FIX]` Search & Filter Bar:** Above the grid. Full-text search across `task_name` and `wbs_code`. Filter dropdowns for: status, criticality, resource, category, date range. Active filters apply to ALL views simultaneously (Grid, Gantt, Kanban) via the shared Zustand store.
- **`[GAP-FIX]` Bulk Selection:** `Ctrl+Click` or checkbox column for multi-select. Bulk toolbar appears with: "Assign Resource", "Change Status", "Set Category", "Delete Selected". All bulk changes fire a single API call.

**Right Pane (Timeline/Gantt):**
- **Interactive Bars:** Drag center → changes start/finish. Drag edge → changes duration. Both fire optimistic update + debounced API call (300ms).
- **Dependency Links:** SVG lines connecting tasks. Click finish dot of Task A → drag to start dot of Task B → creates FS link. Shift+click for other types (SS, FF, SF).
- **Visual Overlays:**
  - Baseline toggle: Grey bars behind active colored bars (from `schedule_baselines` snapshot).
  - Critical Path toggle: Zero-slack bars and their SVG links turn red.
  - `[GAP-FIX]` Deadline markers: Red diamond on the date axis for tasks with deadlines. Filled red diamond if `is_deadline_breached == true`.
- **`[GAP-FIX]` Drag Guardrails:**
  - Dragging a task bar BEFORE its hard predecessor's finish → Gantt shows a red snap-back animation. The bar returns to valid position. Toast: "Cannot start before predecessor [Task Name] finishes."
  - Dragging a parent/summary task → children move proportionally (offset preserved). Warning toast if any child would violate constraints.
  - Dragging a critical path task → amber warning overlay: "This task is on the critical path. Moving it will shift the project end date."
  - All of these are optimistic UI behaviors. The engine is the final arbiter — if the optimistic position violates invariants, the engine response will correct it.
- **`[GAP-FIX]` Dependency Rendering Limits:** When more than 200 dependency lines are visible in the current viewport, show only critical path dependencies by default. Toggle button: "Show all dependencies" (with performance warning if >500).

### 2.2. The Kanban Board (`<KanbanBoard />`)
- **Columns:** Map to task states from Constitution §5: "Draft", "Not Started", "In Progress", "Completed", "Closed".
- **Drag-and-Drop:** `@hello-pangea/dnd`.
- **State Machine Enforcement:**
  - Drop to "Completed" → sets `percent_complete = 100`, `actual_finish = Date.now()`. Fires optimistic update.
  - Drop to "In Progress" from "Not Started" → sets `actual_start = Date.now()` if not already set.
  - `[GAP-FIX]` Drop to "Not Started" from "Completed" (reopen) → resets `actual_finish = null`, sets `percent_complete` to last known value before 100.
  - `[GAP-FIX]` Invalid transitions (e.g., "Draft" → "Completed") → card snaps back with toast: "Cannot move directly to Completed. Task must be In Progress first."
  - "Closed" column is drop-disabled. Tasks can only be closed via admin action in the TaskDrawer.
- **`[GAP-FIX]` Kanban Card Content:** Shows `task_name`, `assigned_resources` (avatar), `deadline` (if set, with red indicator if breached), `percent_complete` as progress bar, critical path badge (if `is_critical`).

### 2.3. The Task Deep-Dive Drawer (`<TaskDrawer />`)
Tabbed interface for granular task control:

**Tab 1: Details & Dependencies:**
- Full task edit form: name, mode, constraint_type + constraint_date, deadline, assigned_resources (multi-select), category_code.
- Dependency table: Add/remove predecessors with type selector (FS/SS/FF/SF), lag input (days, can be negative for lead), `[GAP-FIX]` hard/soft toggle.
- `[GAP-FIX]` Constraint type dropdown with conditional date picker (appears when type is not ASAP/ALAP).

**Tab 2: Interactive MoM (AI Chat):**
- Text area for meeting notes.
- Submit → AI loading state → preview of extracted Action Items.
- `[GAP-FIX]` Each extracted item shows: task name, suggested assignee, suggested deadline, confidence score badge (green >0.7, amber 0.5-0.7, red <0.5).
- `[GAP-FIX]` Per-item accept/reject buttons. "Accept All" and "Reject All" batch buttons.
- `[GAP-FIX]` Impact preview: shows WHERE in the WBS hierarchy the new tasks will be created (as children of the current task).
- Confirmed items are created in `draft` status. CPM does NOT run until admin explicitly triggers it or edits the new tasks.
- `[GAP-FIX]` If AI is unavailable: text area shows "AI extraction unavailable. You can manually create sub-tasks below." with manual task creation form.

**Tab 3: Financials (Read-Only):**
- Displays: `wo_value`, `wo_retention_value`, `payment_value`, `weightage_percent`, `cost_variance`, `cost_variance_flag` (color-coded: red=overrun, green=underrun, grey=on_budget).
- `[GAP-FIX]` Role-based: Client role does NOT see retention value or cost variance. Only sees `wo_value` and `payment_value`.
- `[GAP-FIX]` If financial aggregation fails: shows "Financial data temporarily unavailable" with retry button. Schedule data remains fully functional.

**Tab 4: Work Logs:**
- List view of timesheets and DPRs for this task.
- `[GAP-FIX]` Shows submission timestamp and source (Mobile App / Web).

**Tab 5: Audit History `[GAP-FIX — New Tab]`:**
- Chronological list of all changes to this task from `audit_log`.
- Each entry shows: timestamp, actor, action, changed fields (before → after), change source.

---

## 3. State Management & Optimistic Updates

### 3.1. The Schedule Store (`useScheduleStore`)

**Core State:**
- `taskMap`: Normalized dictionary of all tasks by `task_id` (O(1) lookups).
- `dependencyGraph`: Adjacency list of predecessor/successor relationships.
- `activeFilters`: Current search/filter state (applies to all views).
- `selectedTasks`: Set of task_ids currently selected (for bulk operations).
- `systemState`: The project's current lifecycle state (draft/planning/active/etc.).
- `[GAP-FIX]` `undoStack`: Array of previous state snapshots (max 50). Each entry contains the changed task IDs and their previous values (not full state clone).
- `[GAP-FIX]` `pendingCalculation`: Boolean. True while an API recalculation is in-flight. UI shows "calculating..." indicators on affected tasks.
- `[GAP-FIX]` `lastConfirmedVersion`: The `calculation_version` UUID from the most recent successful engine response. Used to detect stale state.

**Action: `updateTaskDate(taskId, newDates)`**
1. **`[GAP-FIX]` Push to undo stack:** Save current state of affected task(s).
2. **Optimistic UI:** Immediately update `taskMap`. Gantt bar moves instantly. Set `pendingCalculation = true`.
3. **Background Sync:** Fire `POST /api/scheduler/{project_id}/calculate` with Constitution §7.1 contract. Include `idempotency_key`.
4. **Reconciliation:** API returns Constitution §7.3 response. Store ingests the payload:
   - For each task in response: overwrite `taskMap[task_id]` with engine values.
   - If engine dates differ from optimistic → UI snaps to engine truth (no animation, instant correction).
   - Set `pendingCalculation = false`.
   - Update `lastConfirmedVersion`.
5. **Rollback:** If API fails (network error, validation failure, timeout after 3 retries):
   - Revert to pre-optimistic state from undo stack.
   - Flash Toast error with specific message from API error contract.
   - Set `pendingCalculation = false`.

**`[GAP-FIX]` Action: `undo()`**
1. Pop the most recent entry from `undoStack`.
2. Apply the previous values to `taskMap`.
3. Fire a new API request with the reverted values (so the engine confirms the undo is valid).
4. Reconcile as normal.

**`[GAP-FIX]` Action: `bulkUpdate(taskIds, changes)`**
1. Push all affected tasks to undo stack.
2. Apply changes optimistically to all selected tasks.
3. Fire single `POST /api/scheduler/{project_id}/tasks/bulk` request.
4. Reconcile as normal.

### 3.2. `[GAP-FIX]` Version Conflict Handling
If the API returns a `VERSION_CONFLICT` error (HTTP 409):
1. Store fetches the latest full schedule from `GET /api/scheduler/{project_id}/schedule`.
2. Store replaces `taskMap` entirely with the server's current state.
3. Toast: "Your change conflicted with another user's edit. The schedule has been refreshed."
4. User can re-apply their change if desired.

No merge resolution UI in MVP. Last-write-wins at the API level. The 409 prevents silent data loss.

---

## 4. Native BI Dashboards

All charts use `Recharts` and subscribe to `useScheduleStore`. They re-render automatically on any store change.

### 4.1. The S-Curve (`<SCurveChart />`)
- `<LineChart />` with two series:
  - **Planned Value (PV):** Cumulative `baseline_cost` for tasks with `baseline_finish <= date`, plotted daily. Uses linear cost loading (daily_cost = baseline_cost / duration).
  - **Earned Value (EV):** Cumulative `(percent_complete / 100) * baseline_cost` for all tasks, plotted daily.
- `[GAP-FIX]` **Actual Cost (AC):** Third series. Cumulative `wo_value` for all tasks, plotted daily.
- `[GAP-FIX]` **Baseline overlay:** When comparing against a historical baseline, the S-Curve shows that baseline's PV as a dashed line alongside the current PV.
- X-axis: project timeline. Y-axis: cumulative cost (₹).

### 4.2. Cash Flow Forecaster (`<CashFlowChart />`)
- `<BarChart />` where X-axis = future months, Y-axis = sum of `baseline_cost` for tasks scheduled to finish in those months.
- **Dynamic Re-rendering:** Dragging a task from December to January → bar instantly shifts.
- `[GAP-FIX]` **Actual vs Forecast overlay:** Bars split into: "Actual Spend" (wo_value for past months) and "Forecast" (baseline_cost for future months). Distinct colors.

### 4.3. KPI Cards (`<KPICards />`)
- `[GAP-FIX]` Cards for: SPI, CPI, Schedule Variance, Cost Variance (formulas from Constitution §9).
- Color-coded: Green (healthy), Amber (warning), Red (critical).
  - SPI/CPI: Green ≥ 0.95, Amber 0.85-0.94, Red < 0.85.
  - Variance: Green (positive or zero), Amber (negative but < 5% of total), Red (negative and ≥ 5% of total).

### 4.4. Resource Heatmap (`<ResourceHeatmap />`)
- Grid: X-axis = weeks, Y-axis = resources.
- Cell color: Green (< 80% capacity), Amber (80-100%), Red (> 100% overallocated).
- Click on a red cell → shows which tasks are causing the overallocation.

### 4.5. `[GAP-FIX]` Dashboard Empty States
| System State | Dashboard Behavior |
|-------------|-------------------|
| `draft` | All charts show skeleton/placeholder with message: "Run first calculation to populate dashboards" |
| `planning` (no baseline) | S-Curve shows EV only (no PV without baseline). CPI unavailable. |
| `active` | Full dashboards |
| Financial aggregation failed | Charts that depend on financial data show "Financial data unavailable" with retry. Schedule-only charts (e.g., critical path stats) still render. |

---

## 5. Performance Benchmarks & Edge Cases

- **Memoization:** `React.memo` on row and bar components. Change to Task 4 re-renders only Task 4, its direct parent (rollup), and its direct successors.
- **Debouncing:** Gantt drag → optimistic UI at 60fps, API call debounced at 300ms.
- **`[GAP-FIX]` Initial Load Budget:** First meaningful paint of the Grid + Gantt in under 2 seconds for 5,000 tasks (with virtualization + lazy loading of child WBS levels).
- **`[GAP-FIX]` Chart Re-render Budget:** BI dashboard re-renders in under 100ms after a store change.
- **`[GAP-FIX]` Maximum Concurrent Animations:** Limit to 50 simultaneously animating Gantt bars during a cascade recalculation. Remaining bars snap instantly to new positions.
