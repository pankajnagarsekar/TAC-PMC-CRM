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

    const spi = plannedValue > 0 ? earnedValue / plannedValue : 1;
    const cpi = actualCost > 0 ? earnedValue / actualCost : 1;

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
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-3 2xl:grid-cols-6">
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
        value={stats.spi.toFixed(2)}
        subtitle="Schedule Performance (EV/PV)"
        status={getSpiStatus(stats.spi)}
        icon={<Gauge size={18} />}
        trend={`${((stats.spi - 1) * 100).toFixed(1)}%`}
        trendUp={stats.spi >= 1}
      />
      <KPICard
        label="CPI"
        value={stats.cpi.toFixed(2)}
        subtitle="Cost Performance (EV/AC)"
        status={getCpiStatus(stats.cpi)}
        icon={<BarChart3 size={18} />}
        trend={`${((stats.cpi - 1) * 100).toFixed(1)}%`}
        trendUp={stats.cpi >= 1}
      />
    </div>
  );
}
