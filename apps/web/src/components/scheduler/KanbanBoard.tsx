"use client";

import React, { useMemo } from "react";
import { toast } from "sonner";

import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import {
  KANBAN_META,
  KANBAN_STATUSES,
  buildTaskStatusTransition,
  getTaskStatus,
  normalizeTaskOrder,
} from "./scheduler-utils";

function groupTasks(tasks: ScheduleTask[]) {
  return tasks.reduce<Record<ScheduleTaskStatus, ScheduleTask[]>>((acc, task) => {
    const status = getTaskStatus(task);
    acc[status].push(task);
    return acc;
  }, {
    draft: [],
    not_started: [],
    in_progress: [],
    completed: [],
    closed: [],
  });
}

export default function KanbanBoard() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
  const openTask = useScheduleStore((state) => state.openTask);
  const selectTask = useScheduleStore((state) => state.selectTask);
  const systemState = useScheduleStore((state) => state.systemState);

  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);
  const grouped = useMemo(() => groupTasks(tasks), [tasks]);
  const readOnly = systemState === "locked";

  const handleDrop = (taskId: string, targetStatus: ScheduleTaskStatus) => {
    const task = taskMap[taskId];
    if (!task || readOnly) return;

    const patch = buildTaskStatusTransition(task, targetStatus);
    if (!patch) {
      toast.error("Invalid task transition.");
      return;
    }

    queueCalculation({
      task_id: taskId,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: patch,
      trigger_source: "kanban_drop",
    });
  };

  const onDragStart = (event: React.DragEvent<HTMLElement>, taskId: string) => {
    event.dataTransfer.setData("text/plain", taskId);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 px-2">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">Kanban Board</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Status transitions respect the scheduler state machine
          </p>
        </div>
        <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
          {tasks.length.toLocaleString("en-US")} tasks
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-5">
        {KANBAN_STATUSES.map((status) => {
          const columnTasks = grouped[status];
          const meta = KANBAN_META[status];

          return (
            <div
              key={status}
              className={`rounded-[24px] border bg-slate-950/60 p-3 shadow-xl ${meta.tone}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                const taskId = event.dataTransfer.getData("text/plain");
                if (taskId) handleDrop(taskId, status);
              }}
            >
              <div className="mb-3 flex items-start justify-between gap-2">
                <div>
                  <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-white">{meta.label}</h4>
                  <p className="mt-1 text-[10px] leading-4 text-white/55">{meta.description}</p>
                </div>
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[10px] font-black text-white/80">
                  {columnTasks.length}
                </span>
              </div>

              <div className="space-y-2">
                {columnTasks.map((task) => {
                  const isSelected = selectedTasks.has(task.task_id);

                  return (
                    <article
                      key={task.task_id}
                      draggable={!readOnly}
                      onDragStart={(event) => onDragStart(event, task.task_id)}
                      onClick={() => {
                        selectTask(task.task_id);
                        openTask(task.task_id);
                      }}
                      className={`cursor-pointer rounded-2xl border px-3 py-3 transition hover:-translate-y-0.5 hover:border-white/20 ${isSelected ? "border-sky-400/40 bg-sky-500/15" : "border-white/5 bg-white/[0.03]"}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold text-white">{task.task_name}</p>
                          <p className="mt-1 text-[10px] uppercase tracking-[0.16em] text-white/45">
                            {task.wbs_code || task.task_id}
                          </p>
                        </div>
                        <span className="rounded-full border border-white/10 bg-white/5 px-2 py-1 text-[10px] font-black uppercase text-white/70">
                          {task.percent_complete ?? 0}%
                        </span>
                      </div>
                      <div className="mt-3 flex flex-col gap-2">
                        <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                          <div
                            className="h-full bg-sky-400 transition-all duration-300"
                            style={{ width: `${task.percent_complete ?? 0}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between gap-2 text-[10px] uppercase tracking-[0.16em] text-white/50">
                          <span>{task.task_mode ?? "Auto"}</span>
                          <span>{task.scheduled_duration ?? 0}d</span>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
