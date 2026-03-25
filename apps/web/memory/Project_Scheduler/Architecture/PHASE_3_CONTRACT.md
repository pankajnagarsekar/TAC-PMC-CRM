# PHASE_3_CONTRACT.md (Frontend Grid + Canvas)

Date: 2026-03-25

This artifact documents the Phase 3 frontend contract as implemented in `apps/web/src` for the Project Scheduler page: component hierarchy, Zustand store action signatures and call-sites, Gantt interaction handling (including edge cases), and the current "living types" expectations.

References (source-of-truth order):
- `CLAUDE.md` (skill-first + verification protocol)
- `Ruflo.md` (Phase 3 directives: single store, optimistic updates, debounce, virtualization, conflict handling)
- `00_PHASE_FEEDING_MAP.md` (expected Phase 3 deliverables and behaviors)
- `00_SYSTEM_CONSTITUTION.md` (invariants, earned value formulas, limits)

## Component Hierarchy (Page -> Views)

Entry page:
- `apps/web/src/app/admin/scheduler/page.tsx` (`ProjectSchedulerPage`)

Rendered view tree (no props; all are store-connected):
- `ProjectSchedulerPage`
- `KPICards` (KPI summary)
- Main grid layout
- `SchedulerGrid` (virtualized table + inline edits)
- `GanttChart` (timeline canvas + pointer-based drag commit)
- `KanbanBoard` (status columns + HTML5 drag/drop)
- Side column
- `TaskDrawer` (selected task details + edits)
- `SCurveChart` (PV/EV chart)
- Bottom analytics
- `CashFlowChart`
- `ResourceHeatmap`

How they fit together:
- `ProjectSchedulerPage` owns fetch/import/export UI and calls store `loadSchedule(...)` after API responses.
- `SchedulerGrid`, `GanttChart`, `KanbanBoard`, and `TaskDrawer` are the editing surfaces. They all write via store `queueCalculation(...)` (except `removeTask(...)` which is local-only).
- Analytics (`KPICards`, `SCurveChart`, `CashFlowChart`, `ResourceHeatmap`) are read-only views that recompute derived UI values by subscribing to `taskMap` + `taskOrder` and normalizing to an ordered array.

## Store Contract (Zustand)

Implementation:
- `apps/web/src/store/useScheduleStore.ts`

Living types:
- `apps/web/src/types/schedule.types.ts`

Single source of truth rule:
- All scheduler views render from `useScheduleStore` state (`taskMap`, `taskOrder`, `selectedTasks`, `systemState`, flags).
- Page-level data load/import/reload hydrates the store via `loadSchedule(...)`.

### State Shape (Frontend)

From `ScheduleStoreState`:
- `taskMap: Record<string, ScheduleTask>`: normalized by `task_id`
- `taskOrder: string[]`: ordered `task_id`s (used for stable rendering)
- `dependencyGraph: Record<string, { predecessors: string[]; successors: string[] }>`: derived from each task's `predecessors`
- `activeFilters: { searchTerm?: string; column?: string; value?: string | number }` (currently unused by UI)
- `selectedTasks: Set<string>`: selection model used by grid, gantt, kanban, drawer
- `systemState: "draft" | "initialized" | "active" | "locked" | null`: used to gate edits (`locked` => read-only)
- `undoStack: UndoStackEntry[]`: capped to 50 entries
- `pendingCalculation: boolean`: UI "Recalculating" indicator
- `lastConfirmedVersion: string | null`: last engine `calculation_version`
- `calculationError: string | null`: UI error banner/toasts

### Action Signatures (Frontend)

From `ScheduleStoreState`:
```ts
loadSchedule(payload: ScheduleCalculationResponse): void
reconcileWithEngine(response: ScheduleCalculationResponse): void
queueCalculation(payload: ScheduleChangeRequest): void
createDraftTask(projectId: string): ScheduleTask
removeTask(taskId: string): void
openTask(taskId: string | null): void
rollbackToUndo(): void
undo(): void
selectTask(taskId: string): void
deselectTask(taskId: string): void
```

