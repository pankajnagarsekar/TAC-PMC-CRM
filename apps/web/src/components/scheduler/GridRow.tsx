"use client";

import { memo } from "react";
import { ChevronDown, ChevronRight, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import type { ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import { formatTaskDate, getTaskStatus, KANBAN_META, VALID_STATUS_TRANSITIONS } from "./scheduler-utils";
import EditableCell from "./EditableCell";

function stripHtmlTags(s: string): string {
  return s.replace(/<[^>]*>/g, "").trim();
}

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
  onOpenModal: (taskId: string) => void;
  onEdit: (taskId: string, changes: Partial<ScheduleTask>) => void;
  onStatusChange: (task: ScheduleTask, nextStatus: ScheduleTaskStatus) => void;
  onToggleSelection: (taskId: string) => void;
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
  onOpenModal,
  onEdit,
  onStatusChange,
  onToggleSelection,
  onRemove,
}: GridRowProps) {
  const status = getTaskStatus(task);
  const statusMeta = KANBAN_META[status];

  return (
    <div
      className={`grid items-stretch border-b border-slate-200 dark:border-white/5 text-xs transition-colors ${isSelected ? "bg-slate-100 dark:bg-white/[0.04]" : "bg-transparent hover:bg-slate-50 dark:hover:bg-white/[0.025]"}`}
      style={{ gridTemplateColumns: columnTemplate, minHeight: rowHeight }}
      onClick={() => onSelect(task.task_id)}
    >
      <div className="flex items-center justify-center px-3 border-r border-slate-200 dark:border-white/5">
        <input 
          type="checkbox" 
          checked={isSelected}
          onChange={(e) => {
            e.stopPropagation();
            onToggleSelection(task.task_id);
          }}
          className="h-3 w-3 rounded border-slate-300 text-sky-600 focus:ring-sky-500 bg-transparent cursor-pointer"
        />
      </div>

      <div className="flex items-center gap-2 px-3 text-[10px] font-black uppercase tracking-[0.18em] text-orange-600 dark:text-orange-300 border-r border-slate-200 dark:border-white/5">
        <span>{task.wbs_code || task.task_id}</span>
      </div>

      <div className="flex items-center gap-2 px-3 py-2 border-r border-slate-200 dark:border-white/5" style={{ paddingLeft: 12 + depth * 16 }}>
        {task.is_summary ? (
          <button
            type="button"
            className="rounded p-0.5 hover:bg-slate-200 dark:hover:bg-white/10 text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition-colors"
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
          <span className={`truncate font-semibold ${task.is_critical ? "text-rose-600 dark:text-rose-400" : "text-slate-900 dark:text-white"}`}>
            {task.task_name}
          </span>
        ) : (
          <div className="flex-1 flex items-center gap-2">
            <EditableCell
              value={task.task_name}
              onCommit={(nextValue) => {
                if (typeof nextValue !== "string") return;
                const clean = stripHtmlTags(nextValue);
                if (!clean) {
                  toast.error("Task description cannot be empty.");
                  return;
                }
                onEdit(task.task_id, { task_name: clean });
              }}
              className={task.is_critical ? "text-rose-600 dark:text-rose-400" : ""}
            />
            {task.is_critical && (
              <span 
                className="flex items-center justify-center w-4 h-4 rounded-full bg-rose-500/10 text-rose-500"
                title="Critical Path: Delaying this task will delay the project finish."
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M17.66 11.2c-.23-.3-.51-.56-.77-.82-.67-.6-1.43-1.03-2.07-1.66C13.33 7.26 13 4.85 13.95 3c-.95.23-1.78.75-2.49 1.32-2.59 2.08-3.61 5.75-2.39 8.9.04.1.08.2.08.33 0 .22-.15.42-.35.5-.23.1-.47.04-.64-.12-.06-.05-.1-.1-.15-.17-1.1-1.43-1.39-3.41-1.12-5.18-2.14 1.44-3.14 4.14-2.56 6.63.14.6.37 1.18.66 1.72.71 1.33 1.84 2.41 3.24 2.99 1.5.6 3.14.6 4.7.2 2.3-.6 4.11-2.4 4.71-4.72.08-.36.15-.72.15-1.08 0-1-.31-1.91-.85-2.71zm-4.46 6.8c-.8.15-1.6.03-2.3-.33-.77-.39-1.29-1.06-1.52-1.86-.06-.2-.06-.41 0-.6.1-.25.32-.42.56-.47.24-.04.48.06.63.26.24.3.56.53.93.65.13.04.27.06.4.06.51 0 .97-.24 1.25-.65.26-.39.31-.88.13-1.33-.02-.05-.05-.1-.08-.14-.42-.51-1.03-.84-1.16-1.53-.13-.7.2-1.33.64-1.84.14.33.43.59.78.69.25.07.5.04.71-.08.22-.13.36-.35.39-.59.03-.24-.07-.47-.25-.62-.1-.08-.18-.16-.25-.26.22.1.42.22.61.37.7.53 1.14 1.4 1.07 2.3-.04.47-.2.9-.45 1.27-.45.68-.43 1.5.02 2.16.4.58.5 1.31.2 2 .16-.13.3-.28.43-.43.14.57.06 1.18-.24 1.68-.42.7-1.18 1.13-2 1.22z"/></svg>
              </span>
            )}
          </div>
        )}
        
        {/* Assignee Details (REQ-010) */}
        {task.assignee_details && task.assignee_details.length > 0 ? (
          <div className="flex -space-x-1 ml-auto">
            {task.assignee_details.slice(0, 3).map((u: { name: string; initial: string }, idx: number) => (
              <div 
                key={idx}
                className="w-4 h-4 rounded-full bg-sky-100 dark:bg-sky-500/20 flex items-center justify-center border border-white dark:border-slate-900 shadow-sm"
                title={u.name}
              >
                <span className="text-[8px] font-black text-sky-700 dark:text-sky-300">
                  {u.initial}
                </span>
              </div>
            ))}
            {task.assignee_details.length > 3 && (
              <div className="w-4 h-4 rounded-full bg-slate-300 dark:bg-white/20 flex items-center justify-center border border-white dark:border-slate-900">
                <span className="text-[7px] font-black text-slate-600">+{task.assignee_details.length - 3}</span>
              </div>
            )}
          </div>
        ) : task.assignee_ids && task.assignee_ids.length > 0 && (
          <div className="flex -space-x-1 ml-auto opacity-50">
             <div className="w-4 h-4 rounded-full bg-slate-200 dark:bg-white/10 flex items-center justify-center border border-white dark:border-slate-900">
               <span className="text-[8px] font-black text-slate-500">?</span>
             </div>
          </div>
        )}
      </div>

      <div className="flex items-center px-3 border-r border-slate-200 dark:border-white/5">
        {readOnly ? (
          <span className="text-slate-700 dark:text-slate-300">{task.task_mode === "Manual" ? "Manual" : "Auto (CPM)"}</span>
        ) : (
          <select
            value={task.task_mode ?? "Auto"}
            onChange={(event) => onEdit(task.task_id, { task_mode: event.target.value as "Auto" | "Manual" })}
            className="w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-2 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-slate-900 dark:text-white outline-none focus:border-orange-400/40"
            title="Auto (CPM): Calculated by engine | Manual: User-defined dates"
          >
            <option value="Auto">Auto (CPM)</option>
            <option value="Manual">Manual</option>
          </select>
        )}
      </div>

      <div
        className="flex items-center px-3 text-slate-700 dark:text-slate-300 border-r border-slate-200 dark:border-white/5 font-medium"
        title={task.calc_reason || "Calculated by engine"}
      >
        {!readOnly && task.task_mode === "Manual" ? (
          <input
            type="date"
            value={task.scheduled_start?.split("T")[0] || ""}
            onChange={(e) => onEdit(task.task_id, { scheduled_start: e.target.value })}
            className="bg-transparent text-xs outline-none focus:text-orange-500 w-full"
          />
        ) : (
          formatTaskDate(task.scheduled_start)
        )}
      </div>
      <div
        className="flex items-center px-3 text-slate-700 dark:text-slate-300 border-r border-slate-200 dark:border-white/5 font-medium"
        title={task.calc_reason || "Calculated by engine"}
      >
        {!readOnly && task.task_mode === "Manual" ? (
          <input
            type="date"
            value={task.scheduled_finish?.split("T")[0] || ""}
            onChange={(e) => onEdit(task.task_id, { scheduled_finish: e.target.value })}
            className="bg-transparent text-xs outline-none focus:text-orange-500 w-full"
          />
        ) : (
          formatTaskDate(task.scheduled_finish)
        )}
      </div>

      <div className="flex items-center justify-center px-3 text-slate-800 dark:text-slate-300 border-r border-slate-200 dark:border-white/5 font-bold uppercase text-[10px] tracking-widest">
        {`${task.scheduled_duration || 0} d`}
      </div>

      <div className="flex items-center justify-center px-3 border-r border-slate-200 dark:border-white/5">
        {readOnly ? (
          <span className="text-slate-800 dark:text-slate-300 font-black">{task.percent_complete ?? 0}%</span>
        ) : (
          <div className="w-16">
            <EditableCell
              type="number"
              value={task.percent_complete ?? 0}
              onCommit={(nextValue) => {
                const n = Number(nextValue);
                if (!Number.isFinite(n)) {
                  toast.error("Enter a number (0–100).");
                  return;
                }
                if (n < 0 || n > 100) {
                  toast.error(`Must be 0–100%. Got ${n}%.`);
                  return;
                }
                onEdit(task.task_id, { percent_complete: Math.round(n) });
              }}
              className="text-center font-black"
            />
          </div>
        )}
      </div>

      <div className="flex items-center px-3 text-slate-800 dark:text-slate-300 border-r border-slate-200 dark:border-white/5 font-black text-[9px] uppercase tracking-[0.18em]">
        {statusMeta.label}
      </div>

      <div className="flex items-center justify-center px-3 text-slate-800 dark:text-slate-300 border-r border-slate-200 dark:border-white/5 font-black italic">
        {readOnly ? (
          task.heads || 0
        ) : (
          <div className="w-12">
            <EditableCell
              type="number"
              value={task.heads || 0}
              onCommit={(nextValue) => {
                const n = Number(nextValue);
                if (Number.isFinite(n) && n >= 0) {
                  onEdit(task.task_id, { heads: Math.round(n) });
                }
              }}
              className="text-center font-black"
            />
          </div>
        )}
      </div>

      <div className={`flex items-center px-3 border-r border-slate-200 dark:border-white/5 font-bold text-[10px] ${task.deadline && new Date(task.deadline) < new Date(new Date().toDateString()) ? 'text-rose-600 animate-pulse' : 'text-slate-700 dark:text-slate-300'}`}>
        {formatTaskDate(task.deadline)}
      </div>

      <div className="flex items-center justify-end gap-2 px-3">
        {!readOnly && (
          <>
            <select
              value={status}
              onChange={(event) => {
                const nextStatus = event.target.value as ScheduleTaskStatus;
                onStatusChange(task, nextStatus);
              }}
              className="rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-2 py-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-900 dark:text-white outline-none focus:border-orange-400/40"
            >
              {Object.keys(KANBAN_META).map((item) => {
                const isValid = item === status ||
                  (VALID_STATUS_TRANSITIONS[status] || []).includes(item as ScheduleTaskStatus);

                if (!isValid) return null;

                return (
                  <option key={item} value={item}>
                    {KANBAN_META[item as ScheduleTaskStatus].label}
                  </option>
                );
              })}
            </select>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-xl text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              onClick={(event) => {
                event.stopPropagation();
                onOpenModal(task.task_id);
              }}
              title="Edit task"
            >
              <Pencil size={14} />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-9 w-9 rounded-xl text-slate-600 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-300"
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
