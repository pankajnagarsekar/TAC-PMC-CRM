"use client";

import React, { memo, useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, ChevronDown, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import {
  ROW_HEIGHT,
  formatTaskDate,
  getTaskStatus,
  normalizeTaskOrder,
  buildTaskStatusTransition,
  KANBAN_META,
} from "./scheduler-utils";

const COLUMN_TEMPLATE =
  "80px minmax(220px, 2.2fr) 110px 120px 120px 120px 120px 120px 120px 120px 90px";

function clampNumber(value: string, min = 0, max = 100) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return min;
  return Math.min(max, Math.max(min, parsed));
}

type EditableCellProps = {
  value: string | number | null | undefined;
  type?: "text" | "number";
  onCommit: (value: string | number | null) => void;
  className?: string;
};

const EditableCell = memo(function EditableCell({
  value,
  type = "text",
  onCommit,
  className = "",
}: EditableCellProps) {
  const [draft, setDraft] = useState(value ?? "");

  useEffect(() => {
    setDraft(value ?? "");
  }, [value]);

  return (
    <input
      value={draft}
      type={type}
      onChange={(event) => setDraft(type === "number" ? event.target.value : event.target.value)}
      onBlur={() => {
        const nextValue =
          type === "number"
            ? (draft === "" ? null : clampNumber(String(draft), 0, 999999))
            : (String(draft).trim() || null);
        onCommit(nextValue);
      }}
      className={`w-full rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-xs font-medium text-white outline-none transition focus:border-orange-400/40 focus:bg-white/[0.05] ${className}`}
    />
  );
});

type RowProps = {
  task: ScheduleTask;
  depth: number;
  isSelected: boolean;
  readOnly: boolean;
  onSelect: (taskId: string) => void;
  onEdit: (taskId: string, changes: Partial<ScheduleTask>) => void;
  onStatusChange: (task: ScheduleTask, nextStatus: ScheduleTaskStatus) => void;
  onRemove: (taskId: string) => void;
};

const GridRow = memo(function GridRow({
  task,
  depth,
  isSelected,
  readOnly,
  onSelect,
  onEdit,
  onStatusChange,
  onRemove,
}: RowProps) {
  const status = getTaskStatus(task);
  const statusMeta = KANBAN_META[status];

  return (
    <div
      className={`grid items-stretch border-b border-white/5 text-xs transition-colors ${isSelected ? "bg-white/[0.04]" : "bg-transparent hover:bg-white/[0.025]"}`}
      style={{ gridTemplateColumns: COLUMN_TEMPLATE, minHeight: ROW_HEIGHT }}
      onClick={() => onSelect(task.task_id)}
    >
      <div className="flex items-center gap-2 px-3 text-[10px] font-black uppercase tracking-[0.18em] text-orange-300">
        <span>{task.wbs_code || task.task_id}</span>
      </div>

      <div className="flex items-center gap-2 px-3 py-2" style={{ paddingLeft: 12 + depth * 16 }}>
        {task.is_summary ? (
          <ChevronDown size={14} className="text-white/30" />
        ) : (
          <span className="w-3" />
        )}
        {readOnly ? (
          <span className="truncate font-semibold text-white">{task.task_name}</span>
        ) : (
          <EditableCell
            value={task.task_name}
            onCommit={(nextValue) => {
              if (typeof nextValue !== "string" || nextValue.length === 0) return;
              onEdit(task.task_id, { task_name: nextValue });
            }}
          />
        )}
      </div>

      <div className="flex items-center px-3">
        {readOnly ? (
          <span className="text-slate-300">{task.task_mode ?? "Auto"}</span>
        ) : (
          <select
            value={task.task_mode ?? "Auto"}
            onChange={(event) => onEdit(task.task_id, { task_mode: event.target.value as "Auto" | "Manual" })}
            className="w-full rounded-xl border border-white/5 bg-white/[0.03] px-2 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-white outline-none focus:border-orange-400/40"
          >
            <option value="Auto">Auto</option>
            <option value="Manual">Manual</option>
          </select>
        )}
      </div>

      <div className="flex items-center px-3 text-slate-300">{formatTaskDate(task.scheduled_start)}</div>

      <div className="flex items-center px-3 text-slate-300">{formatTaskDate(task.scheduled_finish)}</div>

      <div className="flex items-center px-3 text-slate-300">{task.scheduled_duration ?? "—"}</div>

      <div className="flex items-center px-3">
        {readOnly ? (
          <span className="text-slate-300">{task.percent_complete ?? 0}%</span>
        ) : (
          <EditableCell
            type="number"
            value={task.percent_complete ?? 0}
            onCommit={(nextValue) => {
              if (typeof nextValue !== "number") return;
              onEdit(task.task_id, { percent_complete: nextValue });
            }}
          />
        )}
      </div>

      <div className="flex items-center px-3 text-slate-300">{statusMeta.label}</div>

      <div className="flex items-center px-3 text-slate-300">{task.assigned_resources?.length ?? 0}</div>

      <div className="flex items-center px-3 text-slate-300">{formatTaskDate(task.deadline)}</div>

      <div className="flex items-center justify-end gap-2 px-3">
        {!readOnly && (
          <>
            <select
              value={status}
              onChange={(event) => {
                const nextStatus = event.target.value as ScheduleTaskStatus;
                onStatusChange(task, nextStatus);
              }}
              className="rounded-xl border border-white/5 bg-white/[0.03] px-2 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-white outline-none focus:border-orange-400/40"
            >
              {Object.keys(KANBAN_META).map((item) => (
                <option key={item} value={item}>
                  {KANBAN_META[item as ScheduleTaskStatus].label}
                </option>
              ))}
            </select>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-xl text-white/70 hover:text-white"
              onClick={(event) => {
                event.stopPropagation();
                onSelect(task.task_id);
              }}
              title="Edit task"
            >
              <Pencil size={14} />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-xl text-white/70 hover:text-rose-300"
              onClick={(event) => {
                event.stopPropagation();
                onRemove(task.task_id);
              }}
              title="Remove task locally"
            >
              <Trash2 size={14} />
            </Button>
          </>
        )}
      </div>
    </div>
  );
});