API mapping (current implementation):
- `loadSchedule(...)`: no API call; used after `schedulerApi.load(...)` or `schedulerApi.importMpp(...)`
- `queueCalculation(...)`: optimistic patch locally, then debounced API call to `schedulerApi.calculateChange(...)` with `Idempotency-Key` header
- `reconcileWithEngine(...)`: no API call; used after successful calculation response to snap to engine truth
- `rollbackToUndo(...)`: no API call; used after API failure to revert last optimistic entry
- `undo(...)`: immediate API call (no debounce) by sending previous values back through `calculateChange(...)`
- `removeTask(...)` and `createDraftTask(...)`: local-only mutations (no persistence yet)

Debounce semantics:
- Store uses a single global `pendingRequest` and a 300ms timer.
- Multiple `queueCalculation(...)` calls within the debounce window overwrite `pendingRequest` (last write wins).

Reconciliation semantics:
- On success: `reconcileWithEngine(response)` rebuilds `taskMap`, `taskOrder`, `dependencyGraph`, and updates `systemState` + `lastConfirmedVersion`.
- On failure: store sets `calculationError` and calls `rollbackToUndo()`.

## UI Events -> Store Actions (Call-Sites)

### ProjectSchedulerPage (`page.tsx`)

Data load and hydration:
- On project change: `schedulerApi.load(project_id)` then `loadSchedule(response)`
- Reload button: `schedulerApi.load(project_id)` then `loadSchedule(response)`
- Import `.mpp`: `schedulerApi.importMpp(project_id, formData)` then `loadSchedule(response)`

Local task creation:
- Add Task: `createDraftTask(project_id)` (local-only; shows toast)

### SchedulerGrid (`SchedulerGrid.tsx`)

Selection:
- Row click: `selectTask(taskId)` (adds to `selectedTasks`)

Inline edits (on blur or select change):
- Task name input `onBlur`: `queueCalculation({ changes: { task_name }, trigger_source: "grid_edit" })`
- Mode dropdown `onChange`: `queueCalculation({ changes: { task_mode }, trigger_source: "grid_edit" })`
- Percent complete input `onBlur`: `queueCalculation({ changes: { percent_complete }, trigger_source: "grid_edit" })`

Status change:
- Status dropdown `onChange`: uses `buildTaskStatusTransition(...)` then `queueCalculation(..., trigger_source: "kanban_drop")`

Local delete:
- Trash icon: `removeTask(taskId)` (local-only)

Read-only gating:
- When `systemState === "locked"`, editing controls are replaced with read-only text.

### GanttChart (`GanttChart.tsx`)

Selection and drawer open:
- Click row or bar: `selectTask(taskId)` then `openTask(taskId)` (note: `openTask` resets selection to a single task)

Drag interaction (pointer events):
- Pointer down on drag handle: `startDrag(task, mode, clientX)` stores drag state in a ref
- Pointer move (window listener): computes `deltaDays` as `round((clientX - startX) / TIMELINE_DAY_WIDTH)` and stores it on the ref (no rerender during drag)
- Pointer up (window listener): `commitDrag(task, mode, deltaDays)` calls `queueCalculation({ changes: { scheduled_start, scheduled_finish, scheduled_duration }, trigger_source: "gantt_drag" })`

Read-only gating:
- When `systemState === "locked"`, drag start is ignored and commit is blocked.

### KanbanBoard (`KanbanBoard.tsx`)

Selection and drawer open:
- Click card: `selectTask(taskId)` then `openTask(taskId)`

Drag/drop status transitions:
- HTML5 drag start: puts `taskId` into `dataTransfer`
- Column drop: `buildTaskStatusTransition(...)` then `queueCalculation(..., trigger_source: "kanban_drop")`

Read-only gating:
- When `systemState === "locked"`, cards are not draggable and drops do nothing.

### TaskDrawer (`TaskDrawer.tsx`)

Selection model:
- Drawer reads the first element of `selectedTasks` and resolves it in `taskMap`.
- Close button: `openTask(null)` clears selection.

Edits:
- `commit(changes)` uses `queueCalculation(..., trigger_source: "grid_edit")`
- Status transitions call `buildTaskStatusTransition(...)` then `commit(...)`
- "Add Dependency" appends a new `SchedulePredecessor` to `selectedTask.predecessors` and commits `changes: { predecessors: nextPredecessors }`

