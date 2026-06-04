"use client";

import React, { useState, useRef, useEffect } from "react";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { AnalyticsChartType } from "@/types/analytics.types";
import { 
  ChevronDown, 
  TrendingUp, 
  Activity, 
  PieChart, 
  Flag, 
  AlertOctagon, 
  BarChart3, 
  Coins, 
  LineChart, 
  DollarSign, 
  Users2, 
  Clock, 
  Gauge 
} from "lucide-react";

interface ChartOption {
  type: AnalyticsChartType;
  label: string;
  description: string;
  icon: React.ReactNode;
  requiresCost: boolean;
}

interface ChartGroup {
  name: string;
  options: ChartOption[];
}

const groups: ChartGroup[] = [
  {
    name: "Schedule Metrics",
    options: [
      {
        type: "s_curve",
        label: "S-Curve Analysis",
        description: "Cumulative Planned vs Earned Value curves",
        icon: <TrendingUp className="size-4 text-amber-500" />,
        requiresCost: false,
      },
      {
        type: "planned_vs_actual",
        label: "Planned vs Actual Progress",
        description: "Dual-line progress percentage over time",
        icon: <Activity className="size-4 text-sky-500" />,
        requiresCost: false,
      },
      {
        type: "task_status",
        label: "Task Status Distribution",
        description: "Donut chart showing status of tasks",
        icon: <PieChart className="size-4 text-teal-500" />,
        requiresCost: false,
      },
      {
        type: "milestone_trend",
        label: "Milestone Status Trend",
        description: "Visual status timeline for critical milestones",
        icon: <Flag className="size-4 text-violet-500" />,
        requiresCost: false,
      },
      {
        type: "critical_tasks",
        label: "Critical vs Non-Critical Tasks",
        description: "Overview of tasks driving the end finish date",
        icon: <AlertOctagon className="size-4 text-rose-500" />,
        requiresCost: false,
      },
      {
        type: "schedule_variance",
        label: "Baseline vs Current Schedule Variance",
        description: "Variance deviation from original baseline",
        icon: <BarChart3 className="size-4 text-indigo-500" />,
        requiresCost: false,
      },
    ],
  },
  {
    name: "Financial & Earned Value",
    options: [
      {
        type: "cost_overview",
        label: "Cost Overview",
        description: "Planned vs actual financial distribution",
        icon: <Coins className="size-4 text-yellow-500" />,
        requiresCost: true,
      },
      {
        type: "earned_value",
        label: "Earned Value Summary",
        description: "PV, EV, and AC lines with full EVM stats",
        icon: <LineChart className="size-4 text-emerald-500" />,
        requiresCost: true,
      },
      {
        type: "cash_flow",
        label: "Cash Flow Projection",
        description: "Projected monthly cash outflow timeline",
        icon: <DollarSign className="size-4 text-green-500" />,
        requiresCost: true,
      },
    ],
  },
  {
    name: "Resource & Load",
    options: [
      {
        type: "resource_load",
        label: "Resource Workload",
        description: "Aggregated workload duration per assignee",
        icon: <Users2 className="size-4 text-orange-500" />,
        requiresCost: false,
      },
    ],
  },
  {
    name: "Forecasting & Trends",
    options: [
      {
        type: "delay_trend",
        label: "Delay / Slippage Trend",
        description: "Delayed count and average slippage trend",
        icon: <Clock className="size-4 text-red-500" />,
        requiresCost: false,
      },
      {
        type: "completion_forecast",
        label: "Completion Forecast",
        description: "Projected end date based on progress velocity",
        icon: <Gauge className="size-4 text-fuchsia-500" />,
        requiresCost: false,
      },
    ],
  },
];

export default function AnalyticsChartSelector() {
  const selectedChart = useAnalyticsStore((state) => state.selectedChart);
  const setSelectedChart = useAnalyticsStore((state) => state.setSelectedChart);
  const computedMetrics = useAnalyticsStore((state) => state.computedMetrics);

  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const hasCostData = computedMetrics?.cpi !== null || (computedMetrics?.budgetUsedPercent !== null && computedMetrics?.budgetUsedPercent > 0);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Find active option
  const activeOption = groups
    .flatMap((g) => g.options)
    .find((o) => o.type === selectedChart) || groups[0].options[0];

  const handleSelect = (type: AnalyticsChartType) => {
    setSelectedChart(type);
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between gap-3 min-w-[240px] px-4 py-2.5 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-900 dark:text-white hover:border-orange-500/50 transition-all outline-none"
      >
        <div className="flex items-center gap-2">
          {activeOption.icon}
          <span>{activeOption.label}</span>
        </div>
        <ChevronDown size={14} className={`text-slate-400 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute left-0 mt-2 w-[340px] max-h-[480px] overflow-y-auto z-50 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-900 shadow-2xl p-2 scrollbar-thin">
          {groups.map((group) => (
            <div key={group.name} className="mb-2">
              <div className="px-3 py-1.5 text-[9px] font-black uppercase tracking-widest text-slate-400 dark:text-white/30 border-b border-slate-100 dark:border-white/5 mb-1">
                {group.name}
              </div>
              <div className="space-y-0.5">
                {group.options.map((option) => {
                  const isActive = option.type === selectedChart;
                  const isCostWarning = option.requiresCost && !hasCostData;

                  return (
                    <button
                      type="button"
                      key={option.type}
                      onClick={() => handleSelect(option.type)}
                      className={`w-full flex items-start gap-3 p-2 rounded-xl text-left transition-all ${
                        isActive
                          ? "bg-orange-600 dark:bg-orange-500 text-white"
                          : "hover:bg-slate-100 dark:hover:bg-white/5 text-slate-700 dark:text-slate-300"
                      }`}
                    >
                      <div className={`mt-0.5 p-1 rounded-lg ${isActive ? "bg-white/20" : "bg-slate-100 dark:bg-white/5"}`}>
                        {option.icon}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className={`text-[10px] font-black uppercase tracking-wider ${isActive ? "text-white" : "text-slate-900 dark:text-white"}`}>
                            {option.label}
                          </span>
                          {isCostWarning && (
                            <span className="text-[7px] font-bold px-1.5 py-0.2 bg-amber-500/10 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 rounded-full border border-amber-500/20">
                              No Cost Data
                            </span>
                          )}
                        </div>
                        <p className={`text-[9px] mt-0.5 ${isActive ? "text-white/70" : "text-slate-500 dark:text-slate-400"}`}>
                          {option.description}
                        </p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
