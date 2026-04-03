# TAC-PMC-CRM — Remaining Fixes for AI Agent

> **Source:** Post-fix audit of TAC-PMC-CRM-main (8).zip  
> **Scope:** 3 partially-fixed issues + 3 newly discovered issues  
> **Total tasks in this file: 6**  
> All paths are relative to the monorepo root: `TAC-PMC-CRM-main/`

---

## HOW TO USE THIS FILE

Work through each issue **in order**. Each issue contains:
- **File path** (exact, relative to repo root)
- **Problem** (what is wrong right now)
- **Exact code to find** (copy-paste search string)
- **Exact replacement** (drop-in fix)
- **Verification** (how to confirm it worked)

Do not skip or reorder. Issues 1–3 are in Python, issues 4–6 are in TypeScript/TSX.

---

## ISSUE 1 — CPM Backward Pass: LS Fallback Conflates Early Start with Late Start

**File:** `apps/api/app/modules/scheduler/calculate_critical_path.py`  
**Severity:** Major — produces wrong slack values, misidentifies critical path tasks  
**Status:** Partially fixed. The `dur_delta` off-by-one was corrected but the fallback logic still uses `succ["es"]` as a proxy for `succ["ls"]`, which is mathematically wrong.

**Problem:**  
When the backward pass processes a predecessor task, it looks up the successor's Late Start (`ls`). If `ls` is `None` (can happen for summary task successors that haven't been fully computed yet), it falls back to `succ["es"]` — the Early Start. Early Start ≠ Late Start. Using ES as the LS fallback makes the predecessor appear to have zero or negative float, inflating the critical path.

The correct fallback is: if `ls` is None but `lf` is available, derive `ls = lf - dur_delta`. Only fall back to `final_ef` if both are None.

**Find this exact block** (lines ~346–349):

```python
                s_ls = succ["ls"] if succ["ls"] is not None else succ["es"]
                s_lf = succ["lf"] if succ["lf"] is not None else succ["ef"]
                if s_ls is None: s_ls = final_ef
                if s_lf is None: s_lf = final_ef
```

**Replace with:**

```python
                # Derive s_lf first — it's more likely to be set than s_ls
                s_lf = succ["lf"] if succ["lf"] is not None else succ["ef"]
                if s_lf is None:
                    s_lf = final_ef

                # Derive s_ls from s_lf if ls is missing — never use es as a proxy
                succ_dur_delta = timedelta(days=max(0, succ["duration"] - 1))
                if succ["ls"] is not None:
                    s_ls = succ["ls"]
                elif s_lf is not None:
                    s_ls = s_lf - succ_dur_delta
                else:
                    s_ls = final_ef
```

