"use client";

import React, { useMemo, useRef } from "react";
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from "recharts";
import { format, startOfDay, isBefore, isAfter, startOfMonth, endOfMonth, eachMonthOfInterval, differenceInCalendarDays } from "date-fns";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { parseTaskDate } from "@/components/scheduler/scheduler-utils";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface PlannedVsActualChartProps {
  tasks: ScheduleTask[];
}

export default function PlannedVsActualChart({ tasks }: PlannedVsActualChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const today = useMemo(() => startOfDay(new Date()), []);
  const todayStr = useMemo(() => format(new Date(), "MMM yy"), []);
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

  const chartData = useMemo(() => {
    if (tasks.length === 0) return [];

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

    const months = eachMonthOfInterval({
      start: horizonStart,
      end: horizonEnd,
    });

    // Total units of progress is the sum of task durations (days)
    const totalDuration = tasks.reduce((sum, t) => sum + (t.scheduled_duration ?? 1), 0) || 1;

    return months.map((month) => {
      const reportDate = endOfMonth(month);
      let cumulativePlanned = 0;
      let cumulativeActual = 0;

      tasks.forEach((task) => {
        const bStart = parseTaskDate(task.baseline_start || task.scheduled_start);
        const bFinish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
        const duration = task.scheduled_duration ?? 1;

        if (!bStart || !bFinish) return;

        // --- Cumulative Planned Duration ---
        const bDuration = Math.max(1, differenceInCalendarDays(bFinish, bStart) + 1);
        if (!isAfter(bStart, reportDate)) {
          if (!isBefore(reportDate, bFinish)) {
            cumulativePlanned += duration;
          } else {
            const daysPlanned = differenceInCalendarDays(reportDate, bStart) + 1;
            cumulativePlanned += duration * (daysPlanned / bDuration);
          }
        }

        // --- Cumulative Actual Progress Duration ---
        if (!isAfter(month, today)) {
          const percent = Number(task.percent_complete ?? 0) / 100;
          cumulativeActual += duration * percent;
        }
      });

      const plannedPercent = Math.min(100, Math.round((cumulativePlanned / totalDuration) * 100));
      const actualPercent = isAfter(month, today)
        ? null
        : Math.min(100, Math.round((cumulativeActual / totalDuration) * 100));

      return {
        name: format(month, "MMM yy"),
        date: month,
        "Planned Progress (%)": plannedPercent,
        "Actual Progress (%)": actualPercent,
      };
    });
  }, [tasks, today, dateLimits]);

  return (
    <div ref={chartRef} className="space-y-4 h-full w-full relative">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Planned vs Actual Progress</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Cumulative weight-averaged percent complete trend over time
          </p>
        </div>
        {chartData.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={chartData}
            columns={["name", "Planned Progress (%)", "Actual Progress (%)"]}
            title="Planned vs Actual Progress"
            fileName="Planned_Vs_Actual_Progress"
          />
        )}
      </div>

      <div className="h-[340px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%" debounce={100}>
          <AreaChart data={chartData} margin={{ top: 20, right: 30, bottom: 10, left: 10 }}>
            <defs>
              <linearGradient id="colorPlanned" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.1}/>
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#38bdf8" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-white/[0.03]" vertical={false} />
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
              tickFormatter={(v) => `${v}%`}
              domain={[0, 100]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.9)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "12px",
                fontSize: "12px",
                color: "#fff",
                boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)"
              }}
              itemStyle={{ color: "#fff", padding: "2px 0" }}
              formatter={(value: any, name: any) => [`${Number(value || 0)}%`, name]}
            />
            <ReferenceLine
              x={todayStr}
              stroke="#fb923c"
              strokeDasharray="3 3"
              label={{ value: 'TODAY', position: 'top', fill: '#fb923c', fontSize: 8, fontWeight: 900 }}
            />
            <Legend
              verticalAlign="top"
              height={36}
              content={({ payload }) => (
                <div className="flex justify-end gap-4 text-[10px] font-black uppercase tracking-wider text-slate-500">
                  {payload?.map((entry: any, index) => (
                    <div key={index} className="flex items-center gap-1.5">
                      <div className="h-1.5 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                      <span>{entry.value}</span>
                    </div>
                  ))}
                </div>
              )}
            />
            <Area
              type="monotone"
              dataKey="Planned Progress (%)"
              name="Planned Progress"
              stroke="#f59e0b"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#colorPlanned)"
            />
            <Area
              type="monotone"
              dataKey="Actual Progress (%)"
              name="Actual Progress"
              stroke="#38bdf8"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#colorActual)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {chartData.length === 0 && (
        <div className="flex h-[300px] items-center justify-center text-slate-400">
          No tasks found matching active filters.
        </div>
      )}
    </div>
  );
}
