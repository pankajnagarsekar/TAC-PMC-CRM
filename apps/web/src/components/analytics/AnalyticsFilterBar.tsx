"use client";

import React, { useMemo, useEffect, useRef } from "react";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import AnalyticsChartSelector from "./AnalyticsChartSelector";
import { 
  RotateCcw, 
  Calendar, 
  Layers, 
  SlidersHorizontal 
} from "lucide-react";
import type { ScheduleTaskStatus } from "@/types/schedule.types";

const ANALYTICAL_STATUSES: { value: string; label: string; tone: string }[] = [
  { value: "not_started", label: "Not Started", tone: "bg-zinc-400 text-zinc-300 border-zinc-500/20 bg-zinc-500/10" },
  { value: "in_progress", label: "In Progress", tone: "bg-amber-500 text-amber-300 border-amber-500/20 bg-amber-500/10" },
  { value: "delayed", label: "Delayed", tone: "bg-rose-500 text-rose-300 border-rose-500/20 bg-rose-500/10" },
  { value: "completed", label: "Completed", tone: "bg-emerald-500 text-emerald-300 border-emerald-500/20 bg-emerald-500/10" },
  { value: "on_hold", label: "On Hold", tone: "bg-indigo-500 text-indigo-300 border-indigo-500/20 bg-indigo-500/10" },
  { value: "cancelled", label: "Cancelled", tone: "bg-pink-500 text-pink-300 border-pink-500/20 bg-pink-500/10" },
];