GridRow.displayName = "GridRow";

export default function SchedulerGrid() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
  const selectTask = useScheduleStore((state) => state.selectTask);
  const removeTask = useScheduleStore((state) => state.removeTask);
  const systemState = useScheduleStore((state) => state.systemState);
  const pendingCalculation = useScheduleStore((state) => state.pendingCalculation);

  const tasks = useMemo(
    () => normalizeTaskOrder(taskMap, taskOrder),
    [taskMap, taskOrder],
  );

  const readOnly = systemState === "locked";
  const [scrollTop, setScrollTop] = useState(0);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const viewportHeight = 480;
  const visibleCount = Math.ceil(viewportHeight / ROW_HEIGHT) + 8;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 4);
  const endIndex = Math.min(tasks.length, startIndex + visibleCount);
  const visibleTasks = tasks.slice(startIndex, endIndex);
  const topSpacer = startIndex * ROW_HEIGHT;
  const bottomSpacer = Math.max(0, (tasks.length - endIndex) * ROW_HEIGHT);

  const handleEdit = (taskId: string, changes: Partial<ScheduleTask>) => {
    const task = taskMap[taskId];
    if (!task || readOnly) return;

    queueCalculation({
      task_id: taskId,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: {
        ...changes,
      },
      trigger_source: "grid_edit",
    });
  };

  const handleStatusChange = (task: ScheduleTask, nextStatus: ScheduleTaskStatus) => {
    if (readOnly) return;

    const patch = buildTaskStatusTransition(task, nextStatus);
    if (!patch) {
      toast.error("That task transition is not allowed by the scheduler state machine.");
      return;
    }

    queueCalculation({
      task_id: task.task_id,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: patch,
      trigger_source: "kanban_drop",
    });
  };

  const handleRemove = (taskId: string) => {
    removeTask(taskId);
    toast.info("Task removed locally from the grid.");
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 px-2">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">
            Master Scheduler Grid
          </h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Virtualized task table driven by useScheduleStore
          </p>
        </div>

        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
          {pendingCalculation ? (
            <>
              <AlertTriangle size={12} className="text-amber-300" />
              Recalculating
            </>
          ) : (
            <>Synced</>
          )}
          <span className="rounded-full border border-white/5 bg-white/[0.03] px-2 py-1 text-white/70">
            {tasks.length.toLocaleString("en-US")} tasks
          </span>
        </div>
      </div>

      <div className="overflow-hidden rounded-[28px] border border-white/5 bg-slate-950/60 shadow-2xl">
        <div className="grid border-b border-white/5 bg-white/[0.03] text-[10px] font-black uppercase tracking-[0.18em] text-slate-400" style={{ gridTemplateColumns: COLUMN_TEMPLATE }}>
          <div className="px-3 py-3">WBS</div>
          <div className="px-3 py-3">Task</div>
          <div className="px-3 py-3">Mode</div>
          <div className="px-3 py-3">Start</div>
          <div className="px-3 py-3">Finish</div>
          <div className="px-3 py-3">Duration</div>
          <div className="px-3 py-3">% Complete</div>
          <div className="px-3 py-3">Status</div>
          <div className="px-3 py-3">Resources</div>
          <div className="px-3 py-3">Deadline</div>
          <div className="px-3 py-3 text-right">Actions</div>
        </div>

        <div
          ref={viewportRef}
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
          className="custom-scrollbar max-h-[72vh] overflow-y-auto"
        >
          <div style={{ height: topSpacer }} />
          {visibleTasks.map((task) => (
            <GridRow
              key={task.task_id}
              task={task}
              depth={task.parent_id ? 1 : 0}
              isSelected={selectedTasks.has(task.task_id)}
              readOnly={readOnly}
              onSelect={selectTask}
              onEdit={handleEdit}
              onStatusChange={handleStatusChange}
              onRemove={handleRemove}
            />
          ))}
          <div style={{ height: bottomSpacer }} />
        </div>
      </div>
    </div>
  );
}
