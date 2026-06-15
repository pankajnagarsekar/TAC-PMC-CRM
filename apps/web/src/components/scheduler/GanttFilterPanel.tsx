"use client";

import React, { useMemo } from "react";
import { Filter, RotateCcw, AlertTriangle, Users, Minimize2, Maximize2 } from "lucide-react";
import useSWR from "swr";
import { identityApi } from "@/lib/api";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTaskStatus } from "@/types/schedule.types";
import { KANBAN_META } from "./scheduler-utils";

interface GanttFilterPanelProps {
  onClose?: () => void;
}

export default function GanttFilterPanel({ onClose }: GanttFilterPanelProps) {
  const activeFilters = useScheduleStore((state) => state.activeFilters);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const setSearchTerm = useScheduleStore((state) => state.setSearchTerm);
  const setStatusFilter = useScheduleStore((state) => state.setStatusFilter);
  const setMilestonesOnly = useScheduleStore((state) => state.setMilestonesOnly);
  const setCriticalOnly = useScheduleStore((state) => state.setCriticalOnly);
  const setDelayedOnly = useScheduleStore((state) => state.setDelayedOnly);
  const setResourceFilter = useScheduleStore((state) => state.setResourceFilter);
  const expandAll = useScheduleStore((state) => state.expandAll);
  const collapseAll = useScheduleStore((state) => state.collapseAll);
  const batchConvertSchedulingMode = useScheduleStore((state) => state.batchConvertSchedulingMode);
  const systemState = useScheduleStore((state) => state.systemState);

  const { data: usersResponse } = useSWR("/api/v1/users/", () => identityApi.listUsers());
  const users = useMemo(() => usersResponse?.data || usersResponse || [], [usersResponse]);

  const handleStatusToggle = (status: ScheduleTaskStatus) => {
    const current = activeFilters.statusFilter || [];
    const next = current.includes(status)
      ? current.filter((s) => s !== status)
      : [...current, status];
    setStatusFilter(next);
  };

  const clearAllFilters = () => {
    setSearchTerm("");
    setStatusFilter([]);
    setMilestonesOnly(false);
    setCriticalOnly(false);
    setDelayedOnly(false);
    setResourceFilter("");
  };

  const hasActiveFilters = Boolean(
    activeFilters.searchTerm ||
    (activeFilters.statusFilter && activeFilters.statusFilter.length > 0) ||
    activeFilters.milestonesOnly ||
    activeFilters.criticalOnly ||
    activeFilters.delayedOnly ||
    activeFilters.resourceFilter
  );

  return (
    <div className="relative border border-slate-200 dark:border-white/5 bg-white/70 dark:bg-slate-900/80 backdrop-blur-md rounded-3xl p-6 shadow-2xl transition-all animate-in fade-in duration-300">
      <div className="flex items-center justify-between border-b border-slate-200 dark:border-white/5 pb-4 mb-4">
        <div className="flex items-center gap-2">
          <Filter size={14} className="text-orange-500" />
          <h4 className="text-xs font-black uppercase tracking-[0.2em] text-slate-800 dark:text-slate-200">
            Diagnostics & View Filters
          </h4>
        </div>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="flex items-center gap-1 px-3 py-1 text-[9px] font-black uppercase tracking-wider text-slate-500 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-white/5 hover:bg-slate-200 dark:hover:bg-white/10 rounded-xl transition-colors cursor-pointer"
            >
              <RotateCcw size={10} />
              Reset Filters
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-900 dark:hover:text-white text-[9px] font-black uppercase tracking-wider px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-white/5 cursor-pointer"
            >
              Close
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Search & Resource */}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 block">
              Global Filter Query
            </label>
            <input
              type="text"
              placeholder="Search ID, WBS, or Task Name..."
              value={activeFilters.searchTerm || ""}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100/50 dark:bg-white/[0.03] px-3.5 py-2 text-xs font-semibold text-slate-900 dark:text-white outline-none focus:border-orange-500/40 transition-all placeholder:text-slate-400"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 block">
              Responsible Person
            </label>
            <div className="relative">
              <Users size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
              <select
                value={activeFilters.resourceFilter || ""}
                onChange={(e) => setResourceFilter(e.target.value)}
                className="w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100/50 dark:bg-white/[0.03] pl-9 pr-3.5 py-2 text-xs font-semibold text-slate-900 dark:text-white outline-none focus:border-orange-500/40 transition-all cursor-pointer"
              >
                <option value="" className="bg-slate-900 text-white">All Resources</option>
                {users.map((u: { id: string; user_id?: string; full_name?: string; email?: string }) => (
                  <option key={u.user_id || u.id} value={u.user_id || u.id} className="bg-slate-900 text-white">
                    {u.full_name || u.email}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Status filters */}
        <div className="space-y-2">
          <label className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 block mb-1">
            Status Grouping
          </label>
          <div className="grid grid-cols-2 gap-2">
            {(Object.keys(KANBAN_META) as ScheduleTaskStatus[]).map((status) => {
              const meta = KANBAN_META[status];
              const isChecked = (activeFilters.statusFilter || []).includes(status);
              return (
                <button
                  key={status}
                  onClick={() => handleStatusToggle(status)}
                  className={`flex items-center gap-2 px-3 py-2 text-[10px] font-bold uppercase tracking-wider rounded-xl border transition-all cursor-pointer ${
                    isChecked
                      ? "bg-slate-900/10 dark:bg-white/5 border-orange-500/50 text-slate-900 dark:text-white shadow-[0_0_12px_rgba(249,115,22,0.15)]"
                      : "bg-transparent border-slate-200 dark:border-white/5 text-slate-500 hover:text-slate-900 dark:hover:text-white"
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${meta.tone.split(" ")[0].replace("text-", "bg-")}`} />
                  {meta.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Quick Diagnostic Toggles */}
        <div className="space-y-3">
          <label className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 block mb-1">
            Diagnostic Overlays
          </label>

          <div className="space-y-2.5">
            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 group-hover:text-slate-800 dark:text-slate-400 dark:group-hover:text-white transition-colors">
                Milestones Only
              </span>
              <input
                type="checkbox"
                checked={Boolean(activeFilters.milestonesOnly)}
                onChange={(e) => setMilestonesOnly(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-orange-600 focus:ring-orange-500 dark:border-white/10 dark:bg-white/5 cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 group-hover:text-slate-800 dark:text-slate-400 dark:group-hover:text-white transition-colors flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 rounded-full bg-rose-500" />
                Critical Path Only
              </span>
              <input
                type="checkbox"
                checked={Boolean(activeFilters.criticalOnly)}
                onChange={(e) => setCriticalOnly(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-orange-600 focus:ring-orange-500 dark:border-white/10 dark:bg-white/5 cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer group">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 group-hover:text-slate-800 dark:text-slate-400 dark:group-hover:text-white transition-colors flex items-center gap-1.5">
                <AlertTriangle size={12} className="text-orange-500" />
                Slipped & Delayed
              </span>
              <input
                type="checkbox"
                checked={Boolean(activeFilters.delayedOnly)}
                onChange={(e) => setDelayedOnly(e.target.checked)}
                className="w-4 h-4 rounded border-slate-300 text-orange-600 focus:ring-orange-500 dark:border-white/10 dark:bg-white/5 cursor-pointer"
              />
            </label>
          </div>
        </div>

        {/* Global actions (WBS / Scheduling Mode) */}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 block">
              WBS Hierarchy Controls
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={expandAll}
                className="flex items-center justify-center gap-1.5 px-3 py-2 text-[9px] font-black uppercase tracking-wider text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl hover:bg-slate-200 dark:hover:bg-white/10 transition-colors cursor-pointer"
                title="Expand all summary tasks and show descendants"
              >
                <Maximize2 size={10} />
                Expand All
              </button>
              <button
                onClick={collapseAll}
                className="flex items-center justify-center gap-1.5 px-3 py-2 text-[9px] font-black uppercase tracking-wider text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl hover:bg-slate-200 dark:hover:bg-white/10 transition-colors cursor-pointer"
                title="Collapse all parents to level 1"
              >
                <Minimize2 size={10} />
                Collapse All
              </button>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 block">
              Batch Scheduler Mode
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                disabled={selectedTasks.size === 0 || systemState === "locked"}
                onClick={() => batchConvertSchedulingMode(Array.from(selectedTasks), "Auto")}
                className="flex items-center justify-center gap-1 px-3 py-2 text-[9px] font-black uppercase tracking-wider text-sky-400 disabled:opacity-40 bg-sky-500/10 hover:bg-sky-500/20 disabled:hover:bg-sky-500/10 rounded-xl border border-sky-400/20 transition-colors cursor-pointer"
                title="Convert selected tasks to automatic scheduling mode"
              >
                Auto-Schedule
              </button>
              <button
                disabled={selectedTasks.size === 0 || systemState === "locked"}
                onClick={() => batchConvertSchedulingMode(Array.from(selectedTasks), "Manual")}
                className="flex items-center justify-center gap-1 px-3 py-2 text-[9px] font-black uppercase tracking-wider text-amber-400 disabled:opacity-40 bg-amber-500/10 hover:bg-amber-500/20 disabled:hover:bg-amber-500/10 rounded-xl border border-amber-400/20 transition-colors cursor-pointer"
                title="Lock dates and convert selected tasks to manual scheduling mode"
              >
                Manually Lock
              </button>
            </div>
            {selectedTasks.size > 0 ? (
              <p className="text-[8px] text-orange-400 font-bold uppercase tracking-tighter text-center mt-1">
                Applies to {selectedTasks.size} selected task(s)
              </p>
            ) : (
              <p className="text-[8px] text-slate-500 uppercase tracking-tighter text-center mt-1">
                Select tasks in row sheets first
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
