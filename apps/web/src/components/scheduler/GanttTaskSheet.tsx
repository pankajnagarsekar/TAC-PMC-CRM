"use client";

import React, { memo, useCallback, useRef, useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Columns3,
  CornerDownRight,
  CornerUpLeft,
} from "lucide-react";
import { differenceInCalendarDays } from "date-fns";

import EditableCell from "./EditableCell";
import { useColumnConfig, type GanttColumnDef } from "@/hooks/useColumnConfig";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTask, ScheduleTaskStatus, SchedulePredecessor } from "@/types/schedule.types";
import {
  formatTaskDate,
  parseTaskDate,
  getTaskStatus,
  KANBAN_META,
  VALID_STATUS_TRANSITIONS,
  ROW_HEIGHT,
} from "./scheduler-utils";

// ─── Helpers ───────────────────────────────────────────────────────

function stripHtmlTags(s: string): string {
  return s.replace(/<[^>]*>/g, "").trim();
}

function getTaskDepth(task: ScheduleTask, taskMap: Record<string, ScheduleTask>): number {
  let depth = 0;
  let current = task;
  while (current.parent_id && taskMap[current.parent_id]) {
    depth++;
    current = taskMap[current.parent_id];
  }
  return depth;
}

function formatPredecessors(predecessors?: SchedulePredecessor[]): string {
  if (!predecessors || predecessors.length === 0) return "—";
  return predecessors
    .map((p) => {
      let s = p.task_id;
      if (p.type && p.type !== "FS") s += p.type;
      if (p.lag_days && p.lag_days !== 0) {
        s += p.lag_days > 0 ? `+${p.lag_days}d` : `${p.lag_days}d`;
      }
      return s;
    })
    .join(", ");
}

function formatSuccessors(task: ScheduleTask, allTasks: Record<string, ScheduleTask>): string {
  const succs: string[] = [];
  for (const t of Object.values(allTasks)) {
    if (t.predecessors?.some((p) => p.task_id === task.task_id)) {
      succs.push(t.wbs_code || t.task_id);
    }
  }
  return succs.length > 0 ? succs.join(", ") : "—";
}

// Status options for select cells
const STATUS_OPTIONS = Object.entries(KANBAN_META).map(([value, meta]) => ({
  value,
  label: meta.label,
}));

const CONSTRAINT_OPTIONS = [
  { value: "ASAP", label: "As Soon As Possible" },
  { value: "ALAP", label: "As Late As Possible" },
  { value: "SNET", label: "Start No Earlier Than" },
  { value: "SNLT", label: "Start No Later Than" },
  { value: "FNET", label: "Finish No Earlier Than" },
  { value: "FNLT", label: "Finish No Later Than" },
  { value: "MSO", label: "Must Start On" },
  { value: "MFO", label: "Must Finish On" },
];

// ─── Task Indicator Icons ──────────────────────────────────────────

function TaskIndicatorIcons({ task }: { task: ScheduleTask; taskMap: Record<string, ScheduleTask> }) {
  const indicators: { icon: string; title: string; color: string }[] = [];

  if (task.is_critical) {
    indicators.push({ icon: "🔴", title: "Critical path task", color: "text-rose-500" });
  }
  if (task.task_mode === "Manual") {
    indicators.push({ icon: "📌", title: "Manually scheduled", color: "text-amber-500" });
  }
  if (!task.predecessors || task.predecessors.length === 0) {
    const isFirst = !task.parent_id; // Root-level tasks without predecessors are OK
    if (!isFirst && !task.is_summary) {
      indicators.push({ icon: "🔗", title: "Missing predecessor", color: "text-orange-400" });
    }
  }
  if ((!task.assignee_ids || task.assignee_ids.length === 0) && !task.is_summary && !task.is_milestone) {
    indicators.push({ icon: "👤", title: "Unassigned task", color: "text-slate-400" });
  }
  if (task.total_slack === 0 && !task.is_critical) {
    indicators.push({ icon: "⚡", title: "Zero float (near-critical)", color: "text-amber-500" });
  }

  if (indicators.length === 0) return <span className="text-slate-300 dark:text-slate-700">—</span>;

  return (
    <div className="flex items-center gap-0.5" title={indicators.map(i => i.title).join(", ")}>
      {indicators.slice(0, 3).map((ind, i) => (
        <span key={i} className="text-[10px] leading-none">{ind.icon}</span>
      ))}
    </div>
  );
}

// ─── Cell Renderer ─────────────────────────────────────────────────