**Verification:**  
Create a simple 3-task linear schedule: Task A (5d) → Task B (3d) → Task C (2d).  
Total project duration should be 10 days (5+3+2, with the +1 day gaps handled by the FS +1 logic).  
Task A should have slack = 0 (it's on the critical path).  
Task B should have slack = 0.  
Task C should have slack = 0.  
If you add a parallel Task D (1d, no predecessors), Task D should have slack = 9.  
With the old bug, parallel tasks would sometimes show incorrect slack.

---

## ISSUE 2 — Gantt Drag: Pointer Event Listeners Torn Down Mid-Drag

**File:** `apps/web/src/components/scheduler/GanttChart.tsx`  
**Severity:** Major — race condition can cause `commitDrag` to fire with stale task dates  
**Status:** New issue discovered during audit.

**Problem:**  
The `useEffect` that registers `pointermove` and `pointerup` event listeners lists `taskMap` in its dependency array. Every time any CPM calculation completes (which updates `taskMap`), React tears down the old effect and registers new listeners. If a user is mid-drag when a previous calculation resolves, the active listeners are destroyed and replaced. The new `handlePointerUp` closure captures the new `taskMap` — but `taskMap` at that moment may reflect optimistic state rather than the server-confirmed state. This creates a subtle race where a rapid second drag applies its delta on top of a stale snapshot.

**Fix:**  
Remove `taskMap` from the `useEffect` dependency array. Instead, keep a ref that mirrors `taskMap` so the closure always reads the latest value without causing the effect to re-run.

**Step 1 — Add a taskMapRef** (add this immediately after the existing `dragStateRef` declaration, around line ~230):

Find:
```ts
  const dragStateRef = useRef<DragState>(null);
```

Replace with:
```ts
  const dragStateRef = useRef<DragState>(null);
  const taskMapRef = useRef(taskMap);
  useEffect(() => {
    taskMapRef.current = taskMap;
  }, [taskMap]);
```

**Step 2 — Update handlePointerUp to use the ref** (inside the existing `useEffect`, around line ~337):

Find:
```ts
      if (taskId && mode && !readOnly) {
        const task = taskMap[taskId];
        if (task) {
          commitDrag(task, mode, deltaDays);
        }
      }
```

Replace with:
```ts
      if (taskId && mode && !readOnly) {
        const task = taskMapRef.current[taskId];
        if (task) {
          commitDrag(task, mode, deltaDays);
        }
      }
```

**Step 3 — Remove taskMap from the useEffect dependency array** (last line of that useEffect):

Find:
```ts
  }, [readOnly, taskMap, commitDrag]);
```

Replace with:
```ts
  }, [readOnly, commitDrag]);
```

**Verification:**  
- Drag a task bar. The task should move to the correct new date.  
- While dragging slowly, trigger an unrelated recalculation (edit a task name in the grid). The drag should still commit to the correct date — not snap back or jump to a wrong date.  
- No TypeScript errors should appear (`taskMapRef.current` is typed as `ScheduleTaskMap`).

---

## ISSUE 3 — Gantt Bar: No Visual Feedback During Active Drag

**File:** `apps/web/src/components/scheduler/GanttChart.tsx`  
**Severity:** Minor UX — drag affordance is unclear; users can't tell if a drag registered  
**Status:** Partially fixed. `activeDragTaskId` is now correctly set (the original S-BUG #14), but the `Bar` component never receives it, so nothing changes visually while dragging.

**Fix — two parts:**

**Part A: Add `isDragging` prop to the Bar component.**

Find the Bar component props interface (around line ~33):
```ts
const Bar = memo(function Bar({
  task,
  left,
  width,
  emphasizeCritical,
  onSelect,
  onStartDrag,
}: {
  task: ScheduleTask;
  left: number;
  width: number;
  emphasizeCritical: boolean;
  onSelect: (taskId: string) => void;
  onStartDrag: (task: ScheduleTask, mode: DragMode, startX: number) => void;
}) {
  const isMilestone = Boolean(task.is_milestone || task.scheduled_duration === 0);
  const barLeft = Math.max(0, left);
  const isCriticalHighlighted = Boolean(emphasizeCritical && task.is_critical);
```

Replace with:
```ts
const Bar = memo(function Bar({
  task,
  left,
  width,
  emphasizeCritical,
  isDragging,
  onSelect,
  onStartDrag,
}: {
  task: ScheduleTask;
  left: number;
  width: number;
  emphasizeCritical: boolean;
  isDragging: boolean;
  onSelect: (taskId: string) => void;
  onStartDrag: (task: ScheduleTask, mode: DragMode, startX: number) => void;
}) {
  const isMilestone = Boolean(task.is_milestone || task.scheduled_duration === 0);
  const barLeft = Math.max(0, left);
  const isCriticalHighlighted = Boolean(emphasizeCritical && task.is_critical);
```

**Part B: Apply drag styling in the Bar's inner div.**

Find the non-milestone bar's inner div (around line ~82):
```ts
        className={`group relative h-8 rounded-xl border px-3 py-1.5 shadow-lg transition-transform duration-150 ${isCriticalHighlighted ? "border-rose-400/40 bg-rose-500/25" : "border-sky-400/30 bg-sky-500/20"}`}
```

Replace with:
```ts
        className={`group relative h-8 rounded-xl border px-3 py-1.5 shadow-lg transition-transform duration-150 cursor-grab active:cursor-grabbing ${
          isDragging
            ? "scale-[1.03] ring-2 ring-orange-400/60 shadow-orange-400/20 shadow-xl opacity-90"
            : isCriticalHighlighted
            ? "border-rose-400/40 bg-rose-500/25"
            : "border-sky-400/30 bg-sky-500/20"
        }`}
```

**Part C: Pass `isDragging` at the Bar call site** (around line ~565):

Find:
```tsx
                      <Bar
                        task={previewTask}
                        left={left}
                        width={width}
                        emphasizeCritical={highlightCritical}
                        onSelect={handleSelect}
                        onStartDrag={startDrag}
                      />
```

Replace with:
```tsx
                      <Bar
                        task={previewTask}
                        left={left}
                        width={width}
                        emphasizeCritical={highlightCritical}
                        isDragging={activeDragTaskId === task.task_id}
                        onSelect={handleSelect}
                        onStartDrag={startDrag}
                      />
```

**Verification:**  
- Click and hold the move/resize handle on a Gantt bar. The bar should show a subtle orange ring and scale up slightly.  
- Releasing the pointer should remove the ring immediately.  
- Non-dragged bars should be unaffected.

---

## ISSUE 4 — TaskDrawer: Dark-Only Styles in Deps, Financials, MoM, and Logs Tabs

**File:** `apps/web/src/components/scheduler/TaskDrawer.tsx`  
**Severity:** Major UX — multiple tab contents are invisible/unreadable in light mode  
**Status:** Listed as fixed in the bug report (S-BUGs #21, #22, #23) but the dark-only classes remain in the code.

**The pattern to fix throughout this file:**  
Every bare `text-white`, `border-white/5`, `bg-white/[0.0N]` class must get a light-mode counterpart using `dark:` prefix. Below are all specific replacements needed.

---

### 4a — Dependencies tab: empty state border (line ~304)

Find:
```tsx
                <div className="rounded-xl border border-dashed border-white/5 p-4 text-center">
```
Replace with:
```tsx
                <div className="rounded-xl border border-dashed border-slate-200 dark:border-white/5 p-4 text-center">
```

---

### 4b — Dependencies tab: predecessor row container (line ~311)

Find:
```tsx
                    className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2 text-xs text-white/80"
```
Replace with:
```tsx
                    className="rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.02] px-3 py-2 text-xs text-slate-700 dark:text-white/80"
```

---

### 4c — Dependencies tab: predecessor task_id span (line ~314)

Find:
```tsx
                      <span className="font-bold text-white tracking-widest uppercase">{dep.task_id}</span>
```
Replace with:
```tsx
                      <span className="font-bold text-slate-900 dark:text-white tracking-widest uppercase">{dep.task_id}</span>
```

---

### 4d — Dependencies tab: lag/strategy text spans (line ~320)

Find:
```tsx
                      Lag: <span className="text-white font-bold">{dep.lag_days ?? 0}</span> days, Strategy: <span className="text-white">{dep.strength ?? "hard"}</span>
```
Replace with:
```tsx
                      Lag: <span className="text-slate-900 dark:text-white font-bold">{dep.lag_days ?? 0}</span> days, Strategy: <span className="text-slate-900 dark:text-white">{dep.strength ?? "hard"}</span>
```

---

### 4e — Dependencies tab: section divider (line ~328)

Find:
```tsx
              <h5 className="text-[9px] font-black uppercase tracking-[0.25em] text-slate-500 border-b border-white/5 pb-1">Link New Predecessor</h5>
```
Replace with:
```tsx
              <h5 className="text-[9px] font-black uppercase tracking-[0.25em] text-slate-500 border-b border-slate-200 dark:border-white/5 pb-1">Link New Predecessor</h5>
```

---

### 4f — Financials tab: header row (line ~377)

Find:
```tsx
            <div className="bg-white/[0.02] p-4 border-b border-white/5 flex justify-between items-center text-pretty">
```
Replace with:
```tsx
            <div className="bg-slate-50 dark:bg-white/[0.02] p-4 border-b border-slate-200 dark:border-white/5 flex justify-between items-center text-pretty">
```

---

### 4g — Financials tab: individual metric rows (line ~394)

Find:
```tsx
                <div key={label as string} className="flex flex-col gap-1 p-3 rounded-xl border border-white/5 bg-white/[0.01] hover:bg-white/[0.03] transition-colors">
```
Replace with:
```tsx
                <div key={label as string} className="flex flex-col gap-1 p-3 rounded-xl border border-slate-200 dark:border-white/5 bg-white dark:bg-white/[0.01] hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors">
```

---

### 4h — Financials tab: metric value span (line ~399)

Find:
```tsx
                    <span className="text-sm font-black text-white italic">
```
Replace with:
```tsx
                    <span className="text-sm font-black text-slate-900 dark:text-white italic">
```

---

### 4i — Financials tab: footer note (line ~407)

Find:
```tsx
            <div className="p-4 bg-orange-500/5 border-t border-white/5 text-[10px] text-orange-400/80 italic text-pretty leading-relaxed">
```
Replace with:
```tsx
            <div className="p-4 bg-orange-500/5 border-t border-slate-200 dark:border-white/5 text-[10px] text-orange-600/80 dark:text-orange-400/80 italic text-pretty leading-relaxed">
```

---

### 4j — MoM tab: textarea (line ~430)

Find:
```tsx
                className="w-full min-h-[160px] rounded-xl border border-white/5 bg-white/[0.03] p-4 text-[11px] font-medium text-white outline-none focus:border-orange-400/40 resize-none transition-all placeholder:text-slate-700 shadow-inner"
```
Replace with:
```tsx
                className="w-full min-h-[160px] rounded-xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] p-4 text-[11px] font-medium text-slate-900 dark:text-white outline-none focus:border-orange-400/40 resize-none transition-all placeholder:text-slate-400 dark:placeholder:text-slate-700 shadow-inner"
```

---

### 4k — MoM tab: results header divider (line ~451)

Find:
```tsx
                  <div className="flex items-center justify-between border-b border-white/5 pb-1">
```
Replace with:
```tsx
                  <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/5 pb-1">
```

---

### 4l — MoM tab: action item card (line ~461)

Find:
```tsx
                      <div key={idx} className="bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                        <p className="text-white text-xs font-bold tracking-tight">{item.task_name}</p>
```
Replace with:
```tsx
                      <div key={idx} className="bg-slate-50 dark:bg-white/[0.02] border border-slate-200 dark:border-white/5 p-3 rounded-xl">
                        <p className="text-slate-900 dark:text-white text-xs font-bold tracking-tight">{item.task_name}</p>
```

---

### 4m — Logs tab: log entry row container (line ~508)

Find:
```tsx
                <div key={i} className="p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-all group">
```
Replace with:
```tsx
                <div key={i} className="p-3 rounded-xl bg-white dark:bg-white/[0.02] border border-slate-200 dark:border-white/5 hover:border-slate-300 dark:hover:border-white/10 transition-all group">
```

---

### 4n — Logs tab: Site Ops link (line ~521)

Find:
```tsx
                <Link href="/admin/site-operations?tab=attendance" className="text-[9px] font-black text-white hover:text-primary transition-colors uppercase flex items-center gap-1">
```
Replace with:
```tsx
                <Link href="/admin/site-operations?tab=attendance" className="text-[9px] font-black text-slate-900 dark:text-white hover:text-primary transition-colors uppercase flex items-center gap-1">
```

**Verification:**  
Open the TaskDrawer in light mode by selecting any task in the scheduler while the app theme is set to light. All five tabs (Task Brief, Project Network, Economics, Field Notes, Log Registry) should be fully readable — no invisible white-on-white text anywhere.

---

## ISSUE 5 — TaskDrawer Logs Tab: Still Shows Hardcoded Mock Data

**File:** `apps/web/src/components/scheduler/TaskDrawer.tsx`  
**Severity:** Major — S-BUG #10 was listed as fixed in the bug report but the mock data is still present  
**Status:** Not fixed. Lines 502–507 still render three static log entries dated `2026-03-26` to `2026-03-28`.

**Problem:**  
The logs tab renders a hardcoded array of fake entries. The fix is to fetch real data from the DPR/site-operations API for the selected task, or — if that endpoint doesn't exist yet — render a proper empty/redirect state instead of fake data.

**Find this block** (lines ~497–525):

```tsx
        <Tabs.Content value="logs" className="space-y-4 pt-2">
          <div className="rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] p-4">
            <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 mb-4">
              Operation Logs & Timesheets
            </h4>

            <div className="space-y-3">
              {[
                { date: "2026-03-28", type: "Labor", summary: "4 carpenters, 2 helpers deployed for formwork" },
                { date: "2026-03-27", type: "Material", summary: "Steel arrival confirmed per schedule" },
                { date: "2026-03-26", type: "Quality", summary: "Compaction test passed for block B1" }
              ].map((log, i) => (
                <div key={i} className="p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-all group">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[8px] font-black text-slate-500 uppercase tracking-widest">{log.date}</span>
                    <span className="text-[8px] font-bold text-orange-400 px-1.5 py-0.5 rounded bg-orange-400/10 border border-orange-400/20 uppercase">{log.type}</span>
                  </div>
                  <p className="text-[10px] text-zinc-400 font-medium group-hover:text-zinc-200 transition-colors">
                    {log.summary}
                  </p>
                </div>
              ))}

              <div className="mt-4 p-3 rounded-xl bg-indigo-500/5 border border-indigo-500/10 flex items-center justify-between">
                <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-tight">Full Registry in Site Ops</span>
                <Link href="/admin/site-operations?tab=attendance" className="text-[9px] font-black text-white hover:text-primary transition-colors uppercase flex items-center gap-1">
                  View <Activity size={10} />
                </Link>
              </div>
            </div>
          </div>
        </Tabs.Content>
```

**Replace the entire block with:**

```tsx
        <Tabs.Content value="logs" className="space-y-4 pt-2">
          <div className="rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] p-4">
            <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 mb-4">
              Operation Logs & Timesheets
            </h4>

            <div className="space-y-3">
              {/* Empty state — log data lives in Site Operations DPRs */}
              <div className="rounded-xl border border-dashed border-slate-200 dark:border-white/10 p-6 text-center space-y-2">
                <Activity size={20} className="mx-auto text-slate-300 dark:text-white/20" />
                <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">
                  No inline logs for this task
                </p>
                <p className="text-[10px] text-slate-400 dark:text-slate-600 leading-relaxed">
                  Daily progress records, labour attendance, and quality entries are captured in Site Operations DPRs and are linked to this task via its WBS code.
                </p>
              </div>

              <div className="mt-2 p-3 rounded-xl bg-indigo-500/5 border border-indigo-500/10 dark:border-indigo-500/10 flex items-center justify-between">
                <span className="text-[9px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-tight">
                  Full Registry in Site Ops
                </span>
                <Link
                  href={`/admin/site-operations?tab=attendance&task=${selectedTask.task_id}`}
                  className="text-[9px] font-black text-slate-900 dark:text-white hover:text-primary transition-colors uppercase flex items-center gap-1"
                >
                  View <Activity size={10} />
                </Link>
              </div>
            </div>
          </div>
        </Tabs.Content>
```

**Verification:**  
- Open the logs tab on any task in the scheduler. You should see the empty state with the informational message — no fake hardcoded log entries with `2026-03-XX` dates.  
- The "View" link should navigate to site operations with the task ID appended as a query param.  
- The tab should look correct in both light and dark mode.

---

## ISSUE 6 — S-BUG #4 Residual: projectStart Shifts on Full-Schedule Recalculation

**File:** `apps/web/src/store/useScheduleStore.ts`  
**Severity:** Major — affects any scenario that triggers a full-schedule recalculation (imports, task deletes, undo operations)  
**Status:** Partially fixed. Granular single-task edits now correctly use `calculateChange` (no `projectStart` sent). But the full-schedule fallback path (used for imports and task deletion) still derives `projectStart = min(all task scheduled_starts)`, which shifts every time a task is moved earlier than the current earliest task.

**Find this block** in the `executeCalculationRequest` function (the `else` branch, around lines ~87–101):

```ts
    } else {
      // Fallback: stable projectStart logic
      const toISODate = (dateStr: string | null | undefined): string | null => {
        if (!dateStr) return null;
        if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return dateStr.split("T")[0];
        const parsed = new Date(dateStr);
        return isNaN(parsed.getTime()) ? null : parsed.toISOString().split("T")[0];
      };
      const starts = tasks.map((t) => toISODate(t.scheduled_start)).filter(Boolean).sort() as string[];
      const projectStart = starts.length > 0 ? starts[0] : new Date().toISOString().split("T")[0];

      response = await schedulerApi.calculate(
        request.project_id,
        tasks,
        projectStart
      );
    }
```

**Replace with:**

```ts
    } else {
      // Full-schedule fallback (imports, task deletes, undo).
      // S-BUG #4: projectStart must be stable — use the project's own scheduled_start
      // if available, to prevent a single task drag from shifting the entire schedule.
      const toISODate = (dateStr: string | null | undefined): string | null => {
        if (!dateStr) return null;
        if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return dateStr.split("T")[0];
        const parsed = new Date(dateStr);
        return isNaN(parsed.getTime()) ? null : parsed.toISOString().split("T")[0];
      };

      // Priority: (1) explicit project start stored on the task's project,
      // (2) the earliest non-null scheduled_start across all tasks (legacy fallback).
      // The project start is stored on tasks as project.scheduled_start via the load response.
      const firstTask = tasks[0];
      const projectRecord = (firstTask as any)?.project;
      const stableStart =
        toISODate((projectRecord as any)?.scheduled_start) ||
        toISODate((firstTask as any)?.project_scheduled_start);

      let projectStart: string;
      if (stableStart) {
        projectStart = stableStart;
      } else {
        // Legacy: derive from tasks — least-bad option when project record is unavailable
        const starts = tasks
          .map((t) => toISODate(t.scheduled_start))
          .filter(Boolean)
          .sort() as string[];
        projectStart = starts.length > 0 ? starts[0] : new Date().toISOString().split("T")[0];
      }

      response = await schedulerApi.calculate(
        request.project_id,
        tasks,
        projectStart
      );
    }
```

Additionally, update `loadSchedule` in the same store to cache the project's start date on the tasks when loading, so the full-recalc path can find it. Find the `loadSchedule` action:

```ts
    loadSchedule: (response) => {
      clearPendingCalculation();
      const decoratedTasks = (response.tasks || []).map(t => ({
        ...t,
        project_id: t.project_id || response.project_id
      }));
```

Replace with:

```ts
    loadSchedule: (response) => {
      clearPendingCalculation();
      const decoratedTasks = (response.tasks || []).map(t => ({
        ...t,
        project_id: t.project_id || response.project_id,
        // S-BUG #4: Cache project's canonical start date on every task so
        // the full-recalc path can use a stable projectStart anchor
        project_scheduled_start: (response as any).project_start || t.project_scheduled_start,
      }));
```

**Verification:**  
1. Load a project with tasks starting on `2024-01-15`.  
2. Import a new task via file that has a start date of `2023-12-01` (earlier than all existing tasks).  
3. After the import recalculation, all existing tasks should remain on their original dates — only the imported task should be placed at `2023-12-01`.  
4. Previously, all tasks would have shifted because `projectStart` jumped back to `2023-12-01`.

---

## SUMMARY OF ALL CHANGES

| # | Issue | File(s) | Type |
|---|-------|---------|------|
| 1 | CPM backward pass LS fallback | `apps/api/…/calculate_critical_path.py` | Logic fix (Python) |
| 2 | Gantt pointer event race condition | `apps/web/…/GanttChart.tsx` | Race condition fix (TSX) |
| 3 | Gantt bar drag visual feedback | `apps/web/…/GanttChart.tsx` | UX fix (TSX) |
| 4 | TaskDrawer dark-only styles (14 locations) | `apps/web/…/TaskDrawer.tsx` | Theme parity (TSX) |
| 5 | TaskDrawer logs tab fake data | `apps/web/…/TaskDrawer.tsx` | Regression fix (TSX) |
| 6 | projectStart instability in full-recalc | `apps/web/…/useScheduleStore.ts` | Logic fix (TS) |

**After all fixes:** Run `pnpm build` from the monorepo root to verify no TypeScript errors. Pay particular attention to the `ScheduleTask` type — if `project_scheduled_start` is not in the type definition, either add it as an optional field in `apps/web/src/types/schedule.types.ts` or use a type assertion in the store. The recommended addition:

```ts
// In apps/web/src/types/schedule.types.ts, in the ScheduleTask interface:
project_scheduled_start?: string | null;  // Cached project anchor date for stable full-recalc
```
