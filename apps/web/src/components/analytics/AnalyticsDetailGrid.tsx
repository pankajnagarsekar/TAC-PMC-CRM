"use client";

import React, { useMemo, useState } from "react";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { formatINRShort } from "@/lib/formatters";
import { parseTaskDate } from "@/components/scheduler/scheduler-utils";
import { useRouter, useSearchParams } from "next/navigation";
import { ChevronDown, ChevronUp, ArrowRight } from "lucide-react";
import { getFilteredTasks, computeMilestoneData, computeResourceLoad, computeSCurveData } from "@/lib/analyticsComputeEngine";

interface AnalyticsDetailGridProps {
  tasks: ScheduleTask[];
  financials?: any[];
}

export default function AnalyticsDetailGrid({ tasks, financials }: AnalyticsDetailGridProps) {
  const selectedChart = useAnalyticsStore((state) => state.selectedChart);
  const filters = useAnalyticsStore((state) => state.filters);
  const setSelectedTask = useScheduleStore((state) => state.setSelectedTask);

  const [isOpen, setIsOpen] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  const filteredTasks = useMemo(() => {
    return getFilteredTasks(tasks, filters);
  }, [tasks, filters]);

  const handleRowClick = (taskId: string) => {
    // Select task in store
    setSelectedTask(taskId);
    
    // Switch to grid tab
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", "grid");
    router.replace(`?${params.toString()}`);
  };

  const tableData = useMemo(() => {
    switch (selectedChart) {
      case "s_curve":
      case "earned_value":
        // Sort tasks by largest cost variance (absolute value of baseline_cost - wo_value)
        return filteredTasks
          .map(t => {
            const bac = Number(t.baseline_cost ?? 0);
            const progress = Number(t.percent_complete ?? 0) / 100;
            const ev = bac * progress;
            const ac = Number(t.payment_value ?? t.wo_value ?? 0);
            const cv = ev - ac;
            return { ...t, ev, ac, cv };
          })
          .sort((a, b) => Math.abs(b.cv) - Math.abs(a.cv))
          .slice(0, 10);

      case "task_status":
        // Show tasks grouped by status
        return [...filteredTasks]
          .sort((a, b) => (a.task_status || "").localeCompare(b.task_status || ""))
          .slice(0, 15);

      case "milestone_trend":
        // Get milestone slippages
        return computeMilestoneData(tasks, filters);

      case "critical_tasks":
        // Overdue or active critical tasks first
        return [...filteredTasks]
          .filter(t => t.is_critical)
          .sort((a, b) => (a.percent_complete ?? 0) - (b.percent_complete ?? 0))
          .slice(0, 10);

      case "schedule_variance":
        // Sort tasks by largest schedule variance (difference between scheduled_finish and baseline_finish)
        return filteredTasks
          .map(t => {
            const baseline = t.baseline_finish ? new Date(t.baseline_finish) : null;
            const current = t.scheduled_finish ? new Date(t.scheduled_finish) : null;
            let variance = 0;
            if (baseline && current) {
              variance = Math.round((current.getTime() - baseline.getTime()) / (1000 * 60 * 60 * 24));
            }
            return { ...t, variance };
          })
          .sort((a, b) => Math.abs(b.variance) - Math.abs(a.variance))
          .slice(0, 10);

      case "resource_load":
        return computeResourceLoad(tasks, filters);

      case "cost_overview":
        if (financials && financials.length > 0) {
          return financials;
        }
        // Fallback to task aggregation categories
        const categoriesMap: Record<string, any> = {};
        tasks.forEach(t => {
          const code = t.wbs_code?.split('.')[0] || 'Misc';
          const name = code === 'C' ? 'Construction' :
                       code === 'P' ? 'Contracting' :
                       code === 'D' ? 'Design/Engineering' :
                       code === 'S' ? 'Site Ops' :
                       code === 'I' ? 'Interiors' : code;
          if (!categoriesMap[name]) {
            categoriesMap[name] = { category_name: name, original_budget: 0, committed_value: 0, certified_value: 0 };
          }
          categoriesMap[name].original_budget += Number(t.baseline_cost ?? 0);
          categoriesMap[name].committed_value += Number(t.wo_value ?? 0);
          categoriesMap[name].certified_value += Number(t.payment_value ?? 0);
        });
        return Object.values(categoriesMap);

      case "cash_flow":
        return computeSCurveData(tasks, filters);

      case "completion_forecast":
        // Show active critical tasks that are incomplete
        return filteredTasks
          .filter(t => t.is_critical && (t.percent_complete ?? 0) < 100)
          .map(t => {
            const baseline = t.baseline_finish ? new Date(t.baseline_finish) : null;
            const current = t.scheduled_finish ? new Date(t.scheduled_finish) : null;
            let variance = 0;
            if (baseline && current) {
              variance = Math.round((current.getTime() - baseline.getTime()) / (1000 * 60 * 60 * 24));
            }
            return { ...t, variance };
          })
          .slice(0, 10);

      default:
        return filteredTasks.slice(0, 10);
    }
  }, [selectedChart, filteredTasks, tasks, filters, financials]);

  if (tableData.length === 0) return null;

  return (
    <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-white/40 dark:bg-slate-950/40 p-5 shadow-xl backdrop-blur-xl">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full text-left"
      >
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white">
            Supporting Data Details
          </h3>
          <span className="text-[8px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-white/5 text-slate-500">
            {tableData.length} records
          </span>
        </div>
        {isOpen ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>

      {isOpen && (
        <div className="mt-4 pt-4 border-t border-slate-200 dark:border-white/5 overflow-x-auto animate-in slide-in-from-top-2 duration-300">
          <Table>
            <TableHeader>
              <TableRow className="border-slate-100 dark:border-white/5">
                {/* Dynamically adjust headers */}
                {selectedChart === "resource_load" ? (
                  <>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Resource Name</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Planned Workload (Days)</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Completed (Days)</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider text-rose-500">Overdue (Days)</TableHead>
                  </>
                ) : selectedChart === "cost_overview" ? (
                  <>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Cost Category</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Approved Budget</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Committed (WOs)</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Certified (PCs)</TableHead>
                  </>
                ) : selectedChart === "cash_flow" ? (
                  <>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Month</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Planned Value (PV)</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Earned Value (EV)</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Actual Cost (AC)</TableHead>
                  </>
                ) : selectedChart === "milestone_trend" ? (
                  <>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Milestone Name</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Baseline Target</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Current Schedule</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider text-right">Delay (Days)</TableHead>
                  </>
                ) : (
                  <>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Task Description</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">WBS Code</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Status</TableHead>
                    <TableHead className="text-[9px] font-black uppercase tracking-wider">Progress</TableHead>
                    {["s_curve", "earned_value"].includes(selectedChart) ? (
                      <TableHead className="text-[9px] font-black uppercase tracking-wider text-right">Cost Variance (CV)</TableHead>
                    ) : (
                      <TableHead className="text-[9px] font-black uppercase tracking-wider text-right">Variance (Days)</TableHead>
                    )}
                  </>
                )}
              </TableRow>
            </TableHeader>
            <TableBody>
              {tableData.map((row: any, idx) => (
                <TableRow
                  key={row.task_id || row.name || row.category_id || idx}
                  onClick={() => row.task_id && handleRowClick(row.task_id)}
                  className={`border-slate-100 dark:border-white/5 text-[10px] font-bold text-slate-700 dark:text-slate-300 transition-colors ${
                    row.task_id ? "cursor-pointer hover:bg-slate-50 dark:hover:bg-white/[0.02]" : ""
                  }`}
                >
                  {selectedChart === "resource_load" ? (
                    <>
                      <TableCell className="font-semibold text-slate-900 dark:text-white">{row.name}</TableCell>
                      <TableCell>{row.planned}d</TableCell>
                      <TableCell className="text-emerald-500">{row.completed}d</TableCell>
                      <TableCell className="text-rose-500 font-semibold">{row.overdue}d</TableCell>
                    </>
                  ) : selectedChart === "cost_overview" ? (
                    <>
                      <TableCell className="font-semibold text-slate-900 dark:text-white">{row.category_name || row.category_code}</TableCell>
                      <TableCell>{formatINRShort(row.original_budget)}</TableCell>
                      <TableCell>{formatINRShort(row.committed_value)}</TableCell>
                      <TableCell className="text-emerald-500">{formatINRShort(row.certified_value)}</TableCell>
                    </>
                  ) : selectedChart === "cash_flow" ? (
                    <>
                      <TableCell className="font-semibold text-slate-900 dark:text-white">{row.name}</TableCell>
                      <TableCell>{formatINRShort(row.PV)}</TableCell>
                      <TableCell className="text-sky-500">{row.EV !== null ? formatINRShort(row.EV) : "N/A"}</TableCell>
                      <TableCell className="text-rose-500">{row.AC !== null ? formatINRShort(row.AC) : "N/A"}</TableCell>
                    </>
                  ) : selectedChart === "milestone_trend" ? (
                    <>
                      <TableCell className="font-semibold text-slate-900 dark:text-white">{row.name}</TableCell>
                      <TableCell>{new Date(row.baseline).toLocaleDateString("en-IN", { month: "short", day: "2-digit" })}</TableCell>
                      <TableCell>{new Date(row.current).toLocaleDateString("en-IN", { month: "short", day: "2-digit" })}</TableCell>
                      <td className="p-2 text-right">
                        <span className={`px-2 py-0.5 rounded-full text-[9px] font-black ${
                          row.status === 'delayed' ? 'bg-rose-500/10 text-rose-500' :
                          row.status === 'at-risk' ? 'bg-amber-500/10 text-amber-500' :
                          'bg-emerald-500/10 text-emerald-500'
                        }`}>
                          {row.delayDays === 0 ? "On Time" : `+${row.delayDays}d`}
                        </span>
                      </td>
                    </>
                  ) : (
                    <>
                      <TableCell className="font-semibold text-slate-900 dark:text-white flex items-center gap-1.5 py-3">
                        {row.task_name || row.task_description}
                        {row.task_id && <ArrowRight size={10} className="opacity-0 group-hover:opacity-100 transition-opacity text-orange-500" />}
                      </TableCell>
                      <TableCell className="font-mono text-[9px]">{row.wbs_code || "N/A"}</TableCell>
                      <TableCell className="uppercase tracking-widest text-[8px]">{row.task_status}</TableCell>
                      <TableCell>{row.percent_complete ?? 0}%</TableCell>
                      {["s_curve", "earned_value"].includes(selectedChart) ? (
                        <TableCell className={`text-right font-mono ${row.cv >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                          {row.cv >= 0 ? "+" : ""}{formatINRShort(row.cv)}
                        </TableCell>
                      ) : (
                        <TableCell className={(() => {
                          const baseline = row.baseline_finish ? new Date(row.baseline_finish) : null;
                          const current = row.scheduled_finish ? new Date(row.scheduled_finish) : null;
                          const v = row.variance !== undefined ? row.variance : (baseline && current ? Math.round((current.getTime() - baseline.getTime()) / (1000 * 60 * 60 * 24)) : null);
                          
                          if (v === null) return "text-right font-mono text-slate-400";
                          return `text-right font-mono ${v > 0 ? "text-rose-500" : "text-emerald-500"}`;
                        })()}>
                          {(() => {
                            const baseline = row.baseline_finish ? new Date(row.baseline_finish) : null;
                            const current = row.scheduled_finish ? new Date(row.scheduled_finish) : null;
                            const v = row.variance !== undefined ? row.variance : (baseline && current ? Math.round((current.getTime() - baseline.getTime()) / (1000 * 60 * 60 * 24)) : null);
                            
                            if (v === null) return "—";
                            return `${v > 0 ? "+" : ""}${v}d`;
                          })()}
                        </TableCell>
                      )}
                    </>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
