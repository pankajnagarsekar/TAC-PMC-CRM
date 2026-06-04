"use client";

import React, { useMemo, useRef, useState, useEffect } from "react";
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { schedulerApi } from "@/lib/api";
import { formatINRShort } from "@/lib/formatters";
import { parseTaskDate } from "@/components/scheduler/scheduler-utils";
import { startOfMonth, endOfMonth, eachMonthOfInterval, isAfter, isBefore, format, startOfDay } from "date-fns";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface CashFlowProjectionChartProps {
  tasks: ScheduleTask[];
  projectId?: string;
}

const formatCurrency = (value: number) => formatINRShort(value);

export default function CashFlowProjectionChart({ tasks, projectId }: CashFlowProjectionChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  const dateLimits = useMemo<{ startLimit: Date | null; endLimit: Date | null }>(() => {
    const today = new Date();
    let startLimit: Date | null = null;
    let endLimit: Date | null = null;

    if (filters.dateRange === 'this_month') {
      startLimit = startOfMonth(today);
      endLimit = endOfMonth(today);
    } else if (filters.dateRange === 'next_30') {
      startLimit = startOfDay(today);
      endLimit = endOfMonth(new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000));
    } else if (filters.dateRange === 'quarter') {
      const quarter = Math.floor(today.getMonth() / 3);
      startLimit = startOfMonth(new Date(today.getFullYear(), quarter * 3, 1));
      endLimit = endOfMonth(new Date(today.getFullYear(), (quarter + 1) * 3, 0));
    } else if (filters.dateRange === 'custom') {
      if (filters.customDateStart) startLimit = startOfDay(new Date(filters.customDateStart));
      if (filters.customDateEnd) endLimit = endOfMonth(new Date(filters.customDateEnd));
    }
    return { startLimit, endLimit };
  }, [filters.dateRange, filters.customDateStart, filters.customDateEnd]);

  // Client-side projection computation (No API call to avoid 404 Axios interceptor error toasts)
  const chartData = useMemo(() => {
    if (tasks.length === 0) return [];

    // Calculate project horizon
    let projectStart: Date | null = null;
    let projectEnd: Date | null = null;

    for (const task of tasks) {
      const start = parseTaskDate(task.baseline_start || task.scheduled_start);
      const finish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
      if (!start || !finish) continue;

      if (!projectStart || isBefore(start, projectStart)) projectStart = start;
      if (!projectEnd || isAfter(finish, projectEnd)) projectEnd = finish;
    }

    if (!projectStart || !projectEnd) return [];

    let horizonStart = startOfMonth(projectStart);
    let horizonEnd = endOfMonth(projectEnd);

    const { startLimit, endLimit } = dateLimits;
    if (startLimit) horizonStart = startLimit;
    if (endLimit) horizonEnd = endLimit;

    if (isAfter(horizonStart, horizonEnd)) {
      horizonStart = startOfMonth(projectStart);
      horizonEnd = endOfMonth(projectEnd);
    }

    const months = eachMonthOfInterval({ start: horizonStart, end: horizonEnd });

    return months.map((month) => {
      const mStart = startOfMonth(month);
      const mEnd = endOfMonth(month);
      let planned = 0;
      let actual = 0;

      for (const t of tasks) {
        const tStart = parseTaskDate(t.baseline_start || t.scheduled_start);
        const tFinish = parseTaskDate(t.baseline_finish || t.scheduled_finish);
        const cost = Number(t.baseline_cost ?? 0);
        const actualCost = Number(t.payment_value ?? t.wo_value ?? 0);

        if (!tStart || !tFinish || cost === 0) continue;

        // Distribute cost over task months duration (time-phasing)
        const totalTaskDays = Math.max(1, Math.round((tFinish.getTime() - tStart.getTime()) / (1000 * 60 * 60 * 24)) + 1);
        
        // Calculate overlapping days between task and this month
        const overlapStart = new Date(Math.max(tStart.getTime(), mStart.getTime()));
        const overlapEnd = new Date(Math.min(tFinish.getTime(), mEnd.getTime()));
        const overlapDays = Math.max(0, Math.round((overlapEnd.getTime() - overlapStart.getTime()) / (1000 * 60 * 60 * 24)) + 1);

        if (overlapDays > 0) {
          planned += cost * (overlapDays / totalTaskDays);
          if (actualCost > 0) {
            actual += actualCost * (overlapDays / totalTaskDays);
          }
        }
      }

      return {
        month: format(month, "MMM yy"),
        "Planned Outflow": Math.round(planned),
        "Actual Outflow": isAfter(month, new Date()) ? null : Math.round(actual),
      };
    });
  }, [tasks, dateLimits]);

  const maxVal = useMemo(() => {
    if (chartData.length === 0) return 0;
    return Math.max(
      ...chartData.map((d) =>
        Math.max(Number(d["Planned Outflow"] || 0), Number(d["Actual Outflow"] || 0))
      )
    );
  }, [chartData]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Cash Flow Projection</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Projected monthly cash outflow distribution (Planned vs Actual payments)
          </p>
        </div>
        {chartData.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={chartData}
            columns={["month", "Planned Outflow", "Actual Outflow"]}
            title="Cash Flow Projection"
            fileName="Cash_Flow_Projection"
          />
        )}
      </div>

      <div className="h-[340px] w-full min-w-0">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%" debounce={100}>
            <ComposedChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 10, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-white/[0.03]" vertical={false} />
              <XAxis
                dataKey="month"
                tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                dy={10}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={formatCurrency}
                domain={[0, maxVal > 0 ? "auto" : 100000]}
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
                formatter={(value: any, name: any) => [formatCurrency(Number(value || 0)), name]}
              />
              <Legend
                verticalAlign="top"
                height={36}
                content={({ payload }) => (
                  <div className="flex justify-end gap-4 text-[10px] font-black uppercase tracking-wider text-slate-500">
                    {payload?.map((entry: any) => (
                      <div key={entry.value} className="flex items-center gap-1.5">
                        <div className="h-1.5 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                        <span>{entry.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              />
              <Bar dataKey="Planned Outflow" name="Planned Outflow" fill="#505f7a" fillOpacity={0.6} radius={[4, 4, 0, 0]} maxBarSize={35} />
              <Line
                type="monotone"
                dataKey="Actual Outflow"
                name="Actual Outflow"
                stroke="#10b981"
                strokeWidth={3}
                dot={{ r: 4, strokeWidth: 0, fill: "#10b981" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            No projection data available. Add tasks and baseline costs to map projection.
          </div>
        )}
      </div>
    </div>
  );
}
