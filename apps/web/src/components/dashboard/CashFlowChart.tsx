"use client";

import React, { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, Cell } from "recharts";
import { format, startOfMonth, isBefore } from "date-fns";

import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";

/**
 * Cash Flow Forecaster component.
 * Visualizes projected payments based on task completion (WO Value).
 */
export default function CashFlowChart() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const chartData = useMemo(() => {
    const buckets = new Map<string, { key: string; name: string; value: number; date: Date }>();

    tasks.forEach((task) => {
      const finish = parseTaskDate(task.scheduled_finish || task.baseline_finish);
      if (!finish) return;

      const monthStart = startOfMonth(finish);
      const key = format(monthStart, "yyyy-MM");

      const existing = buckets.get(key) ?? {
        key,
        name: format(monthStart, "MMM yy"),
        value: 0,
        date: monthStart,
      };

      existing.value += Number(task.wo_value ?? 0);
      buckets.set(key, existing);
    });

    return Array.from(buckets.values()).sort((a, b) => a.key.localeCompare(b.key));
  }, [tasks]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("en-IN", {
      notation: "compact",
      style: "currency",
      currency: "INR",
    }).format(value);

  const today = startOfMonth(new Date());

  return (
    <div className="rounded-[24px] border border-white/5 bg-slate-950/60 p-5 shadow-2xl backdrop-blur-xl">
      <div className="mb-6">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">Cash Flow Forecast</h3>
        <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
          Work-order disbursement projections by month
        </p>
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fill: "#64748b", fontSize: 10, fontWeight: 600 }}
              axisLine={false}
              tickLine={false}
              dy={10}
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={formatCurrency}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: "12px",
                fontSize: "12px",
              }}
              cursor={{ fill: "rgba(255,255,255,0.03)" }}
              formatter={(value: number | undefined) => [formatCurrency(Number(value || 0)), "Projected"]}
            />
            <Bar dataKey="value" radius={[6, 6, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={isBefore(entry.date, today) ? "#475569" : "#f97316"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