export default function AnalyticsFilterBar() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const tasks = useMemo(() => Object.values(taskMap), [taskMap]);

  const filters = useAnalyticsStore((state) => state.filters);
  const setFilter = useAnalyticsStore((state) => state.setFilter);
  const resetFilters = useAnalyticsStore((state) => state.resetFilters);
  const selectedChart = useAnalyticsStore((state) => state.selectedChart);
  const isMoreFiltersOpen = useAnalyticsStore((state) => state.isMoreFiltersOpen);
  const setMoreFiltersOpen = useAnalyticsStore((state) => state.setMoreFiltersOpen);

  const filterBarRef = useRef<HTMLDivElement>(null);

  // Click outside and keydown Escape overlay dismissal hook
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (filterBarRef.current && !filterBarRef.current.contains(event.target as Node)) {
        setMoreFiltersOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMoreFiltersOpen(false);
      }
    };

    if (isMoreFiltersOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isMoreFiltersOpen, setMoreFiltersOpen]);

  // Derive filter options dynamically from tasks
  const assigneesList = useMemo(() => {
    const names = new Set<string>();
    tasks.forEach(t => {
      t.assignee_details?.forEach(d => { if (d.name) names.add(d.name); });
      t.assigned_resources?.forEach(r => { if (r) names.add(r); });
      const singleAssignee = (t.assignee || t.owner || t.responsible || t.assigned_to_name) as string | undefined;
      if (typeof singleAssignee === "string" && singleAssignee.trim()) {
        names.add(singleAssignee.trim());
      }
    });
    return Array.from(names).sort();
  }, [tasks]);

  // ANL-018: Resolve numbered/WBS code departments to human-readable root task names
  const departmentsList = useMemo(() => {
    const rootTaskMap = new Map<string, string>();
    tasks.forEach(t => {
      if (t.wbs_code && !t.wbs_code.includes('.')) {
        rootTaskMap.set(t.wbs_code, t.task_name || (t as any).name || t.task_id);
      }
    });

    const depts = new Set<string>();
    tasks.forEach(t => {
      const rootCode = t.wbs_code?.split('.')[0];
      if (!rootCode) {
        depts.add('Misc');
        return;
      }
      let name = rootCode === 'C' ? 'Construction' :
                 rootCode === 'P' ? 'Contracting' :
                 rootCode === 'D' ? 'Design/Engineering' :
                 rootCode === 'S' ? 'Site Ops' :
                 rootCode === 'I' ? 'Interiors' : '';
      if (!name) {
        name = rootTaskMap.get(rootCode) || rootCode;
      }
      depts.add(name);
    });
    return Array.from(depts).sort((a, b) => {
      const aNum = parseInt(a, 10);
      const bNum = parseInt(b, 10);
      const isANum = !isNaN(aNum);
      const isBNum = !isNaN(bNum);
      if (isANum && isBNum) {
        return aNum - bNum;
      }
      if (isANum) return -1;
      if (isBNum) return 1;
      return a.localeCompare(b);
    });
  }, [tasks]);

  const vendorsList = useMemo(() => {
    const vendors = new Set<string>();
    tasks.forEach(t => {
      t.assigned_resources?.forEach(r => { if (r) vendors.add(r); });
    });
    return Array.from(vendors).sort();
  }, [tasks]);

  // Is cost-related chart?
  const isCostChart = ['s_curve', 'cost_overview', 'earned_value', 'cash_flow'].includes(selectedChart);

  // Check if filters are dirty
  const isDirty = useMemo(() => {
    return filters.dateRange !== 'full_project' ||
           filters.timeBucket !== 'monthly' ||
           filters.viewLevel !== 'project' ||
           filters.criticalOnly ||
           filters.milestonesOnly ||
           filters.costEnabled ||
           filters.comparePrevious ||
           (filters.statusFilter && filters.statusFilter.length > 0) ||
           (filters.assigneeFilter && filters.assigneeFilter.length > 0) ||
           (filters.vendorFilter && filters.vendorFilter.length > 0) ||
           (filters.departmentFilter && filters.departmentFilter.length > 0);
  }, [filters]);

  const toggleStatusFilter = (status: ScheduleTaskStatus) => {
    const current = filters.statusFilter || [];
    if (current.includes(status)) {
      setFilter("statusFilter", current.filter(s => s !== status));
    } else {
      setFilter("statusFilter", [...current, status]);
    }
  };

  const toggleAssigneeFilter = (name: string) => {
    const current = filters.assigneeFilter || [];
    if (current.includes(name)) {
      setFilter("assigneeFilter", current.filter(n => n !== name));
    } else {
      setFilter("assigneeFilter", [...current, name]);
    }
  };

  const toggleDepartmentFilter = (dept: string) => {
    const current = filters.departmentFilter || [];
    if (current.includes(dept)) {
      setFilter("departmentFilter", current.filter(d => d !== dept));
    } else {
      setFilter("departmentFilter", [...current, dept]);
    }
  };

  const toggleVendorFilter = (vendor: string) => {
    const current = filters.vendorFilter || [];
    if (current.includes(vendor)) {
      setFilter("vendorFilter", current.filter(v => v !== vendor));
    } else {
      setFilter("vendorFilter", [...current, vendor]);
    }
  };

  return (
    <div ref={filterBarRef} className="relative z-30 space-y-4">
      {/* Primary Row */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-2xl border border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-950/40 backdrop-blur-md">
        <div className="flex flex-wrap items-center gap-3">
          {/* Chart Dropdown */}
          <AnalyticsChartSelector />

          {/* Date Range Dropdown */}
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-1">
            <Calendar size={12} className="text-slate-400" />
            <select
              value={filters.dateRange}
              onChange={(e) => setFilter("dateRange", e.target.value as any)}
              className="bg-transparent text-[10px] font-black uppercase tracking-widest text-slate-700 dark:text-slate-200 outline-none py-1.5 cursor-pointer [&>option]:bg-white dark:[&>option]:bg-slate-900 [&>option]:text-slate-900 dark:[&>option]:text-white"
            >
              <option value="full_project">Full Project</option>
              <option value="this_month">This Month</option>
              <option value="next_30">Next 30 Days</option>
              <option value="quarter">This Quarter</option>
              <option value="custom">Custom Date…</option>
            </select>
          </div>

          {/* Inline Custom Date Picker Inputs */}
          {filters.dateRange === "custom" && (
            <div className="flex items-center gap-2 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-1.5 animate-in slide-in-from-left duration-300">
              <input
                type="date"
                aria-label="Start Date"
                value={filters.customDateStart || ""}
                onChange={(e) => setFilter("customDateStart", e.target.value)}
                className="bg-transparent text-[10px] font-bold text-slate-700 dark:text-slate-200 outline-none cursor-pointer"
              />
              <span className="text-[9px] font-black text-slate-400">TO</span>
              <input
                type="date"
                aria-label="End Date"
                value={filters.customDateEnd || ""}
                onChange={(e) => setFilter("customDateEnd", e.target.value)}
                className="bg-transparent text-[10px] font-bold text-slate-700 dark:text-slate-200 outline-none cursor-pointer"
              />
            </div>
          )}

          {/* Time Bucket Group (Daily/Weekly/Monthly) */}
          <div className="flex rounded-xl bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 p-1">
            {(['daily', 'weekly', 'monthly'] as const).map((bucket) => (
              <button
                type="button"
                key={bucket}
                onClick={() => setFilter("timeBucket", bucket)}
                className={`px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest transition-all ${
                  filters.timeBucket === bucket
                    ? "bg-orange-600 dark:bg-orange-500 text-white shadow-md"
                    : "text-slate-500 hover:text-slate-900 dark:hover:text-white"
                }`}
              >
                {bucket}
              </button>
            ))}
          </div>

          {/* View Level Dropdown */}
          <div className="flex items-center gap-1 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl px-3 py-1">
            <Layers size={12} className="text-slate-400" />
            <select
              value={filters.viewLevel}
              onChange={(e) => setFilter("viewLevel", e.target.value as any)}
              className="bg-transparent text-[10px] font-black uppercase tracking-widest text-slate-700 dark:text-slate-200 outline-none py-1.5 cursor-pointer [&>option]:bg-white dark:[&>option]:bg-slate-900 [&>option]:text-slate-900 dark:[&>option]:text-white"
            >
              <option value="project">Project Level</option>
              <option value="phase">Phase Level</option>
              <option value="task_group">Task Group</option>
              <option value="wbs">WBS Code</option>
            </select>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Advanced Filters Button */}
          <button
            type="button"
            onClick={() => setMoreFiltersOpen(!isMoreFiltersOpen)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-[10px] font-black uppercase tracking-widest ${
              isMoreFiltersOpen || (filters.statusFilter && filters.statusFilter.length > 0)
                ? "bg-orange-500/10 border-orange-500/30 text-orange-600 dark:text-orange-400"
                : "bg-slate-100 dark:bg-white/5 border-slate-200 dark:border-white/10 text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <SlidersHorizontal size={12} />
            <span>More Filters</span>
          </button>

          {/* Reset Filters */}
          {isDirty && (
            <button
              type="button"
              onClick={resetFilters}
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 border border-rose-500/20 text-[10px] font-black uppercase tracking-widest transition-all"
            >
              <RotateCcw size={12} />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* Collapsible Advanced Filters Panel */}
      {isMoreFiltersOpen && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-5 rounded-2xl border border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-950/40 backdrop-blur-md animate-in slide-in-from-top-4 duration-300">
          
          {/* Status Filter */}
          <div className="space-y-2">
            <h4 className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30">Statuses</h4>
            <div className="grid grid-cols-2 gap-1.5">
              {ANALYTICAL_STATUSES.map((status) => {
                const isActive = filters.statusFilter?.includes(status.value);
                return (
                  <button
                    type="button"
                    key={status.value}
                    onClick={() => toggleStatusFilter(status.value as any)}
                    className={`flex items-center gap-2 p-2 rounded-xl text-[9px] font-black uppercase tracking-widest border transition-all ${
                      isActive
                        ? "bg-orange-500/10 border-orange-500/25 text-orange-600 dark:text-orange-400 font-bold"
                        : "bg-slate-100/40 dark:bg-white/5 border-slate-200/50 dark:border-white/5 text-slate-600 dark:text-slate-400 hover:bg-slate-100"
                    }`}
                  >
                    <div className={`w-1.5 h-1.5 rounded-full ${status.tone.split(' ')[0]}`} />
                    <span className="truncate">{status.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Department Filter */}
          <div className="space-y-2">
            <h4 className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30">Departments</h4>
            <div className="flex flex-wrap gap-1.5">
              {departmentsList.map((dept) => {
                const isActive = filters.departmentFilter?.includes(dept);
                return (
                  <button
                    type="button"
                    key={dept}
                    onClick={() => toggleDepartmentFilter(dept)}
                    className={`px-2.5 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest border transition-all ${
                      isActive
                        ? "bg-orange-500/10 border-orange-500/25 text-orange-600 dark:text-orange-400"
                        : "bg-slate-100/40 dark:bg-white/5 border-slate-200/50 dark:border-white/5 text-slate-600 dark:text-slate-400"
                    }`}
                  >
                    {dept}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Assignee Filter */}
          <div className="space-y-2">
            <h4 className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30">Owners & Assignees</h4>
            <div className="flex flex-wrap gap-1.5 max-h-[85px] overflow-y-auto pr-1">
              {assigneesList.map((name) => {
                const isActive = filters.assigneeFilter?.includes(name);
                return (
                  <button
                    type="button"
                    key={name}
                    onClick={() => toggleAssigneeFilter(name)}
                    className={`px-2.5 py-1.5 rounded-xl text-[9px] font-black uppercase tracking-widest border transition-all ${
                      isActive
                        ? "bg-orange-500/10 border-orange-500/25 text-orange-600 dark:text-orange-400"
                        : "bg-slate-100/40 dark:bg-white/5 border-slate-200/50 dark:border-white/5 text-slate-600 dark:text-slate-400"
                    }`}
                  >
                    {name}
                  </button>
                );
              })}
              {assigneesList.length === 0 && <span className="text-[9px] text-slate-400 italic">No assignees available</span>}
            </div>
          </div>

          {/* Toggles & Options */}
          <div className="space-y-2">
            <h4 className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30">Analysis Flags</h4>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 p-2 rounded-xl bg-slate-100/40 dark:bg-white/5 border border-slate-200/50 dark:border-white/5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.criticalOnly}
                  onChange={(e) => setFilter("criticalOnly", e.target.checked)}
                  className="rounded border-slate-300 dark:border-white/10 text-orange-600 accent-orange-500"
                />
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400">Critical Only</span>
              </label>

              <label className="flex items-center gap-2 p-2 rounded-xl bg-slate-100/40 dark:bg-white/5 border border-slate-200/50 dark:border-white/5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.milestonesOnly}
                  onChange={(e) => setFilter("milestonesOnly", e.target.checked)}
                  className="rounded border-slate-300 dark:border-white/10 text-orange-600 accent-orange-500"
                />
                <span className="text-[9px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400">Milestones Only</span>
              </label>

              {isCostChart && (
                <label className="flex items-center gap-2 p-2 rounded-xl bg-slate-100/40 dark:bg-white/5 border border-slate-200/50 dark:border-white/5 cursor-pointer col-span-2">
                  <input
                    type="checkbox"
                    checked={filters.costEnabled}
                    onChange={(e) => setFilter("costEnabled", e.target.checked)}
                    className="rounded border-slate-300 dark:border-white/10 text-orange-600 accent-orange-500"
                  />
                  <span className="text-[9px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400">Include Cost Series</span>
                </label>
              )}

              {/* Baseline Version and Compare Toggle Section */}
              <div className="col-span-2 space-y-2 mt-2 pt-2 border-t border-slate-200 dark:border-white/5">
                <span className="text-[8px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30 block">EVM Baseline Context</span>
                <div className="grid grid-cols-2 gap-2">
                  <div className="flex items-center gap-1 bg-slate-100/40 dark:bg-white/5 border border-slate-200/50 dark:border-white/5 rounded-xl px-2 py-1">
                    <span className="text-[8px] font-black text-slate-400">VER:</span>
                    <select
                      value={filters.baselineVersion || 1}
                      onChange={(e) => setFilter("baselineVersion", Number(e.target.value))}
                      className="bg-transparent text-[9px] font-black uppercase tracking-widest text-slate-700 dark:text-slate-200 outline-none w-full cursor-pointer [&>option]:bg-slate-900"
                    >
                      <option value={1}>Baseline v1</option>
                      <option value={2}>Baseline v2</option>
                      <option value={3}>Baseline v3</option>
                    </select>
                  </div>

                  <label className="flex items-center gap-2 p-1.5 rounded-xl bg-slate-100/40 dark:bg-white/5 border border-slate-200/50 dark:border-white/5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.comparePrevious}
                      onChange={(e) => setFilter("comparePrevious", e.target.checked)}
                      className="rounded border-slate-300 dark:border-white/10 text-orange-600 accent-orange-500"
                    />
                    <span className="text-[8px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-400">Compare Prev</span>
                  </label>
                </div>
              </div>

            </div>
          </div>
        </div>
      )}
    </div>
  );
}
