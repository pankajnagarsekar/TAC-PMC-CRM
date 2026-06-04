"use client";

import React, { useMemo, useRef } from "react";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from "recharts";
import { format, startOfDay, isBefore, isAfter, startOfMonth, endOfMonth, eachMonthOfInterval, differenceInCalendarDays } from "date-fns";
import { useScheduleStore } from "@/store/useScheduleStore";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";
import { formatINRShort } from "@/lib/formatters";
import AnalyticsExportBar from "../analytics/AnalyticsExportBar";

interface SCurveChartProps {
  totalBudget?: number;
  pure?: boolean;
}

const formatCurrency = (value: number) => formatINRShort(value);

export default function SCurveChart({ totalBudget: _totalBudget, pure = false }: SCurveChartProps) {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const rawTasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  const today = useMemo(() => startOfDay(new Date()), []);
  const todayStr = useMemo(() => format(new Date(), "MMM yy"), []);

  const hasCostData = useMemo(() => {
    return rawTasks.some(t => Number(t.baseline_cost ?? 0) > 0 || Number(t.wo_value ?? 0) > 0);
  }, [rawTasks]);

  const isPercentScale = !hasCostData;

  // Filter tasks if not in pure mode
  const tasks = useMemo(() => {
    if (pure) return rawTasks;
    
    let filtered = [...rawTasks];
    if (filters.criticalOnly) filtered = filtered.filter(t => t.is_critical);
    if (filters.milestonesOnly) filtered = filtered.filter(t => t.is_milestone);
    if (filters.statusFilter && filters.statusFilter.length > 0) {
      filtered = filtered.filter(t => t.task_status && filters.statusFilter!.includes(t.task_status));
    }
    return filtered;
  }, [rawTasks, filters, pure]);

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

    const totalWeight = tasks.reduce((sum, t) => sum + Number(t.weightage_percent ?? t.scheduled_duration ?? 1), 0) || 1;

    return months.map((month) => {
      const reportDate = endOfMonth(month);
      let cumulativePV = 0;
      let cumulativeEV = 0;
      let cumulativeAC = 0;

      tasks.forEach((task) => {
        const bStart = parseTaskDate(task.baseline_start || task.scheduled_start);
        const bFinish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
        
        const weight = Number(task.weightage_percent ?? task.scheduled_duration ?? 1);
        const pvCost = hasCostData ? Number(task.baseline_cost ?? 0) : weight;
        const evCost = hasCostData ? Number(task.wo_value ?? task.baseline_cost ?? 0) : weight;
        const acCost = hasCostData ? Number(task.payment_value ?? task.wo_value ?? 0) : 0;

        if (!bStart || !bFinish) return;

        // --- Planned Value (PV) Cumulative ---
        const bDuration = Math.max(1, differenceInCalendarDays(bFinish, bStart) + 1);
        if (!isAfter(bStart, reportDate)) {
          if (!isBefore(reportDate, bFinish)) {
            cumulativePV += pvCost;
          } else {
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

        // --- Actual Cost (AC) Cumulative ---
        if (hasCostData && !isAfter(month, today) && acCost > 0) {
          const aStart = parseTaskDate(task.actual_start || task.scheduled_start);
          if (aStart && !isAfter(aStart, reportDate)) {
            cumulativeAC += acCost;
          }
        }
      });

      if (isPercentScale) {
        return {
          name: format(month, "MMM yy"),
          date: month,
          PV: Math.min(100, Math.round((cumulativePV / totalWeight) * 100)),
          EV: isAfter(month, today) ? null : Math.min(100, Math.round((cumulativeEV / totalWeight) * 100)),
          AC: null,
        };
      } else {
        return {
          name: format(month, "MMM yy"),
          date: month,
          PV: Math.round(cumulativePV),
          EV: isAfter(month, today) ? null : Math.round(cumulativeEV),
          AC: isAfter(month, today) ? null : Math.round(cumulativeAC),
        };
      }
    });
  }, [tasks, today, dateLimits, hasCostData, isPercentScale]);

  // Compute EVM Summary Row for below-chart display
  const evmMetrics = useMemo(() => {
    if (chartData.length === 0) return null;
    
    // Find the latest entry that has EV/AC data
    const completedEntries = chartData.filter(d => d.EV !== null);
    const latest = completedEntries[completedEntries.length - 1] || chartData[0];
    
    const pv = latest.PV;
    const ev = latest.EV ?? 0;
    const ac = latest.AC ?? 0;
    
    const sv = hasCostData ? ev - pv : null;
    const cv = hasCostData ? ev - ac : null;
    const spi = hasCostData && pv > 0 ? ev / pv : (hasCostData ? 1.0 : null);
    const cpi = hasCostData && ac > 0 ? ev / ac : (hasCostData ? 1.0 : null);
    const progress = rawTasks.length > 0
      ? Math.round(rawTasks.reduce((sum, t) => sum + (t.percent_complete ?? 0), 0) / rawTasks.length)
      : 0;

    return { pv, ev, ac, sv, cv, spi, cpi, progress };
  }, [chartData, rawTasks, hasCostData]);

  const maxBudget = useMemo(() => {
    if (chartData.length === 0) return 100;
    return Math.max(
      ...chartData.map(d => Math.max(d.PV || 0, d.EV || 0, d.AC || 0))
    );
  }, [chartData]);

  if (pure) {
    return (
      <div className="h-full w-full relative">
        <div className="h-full w-full min-w-0">
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
                tickFormatter={isPercentScale ? (v) => `${v}%` : formatCurrency}
                domain={isPercentScale ? [0, 100] : [0, Math.round(maxBudget * 1.1)]}
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
                formatter={(value: any, name: any) => [isPercentScale ? `${value}%` : formatCurrency(Number(value || 0)), name]}
              />
              <ReferenceLine
                x={todayStr}
                stroke="#fb923c"
                strokeDasharray="3 3"
                label={{ value: 'TODAY', position: 'top', fill: '#fb923c', fontSize: 8, fontWeight: 900 }}
              />
              <Line
                type="monotone"
                dataKey="PV"
                name="Planned Value (PV)"
                stroke="#f59e0b"
                strokeWidth={3}
                dot={{ r: 0 }}
                activeDot={{ r: 6, strokeWidth: 0, fill: "#f59e0b" }}
              />
              <Line
                type="monotone"
                dataKey="EV"
                name="Earned Value (EV)"
                stroke="#38bdf8"
                strokeWidth={3}
                dot={{ r: 0 }}
                connectNulls={false}
                activeDot={{ r: 6, strokeWidth: 0, fill: "#38bdf8" }}
              />
              {!isPercentScale && filters?.costEnabled && (
                <Line
                  type="monotone"
                  dataKey="AC"
                  name="Actual Cost (AC)"
                  stroke="#f43f5e"
                  strokeWidth={3}
                  dot={{ r: 0 }}
                  connectNulls={false}
                  activeDot={{ r: 6, strokeWidth: 0, fill: "#f43f5e" }}
                />
              )}
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

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full relative">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">S-Curve Analysis</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Cumulative Planned vs Earned Value vs Actual Cost
          </p>
        </div>
        {chartData.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={chartData}
            columns={isPercentScale ? ["name", "PV", "EV"] : ["name", "PV", "EV", "AC"]}
            title="S-Curve Analysis"
            fileName="S_Curve_Analysis"
          />
        )}
      </div>

      <div className="h-[350px] w-full min-w-0 overflow-hidden">
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
              tickFormatter={isPercentScale ? (v) => `${v}%` : formatCurrency}
              domain={isPercentScale ? [0, 100] : [0, Math.round(maxBudget * 1.1)]}
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
              formatter={(value: any, name: any) => [isPercentScale ? `${value}%` : formatCurrency(Number(value || 0)), name]}
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
                  {payload?.filter(entry => !isPercentScale || entry.value !== "Actual Cost (AC)").map((entry: any, index) => (
                    <div key={index} className="flex items-center gap-1.5">
                      <div className="h-1.5 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                      <span>{entry.value}</span>
                    </div>
                  ))}
                </div>
              )}
            />
            <Line
              type="monotone"
              dataKey="PV"
              name="Planned Value (PV)"
              stroke="#f59e0b"
              strokeWidth={4}
              dot={{ r: 0 }}
              activeDot={{ r: 6, strokeWidth: 0, fill: "#f59e0b" }}
            />
            <Line
              type="monotone"
              dataKey="EV"
              name="Earned Value (EV)"
              stroke="#38bdf8"
              strokeWidth={4}
              dot={{ r: 0 }}
              connectNulls={false}
              activeDot={{ r: 6, strokeWidth: 0, fill: "#38bdf8" }}
            />
            {!isPercentScale && (
              <Line
                type="monotone"
                dataKey="AC"
                name="Actual Cost (AC)"
                stroke="#ec4899"
                strokeWidth={4}
                dot={{ r: 0 }}
                connectNulls={false}
                activeDot={{ r: 6, strokeWidth: 0, fill: "#ec4899" }}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* S-Curve metrics summary row */}
      {evmMetrics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4 pt-4 border-t border-slate-200 dark:border-white/5">
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">Planned Value (PV)</span>
            <span className="text-sm font-black text-slate-900 dark:text-white mt-1 block">
              {isPercentScale ? `${evmMetrics.pv}%` : formatCurrency(evmMetrics.pv)}
            </span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">Earned Value (EV)</span>
            <span className="text-sm font-black text-slate-900 dark:text-white mt-1 block">
              {isPercentScale ? `${evmMetrics.ev}%` : formatCurrency(evmMetrics.ev)}
            </span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">Actual Cost (AC)</span>
            <span className="text-sm font-black text-slate-900 dark:text-white mt-1 block">
              {isPercentScale ? "N/A" : formatCurrency(evmMetrics.ac)}
            </span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">Schedule Var (SV)</span>
            <span className={`text-sm font-black mt-1 block ${evmMetrics.sv === null ? "text-slate-400" : (evmMetrics.sv >= 0 ? "text-emerald-500" : "text-rose-500")}`}>
              {evmMetrics.sv === null ? "N/A" : `${evmMetrics.sv > 0 ? "+" : ""}${formatCurrency(evmMetrics.sv)}`}
            </span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">Cost Var (CV)</span>
            <span className={`text-sm font-black mt-1 block ${evmMetrics.cv === null ? "text-slate-400" : (evmMetrics.cv >= 0 ? "text-emerald-500" : "text-rose-500")}`}>
              {evmMetrics.cv === null ? "N/A" : `${evmMetrics.cv > 0 ? "+" : ""}${formatCurrency(evmMetrics.cv)}`}
            </span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">SPI (Schedule)</span>
            <span className={`text-sm font-black mt-1 block ${evmMetrics.spi === null ? "text-slate-400" : (evmMetrics.spi >= 1.0 ? "text-emerald-500" : (evmMetrics.spi >= 0.9 ? "text-amber-500" : "text-rose-500"))}`}>
              {evmMetrics.spi === null ? "N/A" : evmMetrics.spi.toFixed(2)}
            </span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">CPI (Cost)</span>
            <span className={`text-sm font-black mt-1 block ${evmMetrics.cpi === null ? "text-slate-400" : (evmMetrics.cpi >= 1.0 ? "text-emerald-500" : (evmMetrics.cpi >= 0.9 ? "text-amber-500" : "text-rose-500"))}`}>
              {evmMetrics.cpi === null ? "N/A" : evmMetrics.cpi.toFixed(2)}
            </span>
          </div>
          <div className="p-3 bg-slate-50 dark:bg-white/[0.02] rounded-xl border border-slate-100 dark:border-white/5">
            <span className="text-[8px] font-black text-slate-400 uppercase tracking-widest block">% Complete</span>
            <span className="text-sm font-black text-slate-900 dark:text-white mt-1 block">{evmMetrics.progress}%</span>
          </div>
        </div>
      )}

      {chartData.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-950/10 backdrop-blur-[2px] rounded-[24px]">
          <div className="text-center">
            <p className="text-sm font-bold text-slate-500 uppercase tracking-widest">No Economic Data Available</p>
            <p className="text-[10px] text-slate-400 mt-1">Add baseline dates to tasks to generate S-Curve</p>
          </div>
        </div>
      )}
    </div>
  );
}
