"use client";

import { memo, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import { formatTaskDate, getTaskStatus, KANBAN_META } from "./scheduler-utils";

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

type GridRowProps = {
  task: ScheduleTask;
  depth: number;
  isSelected: boolean;
  readOnly: boolean;
  rowHeight: number;
  columnTemplate: string;
  isCollapsed: boolean;
  onToggleCollapse: (taskId: string) => void;
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
  rowHeight,
  columnTemplate,
  isCollapsed,
  onToggleCollapse,
  onSelect,
  onEdit,
  onStatusChange,
  onRemove,
}: GridRowProps) {
  const status = getTaskStatus(task);
  const statusMeta = KANBAN_META[status];

  return (
    <div
      className={`grid items-stretch border-b border-white/5 text-xs transition-colors ${isSelected ? "bg-white/[0.04]" : "bg-transparent hover:bg-white/[0.025]"}`}
      style={{ gridTemplateColumns: columnTemplate, minHeight: rowHeight }}
      onClick={() => onSelect(task.task_id)}
    >
      <div className="flex items-center gap-2 px-3 text-[10px] font-black uppercase tracking-[0.18em] text-orange-300">
        <span>{task.wbs_code || task.task_id}</span>
      </div>

      <div className="flex items-center gap-2 px-3 py-2" style={{ paddingLeft: 12 + depth * 16 }}>
        {task.is_summary ? (
          <button
            type="button"
            className="rounded p-0.5 hover:bg-white/10 text-white/50 hover:text-white transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              onToggleCollapse(task.task_id);
            }}
          >
            {isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
          </button>
        ) : (
          <span className="w-4" />
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
            title="Auto: CPM calculated dates | Manual: User-defined dates"
          >
            <option value="Auto">Auto</option>
            <option value="Manual">Manual</option>
          </select>
        )}
      </div>

      <div className="flex items-center px-3 text-slate-300">{formatTaskDate(task.scheduled_start)}</div>
      <div className="flex items-center px-3 text-slate-300">{formatTaskDate(task.scheduled_finish)}</div>

      <div className="flex items-center px-3 text-slate-300">{task.scheduled_duration ?? "--"}</div>

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

export default GridRow;
