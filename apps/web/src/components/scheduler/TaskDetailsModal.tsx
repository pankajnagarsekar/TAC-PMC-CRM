"use client";

import React, { useEffect, useMemo, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { X, Link2, Wallet, Activity, UserRoundPen, MessageSquare, Info, AlertCircle } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { SchedulePredecessor, ScheduleTask, ScheduleTaskStatus, MomResult } from "@/types/schedule.types";
import {
  getTaskStatus,
  KANBAN_META,
  VALID_STATUS_TRANSITIONS,
  buildTaskStatusTransition
} from "./scheduler-utils";
import { formatCurrencySafe } from "@/lib/formatters";
import { StyledDateInput } from "@/components/ui/StyledDateInput";

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

export default function TaskDetailsModal() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const isTaskModalOpen = useScheduleStore((state) => state.isTaskModalOpen);
  const setTaskModalOpen = useScheduleStore((state) => state.setTaskModalOpen);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
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

  // Local state for performance
  const [localTaskName, setLocalTaskName] = useState("");
  const [localDuration, setLocalDuration] = useState<number>(0);
  const [localPercent, setLocalPercent] = useState<number>(0);
  const [localParentId, setLocalParentId] = useState("");

  useEffect(() => {
    if (!selectedTask) return;
    setLocalTaskName(selectedTask.task_name || selectedTask.task_description || "");
    setLocalDuration(selectedTask.scheduled_duration ?? 0);
    setLocalPercent(selectedTask.percent_complete ?? 0);
    setLocalParentId(selectedTask.parent_id || "");
  }, [selectedTask]);

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

  if (!isTaskModalOpen || !selectedTask) return null;

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
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4"
      onClick={() => setTaskModalOpen(false)}
    >
      <div 
        className="bg-white dark:bg-slate-950 border border-slate-200 dark:border-white/10 rounded-[32px] max-w-4xl w-full shadow-2xl glass-panel-luxury overflow-hidden flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-200 dark:border-white/5 flex items-start justify-between bg-slate-50/50 dark:bg-white/[0.02]">
          <div>
            <div className="flex items-center gap-3">
               <div className={`h-3 w-3 rounded-full ${selectedTask.is_critical ? "bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.4)]" : "bg-sky-500 shadow-[0_0_10px_rgba(14,165,233,0.4)]"}`} />
               <h3 className="text-sm font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/80">Task Intel & Control</h3>
            </div>
            <p className="mt-1 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-500 flex items-center gap-2">
              <span className="text-orange-500">{selectedTask.wbs_code || selectedTask.task_id}</span>
              <span className="opacity-30">|</span>
              <span>Project Nexus v{selectedTask.version ?? 1}</span>
            </p>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-10 w-10 rounded-2xl text-slate-500 hover:text-slate-900 hover:bg-slate-200 dark:text-white/40 dark:hover:text-white dark:hover:bg-white/10 transition-all"
            onClick={() => setTaskModalOpen(false)}
          >
            <X size={20} />
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
          <Tabs.Root defaultValue="details" className="space-y-6">
            <Tabs.List className="flex gap-2 rounded-2xl border border-slate-200 dark:border-white/5 bg-slate-100/50 dark:bg-white/[0.02] p-1.5 overflow-x-auto no-scrollbar">
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
                    className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-[10px] font-black uppercase tracking-[0.14em] text-slate-400 transition-all data-[state=active]:bg-white dark:data-[state=active]:bg-white/10 data-[state=active]:text-slate-900 dark:data-[state=active]:text-white data-[state=active]:shadow-lg whitespace-nowrap"
                  >
                    <Icon size={14} />
                    <span>{item.label}</span>
                  </Tabs.Trigger>
                );
              })}
            </Tabs.List>

            <Tabs.Content value="details" className="space-y-6 outline-none">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Basic Info Card */}
                <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02] p-6 space-y-5">
                  <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 border-b border-slate-200 dark:border-white/5 pb-2">Core Registry</h4>
                  
                  <FieldRow label="Task name">
                    <input
                      value={localTaskName}
                      onChange={(e) => setLocalTaskName(e.target.value)}
                      onBlur={() => commit({ task_name: localTaskName })}
                      disabled={readOnly}
                      className={textInputClass()}
                      placeholder="Enter task definition..."
                    />
                  </FieldRow>

                  <div className="grid grid-cols-2 gap-4">
                    <FieldRow label="Execution Mode">
                      <select
                        value={selectedTask.task_mode ?? "Auto"}
                        onChange={(e) => commit({ task_mode: e.target.value as "Auto" | "Manual" })}
                        className={textInputClass()}
                        disabled={readOnly}
                      >
                        <option value="Auto">Auto (CPM)</option>
                        <option value="Manual">Manual</option>
                      </select>
                    </FieldRow>
                    <FieldRow label="Node Status">
                      <select
                        value={getTaskStatus(selectedTask)}
                        onChange={(event) => statusChange(event.target.value as ScheduleTaskStatus)}
                        disabled={readOnly}
                        className={textInputClass()}
                      >
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
                    </FieldRow>
                  </div>

                  <FieldRow label="Parent Unit ID">
                    <input
                      placeholder="example: task-42"
                      value={localParentId}
                      onChange={(e) => setLocalParentId(e.target.value)}
                      onBlur={() => commit({ parent_id: localParentId || null })}
                      disabled={readOnly}
                      className={textInputClass()}
                    />
                  </FieldRow>
                </div>

                {/* Timeline Card */}
                <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02] p-6 space-y-5">
                  <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 border-b border-slate-200 dark:border-white/5 pb-2">Temporal Schedule</h4>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <FieldRow label="Start Anchor">
                      <StyledDateInput
                        value={selectedTask.scheduled_start?.split("T")[0] ?? ""}
                        onChange={(event: React.ChangeEvent<HTMLInputElement>) => commit({ scheduled_start: event.target.value || null })}
                        disabled={readOnly}
                        hideIcon
                      />
                    </FieldRow>
                    <FieldRow label="Finish Anchor">
                      <StyledDateInput
                        value={selectedTask.scheduled_finish?.split("T")[0] ?? ""}
                        onChange={(event: React.ChangeEvent<HTMLInputElement>) => commit({ scheduled_finish: event.target.value || null })}
                        disabled={readOnly}
                        hideIcon
                      />
                    </FieldRow>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <FieldRow label="Critical Deadline">
                      <StyledDateInput
                        value={selectedTask.deadline?.split("T")[0] ?? ""}
                        onChange={(event: React.ChangeEvent<HTMLInputElement>) => commit({ deadline: event.target.value || null })}
                        disabled={readOnly}
                        hideIcon
                      />
                    </FieldRow>
                    <div className="flex items-end pb-1">
                      {selectedTask.deadline && new Date(selectedTask.deadline) < new Date(new Date().toDateString()) && (
                        <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-orange-500/10 border border-orange-500/20 text-[10px] font-black text-orange-400 uppercase tracking-tight animate-pulse">
                          <AlertCircle size={12} /> Violation
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <FieldRow label="Duration (Days)">
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
                    <FieldRow label="Completion %">
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
                </div>
              </div>
            </Tabs.Content>

            <Tabs.Content value="deps" className="space-y-6 outline-none">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02] p-6">
                    <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 mb-4">Established Network</h4>
                    <div className="space-y-3">
                      {(selectedTask.predecessors ?? []).length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-slate-200 dark:border-white/10 p-8 text-center bg-white/5">
                          <Link2 size={24} className="mx-auto text-slate-300 dark:text-white/10 mb-2" />
                          <p className="text-[10px] uppercase tracking-[0.1em] text-slate-500 font-bold">No network links established</p>
                        </div>
                      ) : (
                        (selectedTask.predecessors ?? []).map((dep) => (
                          <div
                            key={`${dep.task_id}-${dep.type}-${dep.lag_days ?? 0}`}
                            className="rounded-2xl border border-slate-200 dark:border-white/5 bg-white dark:bg-white/[0.03] px-4 py-3 flex items-center justify-between group hover:border-sky-400/30 transition-all"
                          >
                            <div className="flex items-center gap-3">
                               <div className="h-8 w-8 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400 font-black text-[10px]">
                                  {dep.type}
                               </div>
                               <div>
                                  <p className="text-xs font-black uppercase tracking-widest text-slate-900 dark:text-white">{dep.task_id}</p>
                                  <p className="text-[9px] uppercase tracking-wider text-slate-500">Lag: {dep.lag_days ?? 0} days</p>
                               </div>
                            </div>
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              className="h-8 w-8 rounded-lg opacity-0 group-hover:opacity-100 text-rose-500 hover:bg-rose-500/10"
                              onClick={() => {
                                const next = (selectedTask.predecessors ?? []).filter(p => !(p.task_id === dep.task_id && p.type === dep.type));
                                commit({ predecessors: next });
                                toast.success("Link removed.");
                              }}
                            >
                               <X size={14} />
                            </Button>
                          </div>
                        ))
                      )}
                    </div>
                 </div>

                 <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02] p-6 space-y-5">
                    <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">Link New Node</h4>
                    <FieldRow label="Target Task ID">
                      <input
                        value={dependencyTaskId}
                        onChange={(event) => setDependencyTaskId(event.target.value)}
                        disabled={readOnly}
                        className={textInputClass()}
                        placeholder="example: task-42"
                      />
                    </FieldRow>
                    <div className="grid grid-cols-2 gap-4">
                      <FieldRow label="Logic Link Type">
                        <select
                          value={dependencyType}
                          onChange={(event) => setDependencyType(event.target.value as SchedulePredecessor["type"])}
                          disabled={readOnly}
                          className={textInputClass()}
                        >
                          <option value="FS">Finish-to-Start</option>
                          <option value="SS">Start-to-Start</option>
                          <option value="FF">Finish-to-Finish</option>
                          <option value="SF">Start-to-Finish</option>
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
                      className="w-full rounded-2xl bg-sky-500/10 text-sky-400 border border-sky-500/20 hover:bg-sky-500/20 py-6 uppercase tracking-[0.2em] font-black text-xs"
                    >
                      Establish Network Link
                    </Button>
                 </div>
              </div>
            </Tabs.Content>

            <Tabs.Content value="financials" className="space-y-6 outline-none">
               <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {[
                    { label: "Contract Value", value: selectedTask.wo_value ?? 0, unit: "INR", icon: Wallet, color: "text-emerald-500" },
                    { label: "Retention Hold", value: selectedTask.wo_retention_value ?? 0, unit: "INR", icon: Info, color: "text-amber-500" },
                    { label: "Certified Value", value: selectedTask.payment_value ?? 0, unit: "INR", icon: Activity, color: "text-sky-500" },
                    { label: "Cost Variation", value: selectedTask.cost_variance ?? 0, unit: "VAR", icon: AlertCircle, color: selectedTask.cost_variance && selectedTask.cost_variance > 0 ? "text-rose-500" : "text-emerald-500" },
                    { label: "Resource Density", value: selectedTask.assigned_resources?.length ?? 0, unit: "HEADS", icon: UserRoundPen, color: "text-indigo-500" },
                    { label: "Weightage", value: (selectedTask.weightage_percent ?? 0).toFixed(2), unit: "%", icon: Activity, color: "text-violet-500" },
                  ].map((item) => (
                    <div key={item.label} className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.02] p-5 flex flex-col gap-3 group hover:border-white/10 transition-all">
                       <div className="flex items-center justify-between">
                          <span className="text-[9px] font-black uppercase tracking-[0.2em] text-slate-500">{item.label}</span>
                          <item.icon size={12} className={item.color} />
                       </div>
                       <div className="flex items-baseline gap-2">
                          <span className="text-xl font-black text-slate-900 dark:text-white italic tracking-tight">
                             {typeof item.value === 'number' ? formatCurrencySafe(item.value) : item.value}
                          </span>
                          <span className="text-[10px] font-bold text-slate-400">{item.unit}</span>
                       </div>
                    </div>
                  ))}
               </div>
               <div className="rounded-2xl bg-orange-500/5 border border-orange-500/10 p-5">
                  <p className="text-[10px] text-orange-600/80 dark:text-orange-400/80 italic leading-relaxed text-center">
                    * Financial metrics are derived from the Procurement Ledger and reconciled against site progress.
                  </p>
               </div>
            </Tabs.Content>

            <Tabs.Content value="mom" className="space-y-6 outline-none">
              <div className="max-w-3xl mx-auto space-y-6">
                 <div className="text-center space-y-2">
                    <h4 className="text-xs font-black uppercase tracking-[0.3em] text-slate-900 dark:text-white/80">Tactical Intelligence</h4>
                    <p className="text-[10px] uppercase tracking-[0.16em] text-slate-500">Transform field notes into schedule adjustments using GPT-4 Reasoning</p>
                 </div>

                 <textarea
                    value={momNotes}
                    onChange={(e) => setMomNotes(e.target.value)}
                    className="w-full min-h-[200px] rounded-[32px] border border-slate-200 dark:border-white/5 bg-slate-50/80 dark:bg-white/[0.02] p-8 text-sm font-medium text-slate-900 dark:text-white outline-none focus:border-orange-400/40 resize-none transition-all placeholder:text-slate-400 dark:placeholder:text-slate-700 shadow-inner"
                    placeholder="Capture raw site updates: 'Work slowed due to rain, added 2 days for slab curing...'"
                  />

                  <Button
                    type="button"
                    disabled={!momNotes.trim() || isAnalyzingMom}
                    onClick={handleAnalyzeMom}
                    className="w-full rounded-[24px] bg-orange-600/10 text-orange-400 border border-orange-500/20 hover:bg-orange-500/20 py-8 group transition-all"
                  >
                    {isAnalyzingMom ? (
                      <Activity size={20} className="mr-3 animate-spin shadow-orange-500/40" />
                    ) : (
                      <Activity size={20} className="mr-3 group-hover:scale-110 transition-transform" />
                    )}
                    <span className="uppercase tracking-[0.25em] font-black text-sm">
                      {isAnalyzingMom ? "Processing Intelligence..." : "Initialize AI Extraction"}
                    </span>
                  </Button>

                  {momResult && (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
                       <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/5 pb-2">
                          <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Extracted Action Registry</p>
                          <div className="text-[10px] font-black text-emerald-400 flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            AI Confidence: {Math.round(momResult.confidence_score * 100)}%
                          </div>
                       </div>

                       <div className="grid gap-3">
                          {(momResult.action_items || []).map((item, idx) => (
                            <div key={idx} className="bg-white dark:bg-white/[0.03] border border-slate-200 dark:border-white/5 p-4 rounded-2xl flex items-center justify-between">
                               <div>
                                  <p className="text-slate-900 dark:text-white text-xs font-bold tracking-tight">{item.task_name}</p>
                                  <p className="text-[10px] uppercase font-black tracking-widest text-orange-400 mt-1">@{item.assignee || 'TBD'}</p>
                               </div>
                               <span className="text-[10px] font-bold text-slate-400 bg-slate-100 dark:bg-white/5 px-3 py-1 rounded-full">{item.deadline || 'PENDING'}</span>
                            </div>
                          ))}
                       </div>

                       <div className="p-6 bg-emerald-500/10 border border-emerald-500/20 rounded-[28px] flex items-center justify-between shadow-xl">
                          <div>
                            <p className="text-[9px] font-black uppercase tracking-widest text-emerald-500/60 mb-1">Schedule Shift Prediction</p>
                            <p className="text-2xl text-emerald-400 font-black italic tracking-tighter">
                              +{momResult.suggested_duration_days} Working Days
                            </p>
                          </div>
                          <Button
                            variant="default"
                            className="bg-emerald-500 text-white rounded-2xl px-8 py-6 font-black uppercase tracking-widest text-[10px] shadow-lg shadow-emerald-500/20 hover:scale-105 transition-all"
                            onClick={() => {
                              commit({ scheduled_duration: momResult.suggested_duration_days });
                              toast.success("Schedule updated with AI insights.");
                            }}
                          >
                            COMMIT DELTA
                          </Button>
                       </div>
                    </div>
                  )}
              </div>
            </Tabs.Content>

            <Tabs.Content value="logs" className="space-y-6 outline-none">
               <div className="max-w-2xl mx-auto py-12 text-center space-y-6">
                  <div className="h-20 w-20 rounded-full bg-slate-100 dark:bg-white/[0.02] border border-slate-200 dark:border-white/5 flex items-center justify-center mx-auto shadow-inner">
                     <Activity size={32} className="text-slate-300 dark:text-white/10" />
                  </div>
                  <div className="space-y-2">
                     <h4 className="text-xs font-black uppercase tracking-[0.3em] text-slate-900 dark:text-white/80">Registry Synchronization</h4>
                     <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500 leading-relaxed mx-auto max-w-md">
                        Operational logs, labour attendance, and material reconciliations live within the 
                        <span className="text-indigo-400 font-black"> Site Operations Module</span>.
                     </p>
                  </div>
                  <Link
                    href={`/admin/site-operations?tab=attendance&task=${selectedTask.task_id}`}
                    className="inline-flex items-center gap-3 rounded-2xl bg-indigo-500 text-white px-8 py-4 font-black uppercase tracking-widest text-[10px] shadow-xl shadow-indigo-500/20 hover:scale-105 transition-all"
                  >
                    Launch Site Operations Registry <UserRoundPen size={14} />
                  </Link>
               </div>
            </Tabs.Content>
          </Tabs.Root>
        </div>

        {/* Footer info */}
        <div className="px-8 py-4 bg-slate-50/50 dark:bg-white/[0.01] border-t border-slate-200 dark:border-white/5 flex justify-between items-center">
           <div className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">
              Last Synced: {new Date().toLocaleTimeString()}
           </div>
           <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-tight text-emerald-500">
                 <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                 Encrypted Tunnel
              </div>
              <div className="flex items-center gap-1.5 text-[9px] font-black uppercase tracking-tight text-sky-500">
                 <div className="h-1.5 w-1.5 rounded-full bg-sky-500" />
                 Z-Buffer Ready
              </div>
           </div>
        </div>
      </div>
    </div>
  );
}