Note:
- `dependencyGraph` is rebuilt only on `loadSchedule(...)` / `reconcileWithEngine(...)`, not on optimistic predecessor edits.

## Gantt Interaction Edge Cases (Current Handling)

Task visibility:
- Tasks without `scheduled_start` and without `scheduled_finish` are filtered out and not rendered in the Gantt.
- Dragging a task with missing parsed start/finish is a no-op (commit returns early).

Date math and clamping:
- `move` drag shifts both start and finish by `deltaDays`.
- `start` drag shifts start by `deltaDays` and clamps `start <= finish`.
- `finish` drag shifts finish by `deltaDays` and clamps `finish >= start`.

Granularity:
- Drag delta is measured in whole days based on a fixed `TIMELINE_DAY_WIDTH` (26px).
- Dates are formatted as `yyyy-MM-dd` in the change payload.

Milestones:
- A milestone is treated as `is_milestone` or `scheduled_duration === 0`.
- Rendering ensures a minimum bar width of 1 day.

Optimism behavior:
- UI does not visually update during pointer move (no "live dragging" preview); the optimistic mutation happens only on pointer up when `queueCalculation(...)` runs.

Duration derivation caveat:
- `scheduled_duration` is included in the drag payload using `getTaskDurationDays(...)`.
- `getTaskDurationDays(...)` returns `task.scheduled_duration` if it is a non-negative number, even if dates changed, so the optimistic `scheduled_duration` may not match the new (start, finish) pair until the engine reconciles.

## Known Deviations (Feeding Map, RuFlo, Constitution)

From `00_PHASE_FEEDING_MAP.md` Session 3.x expectations:
- Grid virtualization uses a manual fixed-height windowing approach, not `@tanstack/react-virtual`.
- WBS hierarchy is not collapsible yet (chevron is visual only); depth is a simple `parent_id ? 1 : 0`.
- Role-based column visibility (Constitution RBAC) is not implemented.
- Gantt does not render dependency SVG lines, baseline overlay toggle, or critical path toggle.
- Gantt dragging does not show an in-flight optimistic preview while pointer moves.
- Kanban uses HTML5 drag/drop, not `@hello-pangea/dnd`.
- TaskDrawer is present and tabbed, but some panels are stubs (e.g., Work Logs).

From `Ruflo.md` Phase 3 directives:
- "Version conflict (HTTP 409) overwrites local state from server" is not implemented; errors currently rollback via `rollbackToUndo()` with a generic error message.
- The "instant UI update while dragging" directive is only satisfied after pointer up (optimistic patch + debounced API), not during pointer move.

From `00_SYSTEM_CONSTITUTION.md`:
- Percent complete is not clamped to `[0, 100]` on the frontend input; invalid values rely on backend validation + rollback.
- "Working days" semantics are not modeled in the frontend date math (calendar-day deltas are used for positioning and drag changes).
- Earned value formulas in charts are simplified and not time-phased per Constitution Section 9 (PV is bucketed by finish month; PV/EV are not cumulative and do not use reporting date cutoffs).

## Frontend Living Types Expectations (TypeScript)

The frontend types for Phase 3 live in:
- `apps/web/src/types/schedule.types.ts`

Key expectations:
- `ScheduleCalculationResponse` is the canonical payload for hydration and reconciliation (`loadSchedule`, `reconcileWithEngine`).
- `ScheduleChangeRequest` is the canonical payload for schedule edits (`queueCalculation`), with `trigger_source` in:
  - `"gantt_drag" | "kanban_drop" | "grid_edit" | "import" | "api" | "ai_suggestion"`
- `ScheduleTask` is intentionally wide and tolerant of additional engine fields (`[key: string]: unknown`).
- Date fields (`scheduled_start`, `scheduled_finish`, `baseline_start`, `baseline_finish`, `actual_start`, `actual_finish`, `deadline`) are `string | null` (expected format is ISO date `yyyy-MM-dd` at day granularity in Phase 3).
- `system_state` is modeled as `"draft" | "initialized" | "active" | "locked"` and is used by the UI as the edit gate (`locked` => read-only).

