"use client";

import React, { useMemo, useRef } from "react";
import {
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  LabelList,
} from "recharts";
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { computeScheduleVariance } from "@/lib/analyticsComputeEngine";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface ScheduleVarianceChartProps {
  tasks: ScheduleTask[];
}

export default function ScheduleVarianceChart({ tasks }: ScheduleVarianceChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  const data = useMemo(() => {
    return computeScheduleVariance(tasks, filters);
  }, [tasks, filters]);

  // Max absolute variance for scaling domain symmetrically
  const maxVal = useMemo(() => {
    if (data.length === 0) return 10;
    const vals = data.map(d => Math.abs(d.variance));
    return Math.max(...vals, 5);
  }, [data]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Baseline vs Current Schedule Variance</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Average schedule slippage in days grouped by view level (positive = delay, negative/zero = ahead/on-time)
          </p>
        </div>
        {data.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={data}
            columns={["name", "variance"]}
            title="Baseline vs Current Schedule Variance"
            fileName="Schedule_Variance"
          />
        )}
      </div>

      <div className="h-[340px] w-full min-w-0">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%" debounce={100}>
            <BarChart
              data={data}
              margin={{ top: 25, right: 30, left: 10, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-white/[0.03]" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                dy={10}
              />
              <YAxis
                domain={[-maxVal, maxVal]}
                tick={{ fill: "#64748b", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${v > 0 ? "+" : ""}${v}d`}
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
                formatter={(value: any, _name: any) => [`${value > 0 ? "+" : ""}${value} Days`, "Variance"]}
              />
              <ReferenceLine y={0} stroke="#64748b" strokeOpacity={0.2} />
              <Bar dataKey="variance" maxBarSize={40}>
                {data.map((entry) => {
                  const color = entry.variance > 0 ? "#ef4444" : "#10b981";
                  return <Cell key={entry.name} fill={color} />;
                })}
                <LabelList
                  dataKey="variance"
                  position="top"
                  formatter={(v: any) => `${v > 0 ? "+" : ""}${v}d`}
                  style={{ fill: "#64748b", fontSize: 12, fontWeight: 700 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            No schedule variance data found.
          </div>
        )}
      </div>
    </div>
  );
}
