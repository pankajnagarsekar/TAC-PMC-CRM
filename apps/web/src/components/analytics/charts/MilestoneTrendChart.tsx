"use client";

import React, { useMemo, useRef } from "react";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { computeMilestoneData } from "@/lib/analyticsComputeEngine";

import AnalyticsEmptyState from "../AnalyticsEmptyState";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface MilestoneTrendChartProps {
  tasks: ScheduleTask[];
}

export default function MilestoneTrendChart({ tasks }: MilestoneTrendChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  const data = useMemo(() => {
    return computeMilestoneData(tasks, filters);
  }, [tasks, filters]);

  // Color mapper based on milestone delay status
  const getColor = (status: "on-time" | "at-risk" | "delayed") => {
    if (status === "delayed") return "#ef4444"; // Red
    if (status === "at-risk") return "#f59e0b";  // Amber
    return "#10b981";                            // Green
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr === "N/A") return "N/A";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString("en-IN", { month: "short", day: "2-digit", year: "numeric" });
  };

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full relative">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Milestone Status Trend</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Slippage deviation in days from original baseline schedule
          </p>
        </div>
        {data.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={data}
            columns={["name", "baseline", "current", "delayDays", "status"]}
            title="Milestone Status Trend"
            fileName="Milestone_Status_Trend"
          />
        )}
      </div>

      {data.length > 0 ? (
        <div className="space-y-6">
          {/* Bar Chart for Delays */}
          <div className="h-[200px] w-full min-w-0">
            <ResponsiveContainer width="100%" height="100%" debounce={100}>
              <BarChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-white/[0.03]" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                />
                <YAxis
                  label={{ value: 'Delay (Days)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 9, style: { textAnchor: 'middle' } }}
                  tick={{ fill: "#64748b", fontSize: 9 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "rgba(15, 23, 42, 0.9)",
                    border: "1px solid rgba(255, 255, 255, 0.1)",
                    borderRadius: "12px",
                    fontSize: "11px",
                    color: "#fff",
                    boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1)"
                  }}
                  formatter={(value: any) => [`${Number(value || 0)} Days`, "Slippage"]}
                />
                <Bar dataKey="delayDays" radius={[6, 6, 0, 0]} maxBarSize={30}>
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={getColor(entry.status)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Timeline Milestones List */}
          <div className="overflow-x-auto max-h-[160px] overflow-y-auto pr-1">
            <table className="w-full border-collapse text-left">
              <thead>
                <tr className="border-b border-slate-100 dark:border-white/5 pb-2">
                  <th className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30 py-2">Milestone</th>
                  <th className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30 py-2">Baseline Finish</th>
                  <th className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30 py-2">Current Finish</th>
                  <th className="text-[9px] font-black uppercase tracking-wider text-slate-400 dark:text-white/30 py-2 text-right">Variance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                {data.map((m) => (
                  <tr key={m.task_id} className="text-[10px] font-bold text-slate-700 dark:text-slate-300">
                    <td className="py-2.5 truncate max-w-[160px] text-slate-900 dark:text-white">{m.name}</td>
                    <td className="py-2.5">{formatDate(m.baseline)}</td>
                    <td className="py-2.5">{formatDate(m.current)}</td>
                    <td className="py-2.5 text-right font-black">
                      <span className={`px-2 py-0.5 rounded-full text-[9px] ${
                        m.status === 'delayed' ? 'bg-rose-500/10 text-rose-500 border border-rose-500/10' :
                        m.status === 'at-risk' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/10' :
                        'bg-emerald-500/10 text-emerald-500 border border-emerald-500/10'
                      }`}>
                        {m.delayDays === 0 ? "On Time" : `+${m.delayDays}d`}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="py-8">
          <AnalyticsEmptyState
            title="No Milestones Defined"
            description="Milestone tasks are needed to generate this chart. Open the Grid or Gantt view and mark tasks as milestones using the task options."
            actionText="Open Grid"
            actionTab="grid"
          />
        </div>
      )}
    </div>
  );
}
