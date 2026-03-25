"use client";

import React, { useEffect, useMemo, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { X, Link2, Wallet, Activity, UserRoundPen, MessageSquare, SendHorizontal } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { SchedulePredecessor, ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import { formatTaskDate, getTaskStatus, buildTaskStatusTransition } from "./scheduler-utils";

function FieldRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="space-y-1.5">
      <span className="block text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
        {label}
      </span>
      {children}
    </label>
  );
}

function textInputClass() {
  return "w-full rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-xs font-medium text-white outline-none focus:border-orange-400/40";
}

export default function TaskDrawer() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
  const openTask = useScheduleStore((state) => state.openTask);
  const systemState = useScheduleStore((state) => state.systemState);

  const selectedTask = useMemo(() => {
    const taskId = [...selectedTasks][0];
    return taskId ? taskMap[taskId] : null;
  }, [selectedTasks, taskMap]);

  const [dependencyTaskId, setDependencyTaskId] = useState("");
  const [dependencyType, setDependencyType] = useState<SchedulePredecessor["type"]>("FS");
  const [dependencyLag, setDependencyLag] = useState(0);
  const readOnly = systemState === "locked";

  useEffect(() => {
    setDependencyTaskId("");
    setDependencyType("FS");
    setDependencyLag(0);
  }, [selectedTask?.task_id]);

  if (!selectedTask) {
    return (
      <aside className="sticky top-6 rounded-[28px] border border-white/5 bg-slate-950/70 p-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">Task Drawer</h3>
            <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
              Select a row or card to inspect task details
            </p>
          </div>
          <UserRoundPen size={18} className="text-white/30" />
        </div>
      </aside>
    );
  }

  const commit = (changes: Partial<ScheduleTask>) => {
    if (readOnly) return;
    queueCalculation({
      task_id: selectedTask.task_id,
      project_id: selectedTask.project_id,
      version: selectedTask.version ?? 1,
      changes,
      trigger_source: "grid_edit",
    });
  };

  const statusChange = (nextStatus: ScheduleTaskStatus) => {
    const patch = buildTaskStatusTransition(selectedTask, nextStatus);
    if (!patch) {
      toast.error("That transition is not allowed.");
      return;
    }
    commit(patch);
  };

  const addPredecessor = () => {
    if (!dependencyTaskId.trim()) return;

    const nextPredecessors: SchedulePredecessor[] = [
      ...(selectedTask.predecessors ?? []),
      {
        task_id: dependencyTaskId.trim(),
        project_id: selectedTask.project_id,
        type: dependencyType,
        lag_days: dependencyLag,
        is_external: false,
        strength: "hard",
      },
    ];

    commit({ predecessors: nextPredecessors });
    setDependencyTaskId("");
    setDependencyLag(0);
    toast.success("Dependency added.");
  };

  return (
    <aside className="sticky top-6 rounded-[28px] border border-white/5 bg-slate-950/70 p-5 shadow-2xl">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">Task Drawer</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            {selectedTask.wbs_code || selectedTask.task_id}
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-xl text-white/60 hover:text-white"
          onClick={() => openTask(null)}
        >
          <X size={16} />
        </Button>
      </div>

      <Tabs.Root defaultValue="details" className="space-y-4">
        <Tabs.List className="grid grid-cols-5 gap-1.5 rounded-2xl border border-white/5 bg-white/[0.02] p-1">
          {[
            { value: "details", label: "Details", icon: Activity },
            { value: "deps", label: "Deps", icon: Link2 },
            { value: "financials", label: "Finance", icon: Wallet },
            { value: "mom", label: "AI", icon: MessageSquare },
            { value: "logs", label: "Logs", icon: UserRoundPen },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <Tabs.Trigger
                key={item.value}
                value={item.value}
                className="flex flex-col items-center justify-center gap-1 rounded-xl px-1 py-2 text-[8px] font-black uppercase tracking-[0.1em] text-slate-400 transition data-[state=active]:bg-white/10 data-[state=active]:text-white sm:flex-row sm:text-[10px] sm:tracking-[0.16em]"
              >
                <Icon size={12} />
                <span className="truncate">{item.label}</span>
              </Tabs.Trigger>
            );
          })}
        </Tabs.List>

        <Tabs.Content value="details" className="space-y-4">
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-white">{selectedTask.task_name}</p>
                <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                  Status: {getTaskStatus(selectedTask)}
                </p>
              </div>
              <select
                value={getTaskStatus(selectedTask)}
                onChange={(event) => statusChange(event.target.value as ScheduleTaskStatus)}
                disabled={readOnly}
                className="rounded-xl border border-white/5 bg-white/[0.03] px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-white outline-none"
              >
                <option value="draft">Draft</option>
                <option value="not_started">Not Started</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="closed">Closed</option>
              </select>
            </div>

            <div className="grid gap-3">
              <FieldRow label="Task name">
                <input
                  value={selectedTask.task_name}
                  onChange={(event) => commit({ task_name: event.target.value })}
                  disabled={readOnly}
                  className={textInputClass()}
                />
              </FieldRow>
              <div className="grid grid-cols-2 gap-3">
                <FieldRow label="Start">
                  <input
                    value={selectedTask.scheduled_start ?? ""}
                    onChange={(event) => commit({ scheduled_start: event.target.value || null })}
                    disabled={readOnly}
                    className={textInputClass()}
                  />
                </FieldRow>
                <FieldRow label="Finish">
                  <input
                    value={selectedTask.scheduled_finish ?? ""}
                    onChange={(event) => commit({ scheduled_finish: event.target.value || null })}
                    disabled={readOnly}
                    className={textInputClass()}
                  />
                </FieldRow>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <FieldRow label="Duration">
                  <input
                    type="number"
                    min={0}
                    value={selectedTask.scheduled_duration ?? 0}
                    onChange={(event) => commit({ scheduled_duration: Number(event.target.value || 0) })}
                    disabled={readOnly}
                    className={textInputClass()}
                  />
                </FieldRow>
                <FieldRow label="% Complete">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={selectedTask.percent_complete ?? 0}
                    onChange={(event) => commit({ percent_complete: Number(event.target.value || 0) })}
                    disabled={readOnly}
                    className={textInputClass()}
                  />
                </FieldRow>
              </div>
              <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                Scheduled {formatTaskDate(selectedTask.scheduled_start)} to {formatTaskDate(selectedTask.scheduled_finish)}.
              </p>
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="deps" className="space-y-4">
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
            <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
              Existing predecessors
            </h4>
            <div className="mt-3 space-y-2">
              {(selectedTask.predecessors ?? []).length === 0 ? (
                <p className="text-xs text-slate-500">No predecessors linked yet.</p>
              ) : (
                (selectedTask.predecessors ?? []).map((dep) => (
                  <div
                    key={`${dep.task_id}-${dep.type}-${dep.lag_days ?? 0}`}
                    className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2 text-xs text-white/80"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span>{dep.task_id}</span>
                      <span className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                        {dep.type}
                      </span>
                    </div>
                    <p className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                      Lag: {dep.lag_days ?? 0}d, {dep.strength ?? "hard"}
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="mt-4 grid gap-3">
              <FieldRow label="Predecessor task id">
                <input
                  value={dependencyTaskId}
                  onChange={(event) => setDependencyTaskId(event.target.value)}
                  disabled={readOnly}
                  className={textInputClass()}
                  placeholder="task-12"
                />
              </FieldRow>
              <div className="grid grid-cols-2 gap-3">
                <FieldRow label="Type">
                  <select
                    value={dependencyType}
                    onChange={(event) => setDependencyType(event.target.value as SchedulePredecessor["type"])}
                    disabled={readOnly}
                    className={textInputClass()}
                  >
                    <option value="FS">FS</option>
                    <option value="SS">SS</option>
                    <option value="FF">FF</option>
                    <option value="SF">SF</option>
                  </select>
                </FieldRow>
                <FieldRow label="Lag days">
                  <input
                    type="number"
                    value={dependencyLag}
                    onChange={(event) => setDependencyLag(Number(event.target.value || 0))}
                    disabled={readOnly}
                    className={textInputClass()}
                  />
                </FieldRow>
              </div>
              <Button type="button" onClick={addPredecessor} disabled={readOnly} className="rounded-xl">
                Add Dependency
              </Button>
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="financials" className="space-y-4">
          <div className="grid gap-3 rounded-2xl border border-white/5 bg-white/[0.03] p-4">
            {[
              ["WO Value", selectedTask.wo_value ?? 0],
              ["Retention", selectedTask.wo_retention_value ?? 0],
              ["Payment Value", selectedTask.payment_value ?? 0],
              ["Cost Variance", selectedTask.cost_variance ?? 0],
              ["Weightage", selectedTask.weightage_percent ?? 0],
            ].map(([label, value]) => (
              <div key={label as string} className="flex items-center justify-between rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2">
                <span className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
                  {label}
                </span>
                <span className="text-sm font-semibold text-white">{String(value)}</span>
              </div>
            ))}
          </div>
        </Tabs.Content>

        <Tabs.Content value="mom" className="space-y-4">
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
            <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
              Minutes of Meeting (AI Agent)
            </h4>
            <p className="mt-1 text-[10px] uppercase tracking-[0.14em] text-slate-500 text-pretty">
              Paste meeting notes here. Our AI will extract dates, progress, and blockers to suggest schedule updates.
            </p>

            <div className="mt-4 space-y-3">
              <textarea
                className="w-full min-h-[120px] rounded-xl border border-white/5 bg-white/[0.03] p-3 text-xs font-medium text-white outline-none focus:border-orange-400/40 resize-none transition-all placeholder:text-slate-600"
                placeholder="Example: Discussed foundation work. Completed ahead of time. Start testing next Monday..."
              />
              <Button
                type="button"
                onClick={() => toast.info("AI Analysis started... (Stub)")}
                className="w-full rounded-xl bg-orange-500/10 text-orange-400 border border-orange-500/20 hover:bg-orange-500/20"
              >
                <Activity size={14} className="mr-2" />
                Process with AI
              </Button>
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="logs" className="space-y-4">
          <div className="rounded-2xl border border-white/5 bg-white/[0.03] p-4">
            <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
              Work Logs
            </h4>
            <p className="mt-3 text-xs text-slate-500">
              Work log integration is a stub in Phase 3. This panel will hydrate from timesheets in a later phase.
            </p>
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </aside>
  );
}
