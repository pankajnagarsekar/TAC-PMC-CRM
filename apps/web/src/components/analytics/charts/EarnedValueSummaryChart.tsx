"use client";

import React, { useMemo, useRef } from "react";
import AnalyticsExportBar from "../AnalyticsExportBar";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { formatINRShort } from "@/lib/formatters";
import { parseTaskDate } from "@/components/scheduler/scheduler-utils";
import { startOfMonth, endOfMonth, eachMonthOfInterval, isAfter, isBefore, format, differenceInCalendarDays, startOfDay } from "date-fns";

interface EarnedValueSummaryChartProps {
  tasks: ScheduleTask[];
}

const formatCurrency = (value: number) => formatINRShort(value);

export default function EarnedValueSummaryChart({ tasks }: EarnedValueSummaryChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);
  const today = useMemo(() => startOfDay(new Date()), []);
  const todayStr = useMemo(() => format(new Date(), "MMM yy"), []);

  const hasCostData = useMemo(() => {
    return tasks.some(t => Number(t.baseline_cost ?? 0) > 0 || Number(t.wo_value ?? 0) > 0);
  }, [tasks]);

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

    const months = eachMonthOfInterval({ start: horizonStart, end: horizonEnd });

    return months.map((month) => {
      const reportDate = endOfMonth(month);
      let cumulativePV = 0;
      let cumulativeEV = 0;
      let cumulativeAC = 0;

      tasks.forEach((task) => {
        const bStart = parseTaskDate(task.baseline_start || task.scheduled_start);
        const bFinish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
        
        const pvCost = Number(task.baseline_cost ?? 0);
        const evCost = Number(task.wo_value ?? task.baseline_cost ?? 0);
        const acCost = Number(task.payment_value ?? task.wo_value ?? 0);

        if (!bStart || !bFinish) return;

        // PV
        const bDuration = Math.max(1, differenceInCalendarDays(bFinish, bStart) + 1);
        if (!isAfter(bStart, reportDate)) {
          if (!isBefore(reportDate, bFinish)) {
            cumulativePV += pvCost;
          } else {
            const daysPlanned = differenceInCalendarDays(reportDate, bStart) + 1;
            cumulativePV += (pvCost / bDuration) * daysPlanned;
          }
        }

        // EV
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

        // AC
        if (!isAfter(month, today) && acCost > 0) {
          const aStart = parseTaskDate(task.actual_start || task.scheduled_start);
          if (aStart && !isAfter(aStart, reportDate)) {
            cumulativeAC += acCost;
          }
        }
      });

      return {
        name: format(month, "MMM yy"),
        PV: Math.round(cumulativePV),
        EV: isAfter(month, today) ? null : Math.round(cumulativeEV),
        AC: isAfter(month, today) ? null : Math.round(cumulativeAC),
      };
    });
  }, [tasks, today, dateLimits]);

  const stats = useMemo(() => {
    if (chartData.length === 0) return null;

    const completed = chartData.filter(d => d.EV !== null);
    const latest = completed[completed.length - 1] || chartData[0];

    const pv = latest.PV;
    const ev = latest.EV ?? 0;
    const ac = latest.AC ?? 0;

    const bac = tasks.reduce((sum, t) => sum + Number(t.baseline_cost ?? 0), 0);
    const sv = ev - pv;
    const cv = ev - ac;

    const spi = pv > 0 ? ev / pv : 1.0;
    const cpi = ac > 0 ? ev / ac : 1.0;

    // EAC = BAC / CPI
    const eac = cpi > 0 ? bac / cpi : bac;
    // VAC = BAC - EAC
    const vac = bac - eac;

    return { bac, pv, ev, ac, sv, cv, spi, cpi, eac, vac };
  }, [chartData, tasks]);

  const maxVal = useMemo(() => {
    if (chartData.length === 0) return 100;
    return Math.max(
      ...chartData.map(d => Math.max(d.PV || 0, d.EV || 0, d.AC || 0))
    );
  }, [chartData]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Earned Value Summary</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Performance measurement baseline projection (EVM)
          </p>
        </div>
        {chartData.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={chartData}
            columns={["name", "PV", "EV", "AC"]}
            title="Earned Value Summary"
            fileName="Earned_Value_Summary"
          />
        )}
      </div>

      <div className="h-[280px] w-full min-w-0">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%" debounce={100}>
            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-white/[0.03]" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                dy={5}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={formatCurrency}
                domain={[0, () => Math.round(maxVal * 1.1)]}
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
              <ReferenceLine
                x={todayStr}
                stroke="#fb923c"
                strokeDasharray="3 3"
                label={{ value: 'TODAY', position: 'top', fill: '#fb923c', fontSize: 8, fontWeight: 900 }}
              />
              <Legend
                verticalAlign="top"
                height={30}
                content={({ payload }) => (
                  <div className="flex justify-end gap-4 text-[9px] font-black uppercase tracking-wider text-slate-500">
                    {payload?.map((entry: any, index) => (
                      <div key={index} className="flex items-center gap-1.5">
                        <div className="h-1 w-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                        <span>{entry.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              />
              <Line type="monotone" dataKey="PV" name="Planned Value" stroke="#f59e0b" strokeWidth={3} dot={{ r: 0 }} />
              <Line type="monotone" dataKey="EV" name="Earned Value" stroke="#38bdf8" strokeWidth={3} dot={{ r: 0 }} connectNulls={false} />
              <Line type="monotone" dataKey="AC" name="Actual Cost" stroke="#ec4899" strokeWidth={3} dot={{ r: 0 }} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            No EVM data available. Add costs and baselines to display statistics.
          </div>
        )}
      </div>

      {/* EVM Dashboard Numbers */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-4 border-t border-slate-200 dark:border-white/5 text-[10px] font-bold text-slate-500">
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">PV (Planned Value)</span>
            <span className="text-xs font-black text-slate-900 dark:text-white mt-0.5 block">
              {hasCostData ? formatCurrency(stats.pv) : "N/A"}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">EV (Earned Value)</span>
            <span className="text-xs font-black text-slate-900 dark:text-white mt-0.5 block">
              {hasCostData ? formatCurrency(stats.ev) : "N/A"}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">AC (Actual Cost)</span>
            <span className="text-xs font-black text-slate-900 dark:text-white mt-0.5 block">
              {hasCostData ? formatCurrency(stats.ac) : "N/A"}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">SV (Schedule Variance)</span>
            <span className={`text-xs font-black mt-0.5 block ${!hasCostData ? "text-slate-400" : (stats.sv >= 0 ? "text-emerald-500" : "text-rose-500")}`}>
              {!hasCostData ? "N/A" : `${stats.sv >= 0 ? "+" : ""}${formatCurrency(stats.sv)}`}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">CV (Cost Variance)</span>
            <span className={`text-xs font-black mt-0.5 block ${!hasCostData ? "text-slate-400" : (stats.cv >= 0 ? "text-emerald-500" : "text-rose-500")}`}>
              {!hasCostData ? "N/A" : `${stats.cv >= 0 ? "+" : ""}${formatCurrency(stats.cv)}`}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">SPI</span>
            <span className={`text-xs font-black mt-0.5 block ${!hasCostData ? "text-slate-400" : (stats.spi >= 1.0 ? "text-emerald-500" : (stats.spi >= 0.9 ? "text-amber-500" : "text-rose-500"))}`}>
              {hasCostData ? stats.spi.toFixed(2) : "N/A"}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">CPI</span>
            <span className={`text-xs font-black mt-0.5 block ${!hasCostData ? "text-slate-400" : (stats.cpi >= 1.0 ? "text-emerald-500" : (stats.cpi >= 0.9 ? "text-amber-500" : "text-rose-500"))}`}>
              {hasCostData ? stats.cpi.toFixed(2) : "N/A"}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">EAC (Projected Cost)</span>
            <span className="text-xs font-black text-slate-900 dark:text-white mt-0.5 block">
              {hasCostData ? formatCurrency(stats.eac) : "N/A"}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">VAC (Variance at Completion)</span>
            <span className={`text-xs font-black mt-0.5 block ${!hasCostData ? "text-slate-400" : (stats.vac >= 0 ? "text-emerald-500" : "text-rose-500")}`}>
              {!hasCostData ? "N/A" : `${stats.vac >= 0 ? "+" : ""}${formatCurrency(stats.vac)}`}
            </span>
          </div>
          <div className="p-2.5 bg-slate-50 dark:bg-white/[0.01] border border-slate-100 dark:border-white/5 rounded-xl">
            <span className="text-[8px] font-black uppercase tracking-wider text-slate-400">BAC (Budget)</span>
            <span className="text-xs font-black text-slate-900 dark:text-white mt-0.5 block">
              {hasCostData ? formatCurrency(stats.bac) : "N/A"}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
