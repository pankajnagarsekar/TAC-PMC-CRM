"use client";

import React, { useMemo } from "react";
import { Activity, CalendarRange, DollarSign, Route } from "lucide-react";

import KPICard from "@/components/ui/KPICard";
import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder } from "@/components/scheduler/scheduler-utils";

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

export default function KPICards() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const totalBaselineCost = tasks.reduce((sum, task) => sum + Number(task.baseline_cost ?? 0), 0);
  const earnedValue = tasks.reduce(
    (sum, task) => sum + (Number(task.percent_complete ?? 0) / 100) * Number(task.baseline_cost ?? 0),
    0,
  );
  const criticalCount = tasks.filter((task) => task.is_critical).length;
  const activeCount = tasks.filter((task) => (task.percent_complete ?? 0) > 0 && (task.percent_complete ?? 0) < 100).length;

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KPICard
        label="Baseline Cost"
        value={formatCurrency(totalBaselineCost)}
        subtitle="Current cumulative baseline"
        status="neutral"
        icon={<DollarSign size={18} />}
      />
      <KPICard
        label="Earned Value"
        value={formatCurrency(earnedValue)}
        subtitle="Percent complete weighted by baseline cost"
        status={earnedValue >= totalBaselineCost ? "positive" : "warning"}
        icon={<Activity size={18} />}
      />
      <KPICard
        label="Critical Tasks"
        value={criticalCount}
        subtitle="Tasks currently flagged critical"
        status={criticalCount > 0 ? "negative" : "positive"}
        icon={<Route size={18} />}
      />
      <KPICard
        label="In Flight"
        value={activeCount}
        subtitle="Tasks actively in progress"
        status="neutral"
        icon={<CalendarRange size={18} />}
      />
    </div>
  );
}
