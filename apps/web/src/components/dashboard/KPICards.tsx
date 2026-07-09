"use client";

import React, { useMemo } from "react";
import { Activity, BarChart3, Coins, IndianRupee, Gauge, Timer } from "lucide-react";
import { startOfDay, isAfter } from "date-fns";

import KPICard from "@/components/ui/KPICard";
import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";
import { formatINRShort } from "@/lib/formatters";

interface KPICardsProps {
  stats?: {
    planned_value?: number;
    earned_value?: number;
    actual_cost?: number;
    spi?: number;
    cpi?: number;
    master_budget?: number;
    total_budget?: number;
    is_baseline_initialized?: boolean;
  };
  onInitializeBaseline?: () => void;
}

/**
 * KPI Dashboard for Enterprise PPM.
 * Implements System Constitution §9 Earned Value Formulas.
 * Prioritizes authoritative backend stats with local calculation fallback.
 */
export default function KPICards({ stats: backendStats, onInitializeBaseline }: KPICardsProps) {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const stats = useMemo(() => {
    // If we have authoritative backend EVA stats, use them
    if (backendStats && (backendStats.planned_value !== undefined || backendStats.total_budget !== undefined)) {
      const rawSpi = backendStats.spi;
      const rawCpi = backendStats.cpi;
      
      return {
        totalBaselineCost: Number(backendStats.master_budget || backendStats.total_budget || 0),
        plannedValue: Number(backendStats.planned_value || 0),
        earnedValue: Number(backendStats.earned_value || 0),
        actualCost: Number(backendStats.actual_cost || 0),
        spi: (rawSpi !== undefined && rawSpi !== null && isFinite(rawSpi)) ? rawSpi : null,
        cpi: (rawCpi !== undefined && rawCpi !== null && isFinite(rawCpi)) ? rawCpi : null,
      };
    }

    // Fallback: Local calculation from schedule store
    const today = startOfDay(new Date());

    let totalBaselineCost = 0;
    let plannedValue = 0; // PV = baseline_cost where finish <= report_date
    let earnedValue = 0;  // EV = %complete * baseline_cost
    let actualCost = 0;   // AC = SUM(wo_value)

    tasks.forEach((task) => {
      const bCost = Number(task.baseline_cost ?? task.wo_value ?? 0);
      const woVal = Number(task.wo_value ?? 0);
      const bFinish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
      const percent = Number(task.percent_complete ?? 0) / 100;

      totalBaselineCost += bCost;
      earnedValue += percent * bCost;
      actualCost += woVal;

      // PV logic from Constitution §9: baseline_cost for tasks with baseline_finish <= today
      if (bFinish && !isAfter(bFinish, today)) {
        plannedValue += bCost;
      }
    });

    // Robustness: prevents misleading "1.00" on empty data or NaN propagation
    const rawSpi = (plannedValue > 0) ? earnedValue / plannedValue : null;
    const rawCpi = (actualCost > 0) ? earnedValue / actualCost : null;

    const spi = (rawSpi !== null && isFinite(rawSpi)) ? rawSpi : null;
    const cpi = (rawCpi !== null && isFinite(rawCpi)) ? (rawCpi > 10 ? 10 : rawCpi) : null;

    return {
      totalBaselineCost,
      plannedValue,
      earnedValue,
      actualCost,
      spi,
      cpi,
    };
  }, [tasks, backendStats]);

  const getSpiStatus = (spi: number) => {
    if (spi >= 1) return "positive";
    if (spi >= 0.85) return "warning";
    return "negative";
  };

  const getCpiStatus = (cpi: number) => {
    if (cpi >= 1) return "positive";
    if (cpi >= 0.9) return "warning";
    return "negative";
  };

  return (
    <div className="grid gap-5 grid-cols-2 md:grid-cols-3 xl:grid-cols-6">
      <KPICard
        label="Total Baseline"
        value={
          (backendStats?.is_baseline_initialized ?? stats.totalBaselineCost > 0) ? (
            formatINRShort(stats.totalBaselineCost)
          ) : (
            <div className="flex flex-col gap-2 w-full">
              <span className="text-lg font-bold text-foreground/50">Not Initialized</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onInitializeBaseline?.();
                }}
                className="mt-1 px-3 py-1.5 w-full bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-bold text-[10px] uppercase tracking-wider rounded-lg shadow-md border border-amber-400/20 transition-all duration-200 hover:scale-[1.03] active:scale-[0.97] flex items-center justify-center gap-1.5"
              >
                <Coins size={12} />
                Initialize Baseline
              </button>
            </div>
          )
        }
        subtitle={(backendStats?.is_baseline_initialized ?? stats.totalBaselineCost > 0) ? "Original project value" : "EVM setup required"}
        status={(backendStats?.is_baseline_initialized ?? stats.totalBaselineCost > 0) ? "neutral" : "warning"}
        icon={<Coins size={18} />}
        tooltip="The total original estimated cost (BAC) for all tasks in the current project scope."
        className={(backendStats?.is_baseline_initialized ?? stats.totalBaselineCost > 0) ? "" : "border-amber-500/20"}
      />
      <KPICard
        label="Planned Value"
        value={formatINRShort(stats.plannedValue)}
        subtitle="PV (Should be earned)"
        status="neutral"
        icon={<Timer size={18} />}
      />
      <KPICard
        label="Earned Value"
        value={formatINRShort(stats.earnedValue)}
        subtitle="EV (Work performed)"
        status={stats.earnedValue >= stats.plannedValue ? "positive" : "warning"}
        icon={<Activity size={18} />}
      />
      <KPICard
        label="Actual Cost"
        value={formatINRShort(stats.actualCost)}
        subtitle="AC (Work Order value)"
        status={stats.actualCost <= stats.earnedValue ? "positive" : "negative"}
        icon={<IndianRupee size={18} />}
      />
      <KPICard
        label="SPI"
        value={stats.spi !== null ? stats.spi.toFixed(2) : "N/A"}
        subtitle="Schedule Perf. (EV/PV)"
        status={stats.spi !== null ? getSpiStatus(stats.spi) : "neutral"}
        icon={<Gauge size={18} />}
        tooltip="Schedule Performance Index: Measures efficiency of time utilization (Earned Value / Planned Value). > 1.0 means project is ahead of schedule."
        trend={stats.spi !== null ? (() => {
          const val = (stats.spi - 1) * 100;
          if (Math.abs(val) > 1000) return ">1000%";
          return `${val.toFixed(1)}%`;
        })() : undefined}
        trendUp={stats.spi !== null ? stats.spi >= 1 : undefined}
      />
      <KPICard
        label="CPI"
        value={stats.cpi !== null ? stats.cpi.toFixed(2) : "N/A"}
        subtitle="Cost Perf. (EV/AC)"
        status={stats.cpi !== null ? getCpiStatus(stats.cpi) : "neutral"}
        icon={<BarChart3 size={18} />}
        tooltip="Cost Performance Index: Measures cost efficiency of work performed (Earned Value / Actual Cost). > 1.0 means project is under budget."
        trend={stats.cpi !== null ? (() => {
          const val = (stats.cpi - 1) * 100;
          if (Math.abs(val) > 1000) return ">1000%";
          return `${val.toFixed(1)}%`;
        })() : undefined}
        trendUp={stats.cpi !== null ? stats.cpi >= 1 : undefined}
      />
    </div>
  );
}
