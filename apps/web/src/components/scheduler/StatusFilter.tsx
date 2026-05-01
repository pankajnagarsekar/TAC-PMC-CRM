"use client";

import React from "react";
import { Filter, Check } from "lucide-react";
import * as Popover from "@radix-ui/react-popover";
import { useScheduleStore } from "@/store/useScheduleStore";
import { KANBAN_META, KANBAN_STATUSES } from "./scheduler-utils";
import type { ScheduleTaskStatus } from "@/types/schedule.types";

export default function StatusFilter() {
  const statusFilter = useScheduleStore((state) => state.activeFilters.statusFilter);
  const effectiveFilter = statusFilter || [];
  const setStatusFilter = useScheduleStore((state) => state.setStatusFilter);

  const toggleStatus = (status: ScheduleTaskStatus) => {
    if (effectiveFilter.includes(status)) {
      setStatusFilter(effectiveFilter.filter((s) => s !== status));
    } else {
      setStatusFilter([...effectiveFilter, status]);
    }
  };

  const clearFilter = () => setStatusFilter([]);

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border transition-all text-[10px] font-black uppercase tracking-widest ${
          effectiveFilter.length > 0 
            ? "bg-orange-500/10 border-orange-500/30 text-orange-600 dark:text-orange-400" 
            : "bg-slate-100 dark:bg-white/5 border-slate-200 dark:border-white/10 text-slate-500 hover:text-slate-900 dark:hover:text-white"
        }`}>
          <Filter size={14} />
          <span>Status {effectiveFilter.length > 0 ? `(${effectiveFilter.length})` : ""}</span>
        </button>
      </Popover.Trigger>
      
      <Popover.Portal>
        <Popover.Content 
          className="z-[100] w-64 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl p-4 animate-in fade-in zoom-in-95 duration-200"
          sideOffset={8}
          align="end"
        >
          <div className="flex items-center justify-between mb-4">
            <h4 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">Filter by Status</h4>
            {effectiveFilter.length > 0 && (
              <button 
                onClick={clearFilter}
                className="text-[10px] font-black uppercase text-rose-500 hover:text-rose-600 transition-colors"
              >
                Clear All
              </button>
            )}
          </div>
          
          <div className="space-y-1">
            {KANBAN_STATUSES.map((status) => {
              const isActive = effectiveFilter.includes(status);
              const meta = KANBAN_META[status];
              
              return (
                <button
                  key={status}
                  onClick={() => toggleStatus(status)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                    isActive 
                      ? "bg-orange-500/10 text-orange-600 dark:text-orange-400" 
                      : "hover:bg-slate-100 dark:hover:bg-white/5 text-slate-600 dark:text-slate-400"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${meta.tone.split(' ')[0]}`} />
                    <span>{meta.label}</span>
                  </div>
                  {isActive && <Check size={14} />}
                </button>
              );
            })}
          </div>
          
          <Popover.Arrow className="fill-white dark:fill-slate-900" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