const TaskSheetCell = memo(function TaskSheetCell({
  column,
  task,
  taskMap,
  rowIndex,
  readOnly,
  depth,
  isCollapsed,
  onCommit,
  onToggleCollapse,
  onIndent,
  onOutdent,
}: {
  column: GanttColumnDef;
  task: ScheduleTask;
  taskMap: Record<string, ScheduleTask>;
  rowIndex: number;
  readOnly: boolean;
  depth: number;
  isCollapsed: boolean;
  onCommit: (taskId: string, changes: Partial<ScheduleTask>) => void;
  onToggleCollapse: (taskId: string) => void;
  onIndent: (taskId: string) => void;
  onOutdent: (taskId: string) => void;
}) {
  // Row number
  if (column.id === "rownum") {
    return (
      <span className="text-[10px] font-black text-slate-400 dark:text-slate-500 tabular-nums text-center w-full block">
        {rowIndex + 1}
      </span>
    );
  }

  // WBS Code with hierarchy controls
  if (column.id === "wbs_code") {
    return (
      <span
        className="text-[10px] font-black text-slate-500 dark:text-slate-400 tracking-wider tabular-nums truncate"
        title={task.wbs_code || task.task_id}
      >
        {task.wbs_code || "—"}
      </span>
    );
  }

  // Task Name — includes indentation, expand/collapse, and indent/outdent
  if (column.id === "task_name") {
    return (
      <div className="flex items-center gap-1 min-w-0" style={{ paddingLeft: depth * 20 }}>
        {/* Expand / Collapse for summary tasks */}
        {task.is_summary ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleCollapse(task.task_id);
            }}
            className="shrink-0 h-5 w-5 flex items-center justify-center rounded hover:bg-slate-200 dark:hover:bg-white/10 text-slate-500 transition-colors"
            title={isCollapsed ? "Expand" : "Collapse"}
          >
            {isCollapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
          </button>
        ) : (
          <div className="w-5 shrink-0" /> // Spacer for alignment
        )}

        {/* Indent/Outdent buttons — visible on hover via group */}
        <div className="flex items-center gap-0.5 opacity-0 group-hover/row:opacity-100 transition-opacity shrink-0">
          {depth > 0 && (
            <button
              type="button"
              onClick={(e) => { e.stopPropagation(); onOutdent(task.task_id); }}
              className="h-4 w-4 flex items-center justify-center rounded text-slate-400 hover:text-orange-500 hover:bg-orange-500/10 transition-all"
              title="Outdent (Ctrl+Shift+I)"
            >
              <CornerUpLeft size={10} />
            </button>
          )}
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onIndent(task.task_id); }}
            className="h-4 w-4 flex items-center justify-center rounded text-slate-400 hover:text-sky-500 hover:bg-sky-500/10 transition-all"
            title="Indent (Ctrl+I)"
          >
            <CornerDownRight size={10} />
          </button>
        </div>

        {/* Task name editable */}
        <div className="flex-1 min-w-0">
          {readOnly ? (
            <span
              className={`truncate text-[11px] font-semibold ${task.is_summary ? "font-black uppercase tracking-wider text-slate-900 dark:text-white" : "text-slate-800 dark:text-slate-200"}`}
              title={task.task_name}
            >
              {task.task_name}
            </span>
          ) : (
            <EditableCell
              value={task.task_name}
              type="text"
              compact
              onCommit={(nextValue) => {
                if (typeof nextValue !== "string") return;
                const clean = stripHtmlTags(nextValue);
                if (clean) onCommit(task.task_id, { task_name: clean });
              }}
              className={task.is_summary ? "font-black uppercase tracking-wider" : ""}
            />
          )}
        </div>
      </div>
    );
  }

  // Indicators column
  if (column.id === "indicators") {
    return <TaskIndicatorIcons task={task} taskMap={taskMap} />;
  }

  // Predecessors — show formatted string
  if (column.id === "predecessors") {
    return (
      <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 truncate" title={formatPredecessors(task.predecessors)}>
        {formatPredecessors(task.predecessors)}
      </span>
    );
  }

  // Successors — derived from graph
  if (column.id === "successors") {
    return (
      <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 truncate">
        {formatSuccessors(task, taskMap)}
      </span>
    );
  }

  // Resource / Assignees
  if (column.id === "resource") {
    const names = task.assignee_details?.map(a => a.name || a.initial).join(", ");
    return (
      <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 truncate" title={names || "Unassigned"}>
        {names || "—"}
      </span>
    );
  }

  // Date columns (start, finish, baseline_start, baseline_finish, constraint_date)
  if (column.type === "date") {
    const rawValue = (task as Record<string, unknown>)[column.field] as string | null | undefined;
    if (!column.editable || readOnly) {
      return (
        <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 tabular-nums truncate">
          {formatTaskDate(rawValue)}
        </span>
      );
    }
    return (
      <EditableCell
        value={rawValue?.split("T")[0] ?? ""}
        type="date"
        compact
        readOnly={readOnly}
        onCommit={(v) => onCommit(task.task_id, { [column.field]: v || null })}
      />
    );
  }

  // Percent complete
  if (column.id === "percent_complete") {
    const isDone = task.task_status === "completed" || task.task_status === "closed";
    const displayValue = isDone ? 100 : (task.percent_complete ?? 0);
    return (
      <EditableCell
        value={displayValue}
        type="percent"
        compact
        readOnly={readOnly}
        onCommit={(v) => onCommit(task.task_id, { percent_complete: v as number })}
      />
    );
  }

  // Duration
  if (column.id === "duration") {
    return (
      <EditableCell
        value={task.scheduled_duration ?? 0}
        type="number"
        compact
        readOnly={readOnly}
        onCommit={(v) => onCommit(task.task_id, { scheduled_duration: v as number })}
      />
    );
  }

  // Total float / slack
  if (column.id === "total_slack") {
    const slack = task.total_slack ?? null;
    const color =
      slack === null
        ? "text-slate-400"
        : slack === 0
        ? "text-rose-500 font-black"
        : slack <= 2
        ? "text-amber-500 font-bold"
        : "text-emerald-500";
    return (
      <span className={`text-[10px] tabular-nums ${color}`}>
        {slack !== null && slack !== undefined ? `${slack}d` : "—"}
      </span>
    );
  }

  // Free float / slack
  if (column.id === "free_slack") {
    const slack = task.free_slack ?? null;
    const color =
      slack === null
        ? "text-slate-400"
        : slack === 0
        ? "text-rose-500 font-black"
        : slack <= 2
        ? "text-amber-500 font-bold"
        : "text-emerald-500";
    return (
      <span className={`text-[10px] tabular-nums ${color}`}>
        {slack !== null && slack !== undefined ? `${slack}d` : "—"}
      </span>
    );
  }

  // Start Variance calculation
  if (column.id === "start_variance") {
    const start = task.scheduled_start ? parseTaskDate(task.scheduled_start) : null;
    const blStart = task.baseline_start ? parseTaskDate(task.baseline_start) : null;
    let variance: number | null = null;
    if (start && blStart) {
      variance = differenceInCalendarDays(start, blStart);
    }
    const color =
      variance === null
        ? "text-slate-400"
        : variance > 0
        ? "text-rose-500 font-bold"
        : variance < 0
        ? "text-emerald-500 font-bold"
        : "text-slate-500";
    
    return (
      <span className={`text-[10px] tabular-nums ${color}`}>
        {variance !== null ? `${variance > 0 ? "+" : ""}${variance}d` : "—"}
      </span>
    );
  }

  // Finish Variance calculation
  if (column.id === "finish_variance") {
    const finish = task.scheduled_finish ? parseTaskDate(task.scheduled_finish) : null;
    const blFinish = task.baseline_finish ? parseTaskDate(task.baseline_finish) : null;
    let variance: number | null = null;
    if (finish && blFinish) {
      variance = differenceInCalendarDays(finish, blFinish);
    }
    const color =
      variance === null
        ? "text-slate-400"
        : variance > 0
        ? "text-rose-500 font-bold"
        : variance < 0
        ? "text-emerald-500 font-bold"
        : "text-slate-500";
    
    return (
      <span className={`text-[10px] tabular-nums ${color}`}>
        {variance !== null ? `${variance > 0 ? "+" : ""}${variance}d` : "—"}
      </span>
    );
  }

  // Status select
  if (column.id === "task_status") {
    const currentStatus = getTaskStatus(task);
    const validOptions = STATUS_OPTIONS.filter(
      (opt) =>
        opt.value === currentStatus ||
        (VALID_STATUS_TRANSITIONS[currentStatus] || []).includes(opt.value as ScheduleTaskStatus)
    );
    return (
      <EditableCell
        value={currentStatus}
        type="select"
        compact
        readOnly={readOnly}
        options={validOptions}
        onCommit={(v) => onCommit(task.task_id, { task_status: v as ScheduleTaskStatus })}
      />
    );
  }

  // Constraint type select
  if (column.id === "constraint_type") {
    return (
      <EditableCell
        value={task.constraint_type ?? "ASAP"}
        type="select"
        compact
        readOnly={readOnly}
        options={CONSTRAINT_OPTIONS}
        onCommit={(v) => onCommit(task.task_id, { constraint_type: v as ScheduleTask["constraint_type"] })}
      />
    );
  }

  // Generic readonly fallback
  const rawValue = (task as Record<string, unknown>)[column.field];
  return (
    <span className="text-[10px] font-medium text-slate-600 dark:text-slate-400 truncate">
      {rawValue !== null && rawValue !== undefined ? String(rawValue) : "—"}
    </span>
  );
});

