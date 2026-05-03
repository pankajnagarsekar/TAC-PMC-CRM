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
  ReferenceLine,
} from "recharts";
import {
  format,
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
import { formatINRShort } from "@/lib/formatters";

/**
 * S-Curve Chart implementation for Enterprise PPM Scheduler.
 * Refactored for Cumulative Aggregation (CRIT-005).
 */
interface SCurveChartProps {
  totalBudget?: number;
}

export default function SCurveChart({ totalBudget }: SCurveChartProps) {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);
  const today = useMemo(() => startOfDay(new Date()), []);

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

    const horizonStart = startOfMonth(projectStart);
    const horizonEnd = endOfMonth(projectEnd);

    // 2. Generate monthly intervals
    const months = eachMonthOfInterval({
      start: horizonStart,
      end: horizonEnd,
    });

    // 3. Project cumulative costs into intervals
    return months.map((month) => {
      const reportDate = endOfMonth(month);
      let cumulativePV = 0;
      let cumulativeEV = 0;

      tasks.forEach((task) => {
        const bStart = parseTaskDate(task.baseline_start || task.scheduled_start);
        const bFinish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
        
        const pvCost = Number(task.baseline_cost ?? 0);
        const evCost = Number(task.wo_value ?? task.baseline_cost ?? 0);

        if (!bStart || !bFinish || (pvCost === 0 && evCost === 0)) return;

        // --- Planned Value (PV) Cumulative ---
        const bDuration = Math.max(1, differenceInCalendarDays(bFinish, bStart) + 1);
        if (!isAfter(bStart, reportDate)) {
          if (!isBefore(reportDate, bFinish)) {
            // Task completely in the past relative to reportDate
            cumulativePV += pvCost;
          } else {
            // Task is currently active during the reportDate month
            const daysPlanned = differenceInCalendarDays(reportDate, bStart) + 1;
            cumulativePV += (pvCost / bDuration) * daysPlanned;
          }
        }

        // --- Earned Value (EV) Cumulative ---
        if (!isAfter(month, today)) {
          const percent = Number(task.percent_complete ?? 0) / 100;
          const taskEV = evCost * percent;
          
          if (percent > 0) {
            const aStart = parseTaskDate(task.actual_start || task.scheduled_start);
            const aFinish = parseTaskDate(task.actual_finish || task.scheduled_finish);
            
            if (task.percent_complete === 100 && aFinish) {
               if (!isAfter(aFinish, reportDate)) {
                 cumulativeEV += evCost;
               }
            } else if (aStart && !isAfter(aStart, reportDate)) {
               cumulativeEV += taskEV;
            }
          }
        }
      });

      return {
        name: format(month, "MMM yy"),
        date: month,
        PV: Math.round(cumulativePV),
        EV: isAfter(month, today) ? null : Math.round(cumulativeEV),
      };
    });
  }, [tasks, today]);

  const formatCurrency = (value: number) => formatINRShort(value);

  return (
    <div className="rounded-[24px] border border-slate-200 dark:border-white/5 bg-white/60 dark:bg-slate-950/60 p-5 shadow-2xl backdrop-blur-xl">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">S-Curve Analysis</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Cumulative Planned vs Earned Value
          </p>
        </div>
        <div className="flex gap-4">
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-3 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]" />
            <span className="text-[10px] font-bold text-slate-500 dark:text-white/30 uppercase tracking-wider">PV</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-3 rounded-full bg-sky-500 shadow-[0_0_8px_rgba(56,189,248,0.4)]" />
            <span className="text-[10px] font-bold text-slate-500 dark:text-white/30 uppercase tracking-wider">EV</span>
          </div>
        </div>
      </div>

      <div className="h-[400px] w-full min-w-0 overflow-hidden">
        <ResponsiveContainer width="100%" height="100%" debounce={100}>
          <LineChart data={chartData} margin={{ top: 20, right: 30, bottom: 10, left: 10 }}>
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
              tickFormatter={formatCurrency}
              domain={[0, (dataMax: number) => Math.round(Math.max(dataMax, totalBudget || 0) * 1.1)]}
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
              formatter={(value: number | undefined) => [formatCurrency(Number(value || 0)), ""]}
            />
            <ReferenceLine
              x={format(new Date(), "MMM yy")}
              stroke="#fb923c"
              strokeDasharray="3 3"
              label={{ value: 'TODAY', position: 'top', fill: '#fb923c', fontSize: 8, fontWeight: 900 }}
            />
            <Line
              type="monotone"
              dataKey="PV"
              stroke="#f59e0b"
              strokeWidth={4}
              dot={{ r: 0 }}
              activeDot={{ r: 6, strokeWidth: 0, fill: "#f59e0b" }}
            />
            <Line
              type="monotone"
              dataKey="EV"
              stroke="#38bdf8"
              strokeWidth={4}
              dot={{ r: 0 }}
              connectNulls={false}
              activeDot={{ r: 6, strokeWidth: 0, fill: "#38bdf8" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      
      {chartData.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900/10 backdrop-blur-[2px] rounded-[24px]">
          <div className="text-center">
            <p className="text-sm font-bold text-slate-500 uppercase tracking-widest">No Economic Data Available</p>
            <p className="text-[10px] text-slate-400 mt-1">Add baseline costs to tasks to generate S-Curve</p>
          </div>
        </div>
      )}
    </div>
  );
}
