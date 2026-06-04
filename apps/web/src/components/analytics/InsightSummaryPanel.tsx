"use client";

import React, { useMemo } from "react";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { generateInsights } from "@/lib/analyticsInsightEngine";
import { normalizeTaskOrder } from "@/components/scheduler/scheduler-utils";
import { 
  Sparkles, 
  AlertOctagon, 
  AlertTriangle, 
  Info 
} from "lucide-react";

const getSeverityStyles = (severity: "info" | "warning" | "critical") => {
  switch (severity) {
    case "critical":
      return {
        bg: "bg-rose-500/5 dark:bg-rose-500/10",
        border: "border-rose-500/20",
        text: "text-rose-700 dark:text-rose-400",
        icon: <AlertOctagon className="size-4 text-rose-500 shrink-0 mt-0.5" />
      };
    case "warning":
      return {
        bg: "bg-amber-500/5 dark:bg-amber-500/10",
        border: "border-amber-500/20",
        text: "text-amber-700 dark:text-amber-400",
        icon: <AlertTriangle className="size-4 text-amber-500 shrink-0 mt-0.5" />
      };
    default:
      return {
        bg: "bg-slate-50 dark:bg-white/[0.02]",
        border: "border-slate-200 dark:border-white/5",
        text: "text-slate-700 dark:text-slate-300",
        icon: <Info className="size-4 text-slate-400 shrink-0 mt-0.5" />
      };
  }
};

export default function InsightSummaryPanel() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const selectedChart = useAnalyticsStore((state) => state.selectedChart);
  const filters = useAnalyticsStore((state) => state.filters);
  const computedMetrics = useAnalyticsStore((state) => state.computedMetrics);
  const projectKPIs = useAnalyticsStore((state) => state.projectKPIs);

  const insights = useMemo(() => {
    if (!computedMetrics) return [];
    return generateInsights(selectedChart, computedMetrics, filters, tasks, projectKPIs);
  }, [selectedChart, computedMetrics, filters, tasks, projectKPIs]);

  return (
    <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-white/60 dark:bg-slate-950/60 p-6 shadow-2xl backdrop-blur-xl h-full flex flex-col justify-between">
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <div className="size-8 rounded-xl bg-orange-500/10 flex items-center justify-center text-orange-500">
            <Sparkles className="size-4 animate-pulse" />
          </div>
          <div>
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white">Delivery Insights</h3>
            <p className="text-[9px] uppercase tracking-widest text-slate-450 dark:text-white/30">Auto-generated Observations</p>
          </div>
        </div>

        <div className="space-y-3 pt-2">
          {insights.map((insight) => {
            const styles = getSeverityStyles(insight.severity);
            return (
              <div 
                key={insight.id}
                className={`flex items-start gap-3 p-4 rounded-2xl border ${styles.bg} ${styles.border} shadow-sm animate-in fade-in duration-300`}
              >
                {styles.icon}
                <div>
                  <h4 className={`text-[10px] font-black uppercase tracking-wider ${styles.text}`}>
                    {insight.title}
                  </h4>
                  <p className="text-[9px] font-medium text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                    {insight.description}
                  </p>
                </div>
              </div>
            );
          })}
          
          {insights.length === 0 && (
            <div className="text-center py-12 text-slate-400 text-[10px] font-bold uppercase tracking-wider">
              No delivery insights available.
            </div>
          )}
        </div>
      </div>

      <div className="pt-4 mt-6 border-t border-slate-200 dark:border-white/5 text-center">
        <p className="text-[8px] font-bold uppercase tracking-widest text-slate-400 dark:text-white/20">
          Project Intelligence Engine v1.0
        </p>
      </div>
    </div>
  );
}
