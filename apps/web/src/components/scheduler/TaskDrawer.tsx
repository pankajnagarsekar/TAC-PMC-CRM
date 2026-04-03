"use client";

import React, { useEffect, useMemo, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { X, Link2, Wallet, Activity, UserRoundPen, MessageSquare, Info } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { SchedulePredecessor, ScheduleTask, ScheduleTaskStatus, MomResult, ActionItem } from "@/types/schedule.types";
import {
  formatTaskDate,
  getTaskStatus,
  KANBAN_META,
  VALID_STATUS_TRANSITIONS,
  buildTaskStatusTransition
} from "./scheduler-utils";
import { formatCurrencySafe } from "@/lib/formatters";

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
  return "w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-3 py-2 text-xs font-medium text-slate-900 dark:text-white outline-none focus:border-orange-400/40 transition-all";
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

  // AI MoM State
  const [momNotes, setMomNotes] = useState("");
  const [isAnalyzingMom, setIsAnalyzingMom] = useState(false);
  const [momResult, setMomResult] = useState<MomResult | null>(null);

  // S-BUG #5: Local state for performance (avoid keystroke recalculations)
  const [localTaskName, setLocalTaskName] = useState(selectedTask?.task_name || "");
  const [localDuration, setLocalDuration] = useState<number>(selectedTask?.scheduled_duration ?? 0);
  const [localPercent, setLocalPercent] = useState<number>(selectedTask?.percent_complete ?? 0);

  useEffect(() => {
    if (!selectedTask) return;
    setLocalTaskName(selectedTask.task_name);
    setLocalDuration(selectedTask.scheduled_duration ?? 0);
    setLocalPercent(selectedTask.percent_complete ?? 0);
  }, [selectedTask, selectedTask?.task_id, selectedTask?.task_name, selectedTask?.scheduled_duration, selectedTask?.percent_complete]);

  const handleAnalyzeMom = async () => {
    if (!selectedTask || !momNotes.trim()) return;
    setIsAnalyzingMom(true);
    try {
      const response = await api.post(
        `/api/v1/projects/${selectedTask.project_id}/tasks/${selectedTask.task_id}/mom-extract`,
        { raw_notes: momNotes }
      );
      setMomResult(response.data);
      toast.success("AI Analysis complete.");
    } catch (err) {
      toast.error("AI Analysis failed. Check provider status.");
      console.error(err);
    } finally {
      setIsAnalyzingMom(false);
    }
  };

  useEffect(() => {
    setDependencyTaskId("");
    setDependencyType("FS");
    setDependencyLag(0);
    setMomNotes("");
    setMomResult(null);
  }, [selectedTask?.task_id]);

  if (!selectedTask) {
    return (
      <aside className="sticky top-6 rounded-[28px] border border-slate-200 dark:border-white/5 bg-slate-50/70 dark:bg-slate-950/70 p-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Task Drawer</h3>
            <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
              Select a row or card to inspect task details
            </p>
          </div>
          <UserRoundPen size={18} className="text-slate-400 dark:text-white/30" />
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
      trigger_source: "drawer_edit",
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
    <aside className="sticky top-6 z-30 rounded-[28px] border border-slate-200 dark:border-white/5 bg-white/80 dark:bg-slate-950/70 p-5 shadow-2xl backdrop-blur-xl">
      <div className="mb-5 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Task Drawer</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            {selectedTask.wbs_code || selectedTask.task_id}
          </p>
        </div>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="h-9 w-9 rounded-xl text-slate-500 hover:text-slate-900 dark:text-white/60 dark:hover:text-white"
          onClick={() => openTask(null)}
        >
          <X size={16} />
        </Button>
      </div>

      <Tabs.Root defaultValue="details" className="space-y-4">
        <Tabs.List className="grid grid-cols-5 gap-1.5 rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.02] p-1">
          {[
            { value: "details", label: "Task Brief", icon: Activity },
            { value: "deps", label: "Project Network", icon: Link2 },
            { value: "financials", label: "Economics", icon: Wallet },
            { value: "mom", label: "Field Notes", icon: MessageSquare },
            { value: "logs", label: "Log Registry", icon: UserRoundPen },
          ].map((item) => {
            const Icon = item.icon;
            return (
              <Tabs.Trigger
                key={item.value}
                value={item.value}
                className="flex flex-col items-center justify-center gap-1 rounded-xl px-1 py-2 text-[7px] font-black uppercase tracking-[0.1em] text-slate-400 transition data-[state=active]:bg-slate-200 dark:data-[state=active]:bg-white/10 data-[state=active]:text-slate-900 dark:data-[state=active]:text-white sm:flex-row sm:text-[9px] sm:tracking-[0.14em]"
              >
                <Icon size={12} />
                <span className="truncate">{item.label}</span>
              </Tabs.Trigger>
            );
          })}
        </Tabs.List>

        <Tabs.Content value="details" className="space-y-4">
          <div className="rounded-2xl border border-slate-200 dark:border-white/5 bg-white dark:bg-white/[0.03] p-4">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-white">{selectedTask.task_name}</p>
                <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">
                  Status: {getTaskStatus(selectedTask)}
                </p>
              </div>
              <select
                value={getTaskStatus(selectedTask)}
                onChange={(event) => statusChange(event.target.value as ScheduleTaskStatus)}
                disabled={readOnly}
                className="rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-slate-900 dark:text-white outline-none"
              >
                {/* S-BUG #8: Only show valid transitions */}
                {Object.keys(KANBAN_META).map((item) => {
                  const currentStatus = getTaskStatus(selectedTask);
                  const isValid = item === currentStatus ||
                    (VALID_STATUS_TRANSITIONS[currentStatus] || []).includes(item as ScheduleTaskStatus);

                  if (!isValid) return null;

                  return (
                    <option key={item} value={item}>
                      {KANBAN_META[item as ScheduleTaskStatus].label}
                    </option>
                  );
                })}
              </select>
            </div>

            <div className="grid gap-3">
              <FieldRow label="Task name">
                <input
                  value={localTaskName}
                  onChange={(e) => setLocalTaskName(e.target.value)}
                  onBlur={() => commit({ task_name: localTaskName })}
                  disabled={readOnly}
                  className={textInputClass()}
                />
              </FieldRow>
              <div className="grid grid-cols-2 gap-3">
                <FieldRow label="Start">
                  <input
                    type="date"
                    value={selectedTask.scheduled_start?.split("T")[0] ?? ""}
                    onChange={(event) => commit({ scheduled_start: event.target.value || null })}
                    disabled={readOnly}
                    className={textInputClass()}
                  />
                </FieldRow>
                <FieldRow label="Finish">
                  <input
                    type="date"
                    value={selectedTask.scheduled_finish?.split("T")[0] ?? ""}
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
                    value={localDuration}
                    onChange={(e) => setLocalDuration(Number(e.target.value || 0))}
                    onBlur={() => commit({ scheduled_duration: localDuration })}
                    disabled={readOnly}
                    className={textInputClass()}
                  />
                </FieldRow>
                <FieldRow label="% Complete">
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={localPercent}
                    onChange={(e) => setLocalPercent(Number(e.target.value || 0))}
                    onBlur={() => commit({ percent_complete: localPercent })}
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

        <Tabs.Content value="deps" className="space-y-4 pt-2">
          <div className="rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] p-4">
            <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
              Project Network (Predecessors)
            </h4>
            <div className="mt-3 space-y-2">
              {(selectedTask.predecessors ?? []).length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/5 p-4 text-center">
                  <p className="text-[10px] uppercase tracking-[0.1em] text-slate-500">No network links established</p>
                </div>
              ) : (
                (selectedTask.predecessors ?? []).map((dep) => (
                  <div
                    key={`${dep.task_id}-${dep.type}-${dep.lag_days ?? 0}`}
                    className="rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2 text-xs text-white/80"
                  >
                    <div className="flex items-center justify-between gap-2 text-[10px]">
                      <span className="font-bold text-white tracking-widest uppercase">{dep.task_id}</span>
                      <span className="bg-white/5 px-2 py-0.5 rounded text-sky-400 font-bold border border-sky-400/20">
                        {dep.type}
                      </span>
                    </div>
                    <p className="mt-2 text-[10px] uppercase tracking-[0.14em] text-slate-500">
                      Lag: <span className="text-white font-bold">{dep.lag_days ?? 0}</span> days, Strategy: <span className="text-white">{dep.strength ?? "hard"}</span>
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="mt-6 space-y-4">
              <h5 className="text-[9px] font-black uppercase tracking-[0.25em] text-slate-500 border-b border-white/5 pb-1">Link New Predecessor</h5>
              <div className="grid gap-3">
                <FieldRow label="Target Task ID">
                  <input
                    value={dependencyTaskId}
                    onChange={(event) => setDependencyTaskId(event.target.value)}
                    disabled={readOnly}
                    className={textInputClass()}
                    placeholder="example: task-42"
                  />
                </FieldRow>
                <div className="grid grid-cols-2 gap-3">
                  <FieldRow label="Link Type">
                    <select
                      value={dependencyType}
                      onChange={(event) => setDependencyType(event.target.value as SchedulePredecessor["type"])}
                      disabled={readOnly}
                      className={textInputClass()}
                    >
                      <option value="FS">Finish-to-Start (FS)</option>
                      <option value="SS">Start-to-Start (SS)</option>
                      <option value="FF">Finish-to-Finish (FF)</option>
                      <option value="SF">Start-to-Finish (SF)</option>
                    </select>
                  </FieldRow>
                  <FieldRow label="Lag Delay (d)">
                    <input
                      type="number"
                      value={dependencyLag}
                      onChange={(event) => setDependencyLag(Number(event.target.value || 0))}
                      disabled={readOnly}
                      className={textInputClass()}
                    />
                  </FieldRow>
                </div>
                <Button
                  type="button"
                  onClick={addPredecessor}
                  disabled={readOnly || !dependencyTaskId}
                  className="rounded-xl mt-2 bg-sky-500/10 text-sky-400 border border-sky-500/20 hover:bg-sky-500/20"
                >
                  Confirm Network Link
                </Button>
              </div>
            </div>
          </div>
        </Tabs.Content>
        <Tabs.Content value="financials" className="space-y-4 pt-2">
          <div className="rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] p-1 overflow-hidden">
            <div className="bg-white/[0.02] p-4 border-b border-white/5 flex justify-between items-center text-pretty">
              <div className="flex items-center gap-2">
                <Info size={14} className="text-slate-500" />
                <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">Financial Economics</h4>
              </div>
              <div className="text-[10px] font-black text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full border border-emerald-400/20">
                Live Delta
              </div>
            </div>
            <div className="p-3 grid gap-2">
              {[
                ["Contract Value", selectedTask.wo_value ?? 0, "INR"],
                ["Retention Hold", selectedTask.wo_retention_value ?? 0, "INR"],
                ["Certified to Date", selectedTask.payment_value ?? 0, "INR"],
                ["Cost Variation", (selectedTask.cost_variance ?? 0) === 0 ? "OPTIMAL" : selectedTask.cost_variance, "VAR"],
                ["Resource Density", (selectedTask.assigned_resources?.length ?? 0), "HEADS"],
              ].map(([label, value, unit]) => (
                <div key={label as string} className="flex flex-col gap-1 p-3 rounded-xl border border-white/5 bg-white/[0.01] hover:bg-white/[0.03] transition-colors">
                  <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500">
                    {label}
                  </span>
                  <div className="flex items-baseline gap-1.5">
                    <span className="text-sm font-black text-white italic">
                      {typeof value === 'number' ? formatCurrencySafe(value) : String(value)}
                    </span>
                    <span className="text-[9px] font-medium text-slate-700">{String(unit)}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-4 bg-orange-500/5 border-t border-white/5 text-[10px] text-orange-400/80 italic text-pretty leading-relaxed">
              * Economics are synchronized with the Procurement Ledger. Variations reflect site deviations from baseline estimates.
            </div>
          </div>
        </Tabs.Content>

        <Tabs.Content value="mom" className="space-y-4 pt-2">
          <div className="rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] p-4 text-pretty">
            <div className="flex items-center gap-2 mb-2">
              <Activity size={16} className="text-orange-400" />
              <h4 className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
                AI Tactics & MOM Notes
              </h4>
            </div>
            <p className="mb-4 text-[10px] uppercase tracking-[0.14em] text-slate-500 leading-relaxed">
              Feed raw site notes or meeting bullets to the AI Agent. It will reconcile
              durations and blockers into actionable schedule adjustments.
            </p>

            <div className="space-y-3">
              <textarea
                value={momNotes}
                onChange={(e) => setMomNotes(e.target.value)}
                className="w-full min-h-[160px] rounded-xl border border-white/5 bg-white/[0.03] p-4 text-[11px] font-medium text-white outline-none focus:border-orange-400/40 resize-none transition-all placeholder:text-slate-700 shadow-inner"
                placeholder="Ex: Discussed Pillar assembly. 4 days added due to curing time. Amit assigned to validation."
              />
              <Button
                type="button"
                disabled={!momNotes.trim() || isAnalyzingMom}
                onClick={handleAnalyzeMom}
                className="w-full rounded-xl bg-orange-600/10 text-orange-400 border border-orange-500/20 hover:bg-orange-500/20 py-6"
              >
                {isAnalyzingMom ? (
                  <Activity size={16} className="mr-3 animate-spin shadow-[0_0_15px_-3px_rgba(249,115,22,0.4)]" />
                ) : (
                  <Activity size={16} className="mr-3" />
                )}
                <span className="uppercase tracking-[0.2em] font-black text-xs">
                  {isAnalyzingMom ? "Syncing Intelligence..." : "Run AI Analysis"}
                </span>
              </Button>

              {momResult && (
                <div className="mt-6 space-y-3 animate-in fade-in slide-in-from-top-4 duration-500">
                  <div className="flex items-center justify-between border-b border-white/5 pb-1">
                    <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">Tactical Insights</p>
                    <div className="text-[8px] font-black text-emerald-400 flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                      Precision: {Math.round(momResult.confidence_score * 100)}%
                    </div>
                  </div>

                  <div className="grid gap-2">
                    {(momResult.action_items || []).map((item: ActionItem, idx: number) => (
                      <div key={idx} className="bg-white/[0.02] border border-white/5 p-3 rounded-xl">
                        <p className="text-white text-xs font-bold tracking-tight">{item.task_name}</p>
                        <div className="mt-2 flex justify-between text-[10px] uppercase font-black tracking-widest opacity-60">
                          <span className="text-orange-400">@{item.assignee || 'TBD'}</span>
                          <span className="text-slate-400 italic font-medium">BY {item.deadline || 'PENDING'}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl flex items-center justify-between">
                    <div>
                      <p className="text-[8px] font-black uppercase tracking-widest text-emerald-500/60 mb-1">Delta Shift</p>
                      <p className="text-sm text-emerald-400 font-black italic">
                        {momResult.suggested_duration_days} Days
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="bg-emerald-400/20 border-emerald-400/30 text-emerald-400 text-[10px] font-black hover:bg-emerald-400/30 px-4"
                      onClick={() => {
                        commit({ scheduled_duration: momResult.suggested_duration_days });
                        toast.success("AI suggestion committed to schedule.");
                      }}
                    >
                      COMMIT
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </Tabs.Content>

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
      </Tabs.Root>
    </aside>
  );
}