// ─── Column Header ─────────────────────────────────────────────────

const ColumnHeader = memo(function ColumnHeader({
  column,
  onResize,
}: {
  column: GanttColumnDef;
  onResize: (columnId: string, newWidth: number) => void;
}) {
  const resizeRef = useRef<{ startX: number; startWidth: number } | null>(null);

  const handleResizeStart = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault();
      e.stopPropagation();
      resizeRef.current = { startX: e.clientX, startWidth: column.width };

      const handleMove = (ev: PointerEvent) => {
        if (!resizeRef.current) return;
        const delta = ev.clientX - resizeRef.current.startX;
        onResize(column.id, resizeRef.current.startWidth + delta);
      };

      const handleUp = () => {
        resizeRef.current = null;
        window.removeEventListener("pointermove", handleMove);
        window.removeEventListener("pointerup", handleUp);
      };

      window.addEventListener("pointermove", handleMove);
      window.addEventListener("pointerup", handleUp);
    },
    [column.id, column.width, onResize]
  );

  return (
    <div
      className="relative flex items-center h-full px-2 text-[9px] font-black uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400 whitespace-nowrap select-none"
      style={{ width: column.width }}
    >
      <span className="truncate">{column.label}</span>
      {/* Resize handle */}
      <div
        className="absolute right-0 top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-orange-400/30 active:bg-orange-500/50 z-10 transition-colors"
        onPointerDown={handleResizeStart}
      />
    </div>
  );
});

