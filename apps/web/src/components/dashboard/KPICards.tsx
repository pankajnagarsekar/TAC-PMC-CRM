"use client";

import React, { useMemo } from "react";
import { Activity, BarChart3, Coins, DollarSign, Gauge, Timer } from "lucide-react";
import { startOfDay, isBefore, isAfter } from "date-fns";

import KPICard from "@/components/ui/KPICard";
import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    notation: "compact",
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 1,
  }).format(value);
}

/**
 * KPI Dashboard for Enterprise PPM.
 * Implements System Constitution §9 Earned Value Formulas.
 */
export default function KPICards() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const stats = useMemo(() => {
    const today = startOfDay(new Date());

    let totalBaselineCost = 0;
    let plannedValue = 0; // PV = baseline_cost where finish <= report_date
    let earnedValue = 0;  // EV = %complete * baseline_cost
    let actualCost = 0;   // AC = SUM(wo_value)

    tasks.forEach((task) => {
      const bCost = Number(task.baseline_cost ?? 0);
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
    const cpi = (rawCpi !== null && isFinite(rawCpi)) ? rawCpi : null;

    return {
      totalBaselineCost,
      plannedValue,
      earnedValue,
      actualCost,
      spi,
      cpi,
    };
  }, [tasks]);

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
        value={formatCurrency(stats.totalBaselineCost)}
        subtitle="Original project value"
        status="neutral"
        icon={<Coins size={18} />}
      />
      <KPICard
        label="Planned Value"
        value={formatCurrency(stats.plannedValue)}
        subtitle="PV (Should be earned)"
        status="neutral"
        icon={<Timer size={18} />}
      />
      <KPICard
        label="Earned Value"
        value={formatCurrency(stats.earnedValue)}
        subtitle="EV (Work performed)"
        status={stats.earnedValue >= stats.plannedValue ? "positive" : "warning"}
        icon={<Activity size={18} />}
      />
      <KPICard
        label="Actual Cost"
        value={formatCurrency(stats.actualCost)}
        subtitle="AC (Work Order value)"
        status={stats.actualCost <= stats.earnedValue ? "positive" : "negative"}
        icon={<DollarSign size={18} />}
      />
      <KPICard
        label="SPI"
        value={stats.spi !== null ? stats.spi.toFixed(2) : "N/A"}
        subtitle="Schedule Perf. (EV/PV)"
        status={stats.spi !== null ? getSpiStatus(stats.spi) : "neutral"}
        icon={<Gauge size={18} />}
        trend={stats.spi !== null ? `${((stats.spi - 1) * 100).toFixed(1)}%` : undefined}
        trendUp={stats.spi !== null ? stats.spi >= 1 : undefined}
      />
      <KPICard
        label="CPI"
        value={stats.cpi !== null ? stats.cpi.toFixed(2) : "N/A"}
        subtitle="Cost Perf. (EV/AC)"
        status={stats.cpi !== null ? getCpiStatus(stats.cpi) : "neutral"}
        icon={<BarChart3 size={18} />}
        trend={stats.cpi !== null ? `${((stats.cpi - 1) * 100).toFixed(1)}%` : undefined}
        trendUp={stats.cpi !== null ? stats.cpi >= 1 : undefined}
      />
    </div>
  );
}
