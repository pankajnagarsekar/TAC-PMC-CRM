"use client";

import React, { useMemo } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from "recharts";
import {
  format,
  addDays,
  differenceInCalendarDays,
  startOfDay,
  isBefore,
  isAfter,
  eachMonthOfInterval,
  endOfMonth,
  startOfMonth,
} from "date-fns";

import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";

/**
 * S-Curve Chart implementation for Enterprise PPM Scheduler.
 * Follows System Constitution §9 formulas:
 * PV: Time-phased linear distribution of baseline_cost.
 * EV: Live earned value calculated from percent_complete * baseline_cost.
 */
export default function SCurveChart() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const chartData = useMemo(() => {
    if (tasks.length === 0) return [];

    // 1. Determine Project Horizon
    let projectStart: Date | null = null;
    let projectEnd: Date | null = null;

    tasks.forEach((task) => {
      const start = parseTaskDate(task.baseline_start || task.scheduled_start);
      const finish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
      if (!start || !finish) return;

      if (!projectStart || isBefore(start, projectStart)) projectStart = start;
      if (!projectEnd || isAfter(finish, projectEnd)) projectEnd = finish;
    });

    if (!projectStart || !projectEnd) return [];

    // Buffer dates to start and end of months
    const horizonStart = startOfMonth(projectStart);
    const horizonEnd = endOfMonth(projectEnd);
    const today = startOfDay(new Date());

    // 2. Generate monthly intervals
    const months = eachMonthOfInterval({
      start: horizonStart,
      end: horizonEnd,
    });

    // 3. Project costs into intervals
    return months.map((month) => {
      const reportDate = endOfMonth(month);
      let totalPV = 0;
      let totalEV = 0;

      tasks.forEach((task) => {
        const bStart = parseTaskDate(task.baseline_start || task.scheduled_start);
        const bFinish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
        const baselineCost = Number(task.baseline_cost ?? 0);

        if (!bStart || !bFinish || baselineCost <= 0) return;

        // --- Planned Value (PV) Logic ---
        // Formula: linear distribution across baseline duration
        const bDuration = Math.max(1, differenceInCalendarDays(bFinish, bStart) + 1);
        const dailyPV = baselineCost / bDuration;

        if (!isAfter(bStart, reportDate)) {
          const daysPlanned = Math.min(
            bDuration,
            differenceInCalendarDays(
              isBefore(reportDate, bFinish) ? reportDate : bFinish,
              bStart
            ) + 1
          );
          totalPV += dailyPV * Math.max(0, daysPlanned);
        }

        // --- Earned Value (EV) Logic ---
        // Formula: Current Earned Value = (percent / 100) * baseline_cost
        // For the chart, we show actual status up to today.
        const percent = Number(task.percent_complete ?? 0) / 100;
        const currentTaskEV = baselineCost * percent;

        // If today is after or during this month, we can show EV
        // (Note: Without history, we assume EV progressed linearly to today)
        if (!isAfter(reportDate, today) || (!isAfter(month, today) && !isBefore(reportDate, today))) {
          const aStart = parseTaskDate(task.actual_start || task.scheduled_start);
          const aFinish = parseTaskDate(task.actual_finish || task.scheduled_finish);

          if (aStart) {
            // Task has started or is complete
            if (task.percent_complete === 100 && aFinish && !isAfter(aFinish, reportDate)) {
              totalEV += baselineCost;
            } else if (percent > 0) {
              // Interpolate EV if reportDate is before or at today
              const effectiveEnd = aFinish || today;
              const timeSpent = Math.max(1, differenceInCalendarDays(effectiveEnd, aStart) + 1);
              const daysToReport = Math.min(
                timeSpent,
                differenceInCalendarDays(
                  isBefore(reportDate, effectiveEnd) ? reportDate : effectiveEnd,
                  aStart
                ) + 1
              );
              totalEV += (currentTaskEV / timeSpent) * Math.max(0, daysToReport);
            }
          }
        } else if (isAfter(month, today)) {
          // Future months: EV is blank (or we could flatline it)
          // Placeholder: Not adding to totalEV for future intervals
        }
      });

      return {
        name: format(month, "MMM yy"),
        date: month,
        PV: Math.round(totalPV),
        EV: isAfter(month, today) ? null : Math.round(totalEV),
      };
    });
  }, [tasks]);

  const formatCurrency = (value: number) =>
    new Intl.NumberFormat("en-IN", {
      notation: "compact",
      style: "currency",
      currency: "INR",
    }).format(value);

  return (
    <div className="rounded-[24px] border border-white/5 bg-slate-950/60 p-5 shadow-2xl backdrop-blur-xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">S-Curve Analysis</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Cumulative Planned vs Earned Value
          </p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-3 rounded-full bg-[#f59e0b]" />
            <span className="text-[10px] font-bold text-white/30 uppercase tracking-wider">PV</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-3 rounded-full bg-[#38bdf8]" />
            <span className="text-[10px] font-bold text-white/30 uppercase tracking-wider">EV</span>
          </div>
        </div>
      </div>

      <div className="h-[300px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
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
              formatter={(value: any) => [formatCurrency(Number(value || 0)), ""]}
            />
            <Line
              type="monotone"
              dataKey="PV"
              stroke="#f59e0b"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
            <Line
              type="monotone"
              dataKey="EV"
              stroke="#38bdf8"
              strokeWidth={3}
              dot={false}
              connectNulls={false}
              activeDot={{ r: 4, strokeWidth: 0 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
