"use client";

import React, { useMemo, useRef } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { AlertOctagon, CheckCircle2 } from "lucide-react";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface CriticalTasksChartProps {
  tasks: ScheduleTask[];
}

export default function CriticalTasksChart({ tasks }: CriticalTasksChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);
  const today = useMemo(() => new Date(), []);

  const stats = useMemo(() => {
    let criticalCount = 0;
    let nonCriticalCount = 0;
    let overdueCriticalCount = 0;

    tasks.forEach(t => {
      // Basic filtering matching our getFilteredTasks wrapper (excluding flags specific to this dashboard view)
      if (filters.statusFilter && filters.statusFilter.length > 0 && (!t.task_status || !filters.statusFilter.includes(t.task_status))) return;
      if (filters.assigneeFilter && filters.assigneeFilter.length > 0 && !t.assignee_ids?.some(id => filters.assigneeFilter!.includes(id))) return;

      const isCompleted = t.task_status === 'completed' || t.task_status === 'closed' || (t.percent_complete ?? 0) === 100;
      
      if (t.is_critical) {
        criticalCount++;
        const finish = t.scheduled_finish ? new Date(t.scheduled_finish) : null;
        if (finish && finish < today && !isCompleted) {
          overdueCriticalCount++;
        }
      } else {
        nonCriticalCount++;
      }
    });

    const data = [
      { name: "Critical Path Tasks", value: criticalCount, color: "#ef4444" },
      { name: "Non-Critical Tasks", value: nonCriticalCount, color: "#64748b" }
    ].filter(d => d.value > 0);

    return { data, criticalCount, nonCriticalCount, overdueCriticalCount, total: criticalCount + nonCriticalCount };
  }, [tasks, filters, today]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Critical vs Non-Critical Tasks</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Critical path vs non-critical tasks count ratio (CPM)
          </p>
        </div>
        {stats.total > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={stats.data}
            columns={["name", "value"]}
            title="Critical vs Non-Critical Tasks"
            fileName="Critical_Vs_Non_Critical_Tasks"
          />
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Donut Chart */}
        <div className="h-[220px] relative flex items-center justify-center">
          {stats.total > 0 ? (
            <ResponsiveContainer width="100%" height="100%" debounce={100}>
              <PieChart>
                <Pie
                  data={stats.data}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {stats.data.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.9)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    borderRadius: "12px",
                    fontSize: "11px",
                    color: "#fff",
                    boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1)"
                  }}
                  formatter={(value: any, name: any) => [`${value} Tasks`, name]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-[10px] text-slate-400 font-bold uppercase">No tasks found</div>
          )}
          <div className="absolute flex flex-col items-center justify-center">
            <span className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{stats.criticalCount}</span>
            <span className="text-[7px] font-bold text-rose-500 uppercase tracking-widest mt-0.5">Critical Tasks</span>
          </div>
        </div>

        {/* Info & Overdue Panel */}
        <div className="space-y-4">
          {/* Overdue Warning Card */}
          {stats.overdueCriticalCount > 0 ? (
            <div className="flex items-start gap-3 p-4 rounded-2xl border border-rose-500/20 bg-rose-500/5 dark:bg-rose-500/10 shadow-sm">
              <AlertOctagon className="size-5 text-rose-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-[10px] font-black uppercase tracking-widest text-rose-600 dark:text-rose-400">Overdue Critical Items</h4>
                <p className="text-[9px] font-semibold text-slate-500 dark:text-slate-300 mt-1 leading-normal">
                  {stats.overdueCriticalCount} critical path tasks have passed their scheduled finish dates. Resolve them immediately to protect project completion.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 p-4 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 dark:bg-emerald-500/10 shadow-sm">
              <CheckCircle2 className="size-5 text-emerald-500 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-[10px] font-black uppercase tracking-widest text-emerald-600 dark:text-emerald-400">Critical Path Clean</h4>
                <p className="text-[9px] font-semibold text-slate-500 dark:text-slate-300 mt-1 leading-normal">
                  No critical path tasks are currently overdue. Delivery dates are protected.
                </p>
              </div>
            </div>
          )}

          {/* Sub-metric Card Grid (ANL-022) */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200 dark:border-white/5">
            <div className="p-2.5 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/5 rounded-xl text-center">
              <span className="text-[8px] font-black uppercase tracking-wider text-slate-400 block">Critical Path</span>
              <span className="text-xs font-black text-rose-500 mt-0.5 block">{stats.criticalCount}</span>
            </div>
            <div className="p-2.5 bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/5 rounded-xl text-center">
              <span className="text-[8px] font-black uppercase tracking-wider text-slate-400 block">Non-Critical</span>
              <span className="text-xs font-black text-slate-700 dark:text-slate-300 mt-0.5 block">{stats.nonCriticalCount}</span>
            </div>
            <div className={`p-2.5 border rounded-xl text-center transition-all ${
              stats.overdueCriticalCount > 0 
                ? "bg-rose-500/10 border-rose-500/25 text-rose-500" 
                : "bg-slate-50 dark:bg-white/[0.02] border-slate-100 dark:border-white/5 text-slate-500"
            }`}>
              <span className="text-[8px] font-black uppercase tracking-wider text-slate-400 block">Overdue Critical</span>
              <span className={`text-xs font-black mt-0.5 block ${stats.overdueCriticalCount > 0 ? "text-rose-500 animate-pulse font-extrabold" : "text-slate-500 dark:text-slate-400"}`}>
                {stats.overdueCriticalCount}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
