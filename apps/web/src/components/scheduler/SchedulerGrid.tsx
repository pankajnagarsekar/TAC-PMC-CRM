"use client";

import { useMemo } from "react";
import { Activity } from "lucide-react";
import { toast } from "sonner";

import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import { schedulerApi } from "@/lib/api";
import { ROW_HEIGHT, buildTaskStatusTransition, normalizeTaskOrder } from "./scheduler-utils";
import GridHeader from "./GridHeader";
import GridRow from "./GridRow";
import { useVirtualizedGrid } from "./useVirtualizedGrid";

const COLUMN_TEMPLATE =
  "80px minmax(250px, 3fr) 90px 110px 110px 90px 80px 100px 100px 110px 90px";


export default function SchedulerGrid() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
  const openTask = useScheduleStore((state) => state.openTask);
  const removeTask = useScheduleStore((state) => state.removeTask);
  const systemState = useScheduleStore((state) => state.systemState);
  const pendingCalculation = useScheduleStore((state) => state.pendingCalculation);
  const collapsedParents = useScheduleStore((state) => state.collapsedParents);
  const toggleParentCollapse = useScheduleStore((state) => state.toggleParentCollapse);

  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const filteredTasks = useMemo(() => {
    return tasks.filter((task) => {
      let current = task.parent_id;
      while (current) {
        if (collapsedParents.has(current)) return false;
        current = taskMap[current]?.parent_id;
      }
      return true;
    });
  }, [tasks, taskMap, collapsedParents]);

  const readOnly = systemState === "locked";

  const { viewportRef, onScroll, startIndex, endIndex, topSpacer, bottomSpacer } = useVirtualizedGrid({
    itemCount: filteredTasks.length,
    rowHeight: ROW_HEIGHT,
  });

  const visibleTasks = filteredTasks.slice(startIndex, endIndex);

  const getTaskDepth = (task: ScheduleTask): number => {
    let depth = 0;
    let current = task.parent_id;
    while (current) {
      depth++;
      current = taskMap[current]?.parent_id;
    }
    return depth;
  };

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
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">
            Master Scheduler Grid
          </h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Virtualized task table with WBS hierarchy
          </p>
        </div>

        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
          {pendingCalculation ? (
            <div className="flex items-center gap-2 text-amber-500 animate-pulse">
              <Activity size={12} className="animate-spin" />
              Recalculating
            </div>
          ) : (
            <div className="flex items-center gap-2 text-emerald-500/60">
              <div className="h-1 w-1 rounded-full bg-emerald-500" />
              Synced
            </div>
          )}
          <span className="rounded-full border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-2 py-0.5 text-slate-600 dark:text-white/70 font-bold">
            {filteredTasks.length.toLocaleString("en-US")} / {tasks.length.toLocaleString("en-US")} tasks
          </span>
          <button
            disabled={pendingCalculation || systemState === "locked"}
            onClick={async () => {
              const { taskMap, systemState } = useScheduleStore.getState();
              if (systemState === "locked") return;
              const tasks = Object.values(taskMap);
              if (tasks.length === 0) return;
              try {
                await schedulerApi.save(
                  tasks[0].project_id,
                  tasks,
                  (tasks[0] as ScheduleTask & { project_scheduled_start?: string }).project_scheduled_start || "",
                  0
                );
                toast.success("Schedule committed to database.");
              } catch {
                toast.error("Failed to commit schedule.");
              }
            }}
            className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {pendingCalculation ? "Waiting..." : "Commit to DB"}
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-[28px] border border-slate-200 dark:border-white/5 bg-white/60 dark:bg-slate-950/60 shadow-2xl">
        <div
          ref={viewportRef}
          onScroll={onScroll}
          className="custom-scrollbar max-h-[72vh] overflow-y-auto overflow-x-auto"
        >
          <div style={{ minWidth: 1400 }}>

            <GridHeader columnTemplate={COLUMN_TEMPLATE} />
            <div style={{ height: topSpacer }} />
            {visibleTasks.map((task) => (
              <GridRow
                key={task.task_id}
                task={task}
                depth={getTaskDepth(task)}
                isSelected={selectedTasks.has(task.task_id)}
                isCollapsed={collapsedParents.has(task.task_id)}
                onToggleCollapse={toggleParentCollapse}
                readOnly={readOnly}
                rowHeight={ROW_HEIGHT}
                columnTemplate={COLUMN_TEMPLATE}
                onSelect={openTask}
                onEdit={handleEdit}
                onStatusChange={handleStatusChange}
                onRemove={handleRemove}
              />
            ))}
            <div style={{ height: bottomSpacer }} />
          </div>
        </div>
      </div>
    </div>
  );
}