// ─── Column Picker Dropdown ────────────────────────────────────────

function ColumnPicker({
  columns,
  onToggle,
  onShowDefaults,
  onShowAll,
}: {
  columns: GanttColumnDef[];
  onToggle: (columnId: string) => void;
  onShowDefaults: () => void;
  onShowAll: () => void;
}) {
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="h-7 w-7 flex items-center justify-center rounded-lg text-slate-400 hover:text-orange-500 hover:bg-orange-500/10 transition-all"
        title="Configure columns"
      >
        <Columns3 size={14} />
      </button>
    );
  }

  return (
    <div className="absolute right-0 top-full mt-1 z-[60] w-56 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-950 shadow-2xl p-3 space-y-2 animate-in fade-in zoom-in-95 duration-200">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500">Columns</span>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-[9px] font-bold text-slate-400 hover:text-slate-900 dark:hover:text-white"
        >
          Done
        </button>
      </div>
      {columns.map((col) => (
        <label
          key={col.id}
          className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 dark:hover:bg-white/5 rounded-lg px-2 py-1.5 transition-colors"
        >
          <input
            type="checkbox"
            checked={col.visible}
            onChange={() => onToggle(col.id)}
            className="h-3 w-3 rounded border-slate-300 text-orange-600 focus:ring-orange-500 cursor-pointer"
          />
          <span className="text-[10px] font-semibold text-slate-700 dark:text-slate-300">{col.label}</span>
        </label>
      ))}
      <div className="flex gap-2 pt-2 border-t border-slate-200 dark:border-white/5">
        <button
          type="button"
          onClick={onShowDefaults}
          className="flex-1 text-[9px] font-black uppercase tracking-wider text-sky-500 hover:bg-sky-500/10 rounded-lg py-1.5 transition-colors"
        >
          Defaults
        </button>
        <button
          type="button"
          onClick={onShowAll}
          className="flex-1 text-[9px] font-black uppercase tracking-wider text-orange-500 hover:bg-orange-500/10 rounded-lg py-1.5 transition-colors"
        >
          Show All
        </button>
      </div>
    </div>
  );
}

// ─── Main GanttTaskSheet Component ─────────────────────────────────

