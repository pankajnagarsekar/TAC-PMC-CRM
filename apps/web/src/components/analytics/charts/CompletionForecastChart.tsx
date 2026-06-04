"use client";

import React, { useMemo, useRef } from "react";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { computeCompletionForecast, computeKPIs } from "@/lib/analyticsComputeEngine";
import { 
  Hourglass, 
  AlertOctagon, 
  Gauge 
} from "lucide-react";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface CompletionForecastChartProps {
  tasks: ScheduleTask[];
}

export default function CompletionForecastChart({ tasks }: CompletionForecastChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  const forecast = useMemo(() => {
    return computeCompletionForecast(tasks, filters);
  }, [tasks, filters]);

  const kpis = useMemo(() => {
    return computeKPIs(tasks, filters);
  }, [tasks, filters]);

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString("en-IN", { month: "short", day: "2-digit", year: "numeric" });
  };

  const getRiskLevel = (slippage: number, criticalCount: number) => {
    if (slippage > 14 || criticalCount > 5) return { label: "High Risk", color: "text-rose-500 bg-rose-500/10 border-rose-500/20" };
    if (slippage > 0 || criticalCount > 0) return { label: "Medium Risk", color: "text-amber-500 bg-amber-500/10 border-amber-500/20" };
    return { label: "On Track", color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/20" };
  };

  const risk = getRiskLevel(forecast.slippageDays, kpis.criticalTasks);

  // Parse dates for relative positioning
  const timelineNodes = useMemo(() => {
    const dates = [
      { id: "baseline", label: "Baseline Finish", date: forecast.baselineFinish, color: "bg-slate-400 border-slate-500", text: "text-slate-500" },
      { id: "target", label: "Current Target", date: forecast.targetFinish, color: "bg-orange-500 border-orange-600", text: "text-orange-600 dark:text-orange-400" },
      { id: "forecast", label: "Forecast Finish", date: forecast.forecastFinish, color: "bg-rose-500 border-rose-600", text: "text-rose-500" }
    ].filter(n => n.date !== null) as Array<{ id: string; label: string; date: string; color: string; text: string }>;

    if (dates.length === 0) return [];

    const sorted = [...dates].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    const minTime = new Date(sorted[0].date).getTime();
    const maxTime = new Date(sorted[sorted.length - 1].date).getTime();
    const totalSpan = maxTime - minTime || 1;

    return sorted.map((node) => {
      const offset = ((new Date(node.date).getTime() - minTime) / totalSpan) * 80 + 10; // 10% to 90% range
      return { ...node, offset };
    });
  }, [forecast]);

  const csvData = useMemo(() => {
    return [
      { Metric: "Baseline Finish Date", Value: formatDate(forecast.baselineFinish) },
      { Metric: "Current Target Date", Value: formatDate(forecast.targetFinish) },
      { Metric: "Forecast Finish Date", Value: formatDate(forecast.forecastFinish) },
      { Metric: "Progress Velocity", Value: `${forecast.overallProgress}%` },
      { Metric: "Projected Slippage Days", Value: forecast.slippageDays },
    ];
  }, [forecast]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Completion Forecast</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Delivery target projection modeled by progress velocity and remaining milestones
          </p>
        </div>
        <AnalyticsExportBar
          chartRef={chartRef}
          chartData={csvData}
          columns={["Metric", "Value"]}
          title="Completion Forecast"
          fileName="Completion_Forecast"
        />
      </div>

      {timelineNodes.length > 0 ? (
        <div className="space-y-8 pt-8 pb-4">
          {/* Custom Timeline Visualizer */}
          <div className="relative w-full h-12 flex items-center">
            {/* Horizontal Timeline Track */}
            <div className="absolute left-[10%] right-[10%] h-1 bg-slate-200 dark:bg-white/10 rounded-full" />
            
            {/* Timeline Nodes */}
            {timelineNodes.map((node) => (
              <div 
                key={node.id} 
                className="absolute -translate-x-1/2 flex flex-col items-center group transition-all"
                style={{ left: `${node.offset}%` }}
              >
                {/* Node Pointer */}
                <div className={`w-4 h-4 rounded-full border-2 ${node.color} shadow-lg cursor-help`} />
                
                {/* Node Popup Text */}
                <div className="absolute -top-12 flex flex-col items-center bg-slate-900 dark:bg-slate-950 px-2.5 py-1 rounded-lg border border-white/10 shadow-md text-center pointer-events-none w-28 opacity-90 group-hover:opacity-100 group-hover:scale-105 transition-all">
                  <span className="text-[7px] font-black text-slate-400 uppercase tracking-widest leading-none">{node.label}</span>
                  <span className="text-[9px] font-black text-white mt-0.5 leading-none">{formatDate(node.date)}</span>
                </div>

                {/* Node Bottom Label */}
                <span className={`text-[8px] font-black uppercase tracking-widest mt-3 ${node.text}`}>
                  {node.id === "baseline" ? "Baseline" : node.id === "target" ? "Target" : "Forecast"}
                </span>
              </div>
            ))}
          </div>

          {/* Forecasting Metrics row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-6 border-t border-slate-200 dark:border-white/5">
            {/* Delivery Velocity */}
            <div className="flex items-center gap-3 p-3.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-2xl">
              <div className="w-10 h-10 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500 shrink-0">
                <Gauge className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[8px] font-black text-slate-400 uppercase tracking-wider block">Progress Velocity</span>
                <span className="text-xs font-black text-slate-900 dark:text-white mt-0.5 block">{forecast.overallProgress}% Complete</span>
              </div>
            </div>

            {/* Projected Slippage */}
            <div className="flex items-center gap-3 p-3.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-2xl">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-500 shrink-0">
                <Hourglass className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[8px] font-black text-slate-400 uppercase tracking-wider block">Projected Slippage</span>
                <span className={`text-xs font-black mt-0.5 block ${forecast.slippageDays > 0 ? "text-rose-500" : "text-emerald-500"}`}>
                  {forecast.slippageDays === 0 
                    ? "On Schedule" 
                    : `${forecast.slippageDays > 0 ? "+" : ""}${forecast.slippageDays} Days`}
                </span>
              </div>
            </div>

            {/* Risk Index */}
            <div className="flex items-center gap-3 p-3.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-2xl">
              <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center text-violet-500 shrink-0">
                <AlertOctagon className="w-5 h-5" />
              </div>
              <div>
                <span className="text-[8px] font-black text-slate-400 uppercase tracking-wider block">Delivery Risk</span>
                <span className={`text-[10px] font-black px-2.5 py-0.5 rounded-full border mt-0.5 inline-block ${risk.color}`}>
                  {risk.label}
                </span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex h-[300px] items-center justify-center text-slate-400">
          Add task baseline dates to activate forecast projections.
        </div>
      )}
    </div>
  );
}
