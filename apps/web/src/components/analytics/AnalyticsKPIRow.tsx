"use client";

import React from "react";
import KPICard from "@/components/ui/KPICard";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { 
  TrendingUp, 
  Calendar, 
  ListTodo, 
  CheckCircle2, 
  AlertCircle, 
  Flame, 
  PiggyBank, 
  Clock, 
  BarChart4, 
  Coins 
} from "lucide-react";

export default function AnalyticsKPIRow() {
  const projectKPIs = useAnalyticsStore((state) => state.projectKPIs);

  if (!projectKPIs) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-5 xl:grid-cols-10 animate-pulse">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-28 rounded-2xl bg-slate-100 dark:bg-white/5" />
        ))}
      </div>
    );
  }

  const {
    overallProgress,
    plannedVsActualVariance,
    totalTasks,
    completedTasks,
    delayedTasks,
    criticalTasks,
    budgetUsedPercent,
    forecastFinishDate,
    spi,
    cpi
  } = projectKPIs;

  // Helper for KPI styling status
  const getSpiCpiStatus = (val: number | null) => {
    if (val === null) return "neutral";
    if (val >= 1.0) return "positive";
    if (val >= 0.9) return "warning";
    return "negative";
  };

  const getVarianceStatus = (val: number) => {
    if (val <= 0) return "positive";
    if (val <= 7) return "warning";
    return "negative";
  };

  const getDelayedStatus = (val: number) => {
    return val > 0 ? "negative" : "positive";
  };

  const getCriticalStatus = (val: number) => {
    return val > 0 ? "warning" : "positive";
  };

  const kpis = [
    {
      label: "Overall Progress",
      value: `${overallProgress}%`,
      status: overallProgress >= 90 ? "positive" : (overallProgress >= 50 ? "warning" : "neutral"),
      icon: <TrendingUp className="w-5 h-5" />,
      tooltip: "Weighted progress of all project tasks",
    },
    {
      label: "Schedule Variance",
      value: plannedVsActualVariance === 0 ? "On Track" : `${plannedVsActualVariance > 0 ? "+" : ""}${plannedVsActualVariance}d`,
      status: getVarianceStatus(plannedVsActualVariance),
      icon: <Calendar className="w-5 h-5" />,
      tooltip: "Days ahead (-) or behind (+) schedule finish milestone",
    },
    {
      label: "Total Tasks",
      value: totalTasks.toString(),
      status: "neutral",
      icon: <ListTodo className="w-5 h-5" />,
      tooltip: "Count of all project tasks",
    },
    {
      label: "Completed Tasks",
      value: completedTasks.toString(),
      status: "neutral",
      icon: <CheckCircle2 className="w-5 h-5" />,
      tooltip: "Tasks currently 100% complete",
    },
    {
      label: "Delayed Tasks",
      value: delayedTasks.toString(),
      status: getDelayedStatus(delayedTasks),
      icon: <AlertCircle className="w-5 h-5" />,
      tooltip: "Overdue tasks finishing in past relative to today",
    },
    {
      label: "Critical Tasks",
      value: criticalTasks.toString(),
      status: getCriticalStatus(criticalTasks),
      icon: <Flame className="w-5 h-5" />,
      tooltip: "Tasks on the Critical Path (CPM)",
    },
    {
      label: "Budget Used",
      value: budgetUsedPercent !== null ? `${budgetUsedPercent}%` : "N/A",
      status: budgetUsedPercent !== null && budgetUsedPercent > 100 ? "negative" : "neutral",
      icon: <PiggyBank className="w-5 h-5" />,
      subtitle: budgetUsedPercent !== null ? undefined : "Data unavailable",
      tooltip: "Percentage of baseline budget committed to Work Orders",
    },
    {
      label: "Forecast Finish",
      value: forecastFinishDate ? new Date(forecastFinishDate).toLocaleDateString("en-IN", { month: "short", day: "2-digit" }) : "N/A",
      status: "neutral",
      icon: <Clock className="w-5 h-5" />,
      tooltip: "Estimated finish date projected by current progress velocity",
    },
    {
      label: "SPI (Schedule)",
      value: spi !== null ? spi.toFixed(2) : "N/A",
      status: getSpiCpiStatus(spi),
      icon: <BarChart4 className="w-5 h-5" />,
      subtitle: spi !== null ? undefined : "No cost data",
      tooltip: "Schedule Performance Index (EV / PV). Target is >= 1.0",
    },
    {
      label: "CPI (Cost)",
      value: cpi !== null ? cpi.toFixed(2) : "N/A",
      status: getSpiCpiStatus(cpi),
      icon: <Coins className="w-5 h-5" />,
      subtitle: cpi !== null ? undefined : "No cost data",
      tooltip: "Cost Performance Index (EV / AC). Target is >= 1.0",
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 xl:grid-cols-10 gap-4">
      {kpis.map((kpi, idx) => (
        <div key={idx} className="min-w-0">
          <KPICard
            label={kpi.label}
            value={kpi.value}
            status={kpi.status as any}
            icon={kpi.icon}
            tooltip={kpi.tooltip}
            subtitle={kpi.subtitle}
            className="h-full border-zinc-200 dark:border-white/5 bg-white/40 dark:bg-slate-950/40"
          />
        </div>
      ))}
    </div>
  );
}