export default function GanttTaskSheet({
  tasks,
  scrollLeft,
  onRowContextMenu,
}: {
  tasks: ScheduleTask[];
  scrollLeft: number;
  onRowContextMenu?: (e: React.MouseEvent, taskId: string) => void;
}) {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const collapsedParents = useScheduleStore((state) => state.collapsedParents);
  const systemState = useScheduleStore((state) => state.systemState);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
  const toggleTaskSelection = useScheduleStore((state) => state.toggleTaskSelection);
  const setSelectedTask = useScheduleStore((state) => state.setSelectedTask);
  const toggleParentCollapse = useScheduleStore((state) => state.toggleParentCollapse);
  const openTaskModal = useScheduleStore((state) => state.openTaskModal);
  const indentTask = useScheduleStore((state) => state.indentTask);
  const outdentTask = useScheduleStore((state) => state.outdentTask);

  const readOnly = systemState === "locked";

  const {
    columns,
    visibleColumns,
    totalWidth,
    resizeColumn,
    toggleColumn,
    showDefaultsOnly,
    showAllColumns,
  } = useColumnConfig();

  const handleCommit = useCallback(
    (taskId: string, changes: Partial<ScheduleTask>) => {
      const task = taskMap[taskId];
      if (!task || readOnly) return;
      queueCalculation({
        task_id: taskId,
        project_id: task.project_id,
        version: task.version ?? 1,
        changes,
        trigger_source: "gantt_edit",
      });
    },
    [taskMap, readOnly, queueCalculation]
  );

  return (
    <div
      className="shrink-0 border-r border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm shadow-[4px_0_8px_rgba(0,0,0,0.05)] sticky left-0 z-40"
      style={{ width: totalWidth, transform: `translateX(${scrollLeft}px)` }}
    >
      {/* Header Row */}
      <div className="flex items-center border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-50">
        <div className="flex items-center" style={{ width: totalWidth }}>
          {visibleColumns.map((col) => (
            <ColumnHeader key={col.id} column={col} onResize={resizeColumn} />
          ))}
        </div>
        <div className="relative shrink-0 px-1">
          <ColumnPicker
            columns={columns}
            onToggle={toggleColumn}
            onShowDefaults={showDefaultsOnly}
            onShowAll={showAllColumns}
          />
        </div>
      </div>

      {/* Task Rows */}
      {tasks.map((task, rowIndex) => {
        const depth = getTaskDepth(task, taskMap);
        const isCollapsed = collapsedParents.has(task.task_id);
        const isSelected = selectedTasks.has(task.task_id);

        return (
          <div
            key={task.task_id}
            className={`group/row flex items-center border-b border-slate-200/60 dark:border-white/[0.03] transition-colors cursor-pointer ${
              isSelected
                ? "bg-orange-50 dark:bg-orange-500/[0.06]"
                : task.is_summary
                ? "bg-slate-50/50 dark:bg-white/[0.01]"
                : "hover:bg-slate-50 dark:hover:bg-white/[0.02]"
            }`}
            style={{ height: ROW_HEIGHT }}
            onClick={() => setSelectedTask(task.task_id)}
            onDoubleClick={() => openTaskModal(task.task_id)}
            onContextMenu={(e) => {
              if (onRowContextMenu) {
                e.preventDefault();
                onRowContextMenu(e, task.task_id);
              }
            }}
          >
            {visibleColumns.map((col) => (
              <div
                key={col.id}
                className="flex items-center px-1.5 overflow-hidden shrink-0"
                style={{ width: col.width, height: ROW_HEIGHT }}
              >
                <TaskSheetCell
                  column={col}
                  task={task}
                  taskMap={taskMap}
                  rowIndex={rowIndex}
                  readOnly={readOnly}
                  depth={depth}
                  isCollapsed={isCollapsed}
                  onCommit={handleCommit}
                  onToggleCollapse={toggleParentCollapse}
                  onIndent={indentTask}
                  onOutdent={outdentTask}
                />
              </div>
            ))}

            {/* Checkbox at very end as overlay */}
            <div className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover/row:opacity-100 transition-opacity">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={(e) => {
                  e.stopPropagation();
                  toggleTaskSelection(task.task_id);
                }}
                onClick={(e) => e.stopPropagation()}
                className="h-3 w-3 rounded border-slate-300 dark:border-white/15 text-orange-600 focus:ring-orange-500 cursor-pointer"
                title={isSelected ? "Deselect row" : "Select row"}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
