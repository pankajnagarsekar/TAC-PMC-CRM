"use client";

import React, { useMemo, useRef } from "react";
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
import { computeDelayTrend } from "@/lib/analyticsComputeEngine";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface DelayTrendChartProps {
  tasks: ScheduleTask[];
}

export default function DelayTrendChart({ tasks }: DelayTrendChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  const data = useMemo(() => {
    return computeDelayTrend(tasks, filters);
  }, [tasks, filters]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Delay / Slippage Trend</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Monthly progression of delayed task counts and average slippage days
          </p>
        </div>
        {data.length > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={data}
            columns={["month", "Delayed Tasks", "Avg Delay (Days)"]}
            title="Delay / Slippage Trend"
            fileName="Delay_Slippage_Trend"
          />
        )}
      </div>

      <div className="h-[340px] w-full min-w-0">
        {data.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%" debounce={100}>
            <ComposedChart
              data={data}
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
                yAxisId="left"
                tick={{ fill: "#64748b", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                label={{ value: "Delayed Count", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 9, style: { textAnchor: "middle" } }}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                tick={{ fill: "#64748b", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
                label={{ value: "Avg Delay (Days)", angle: 90, position: "insideRight", fill: "#64748b", fontSize: 9, style: { textAnchor: "middle" } }}
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
                formatter={(value: any, name: any) => [`${value} ${name.toLowerCase().includes('avg') ? 'Days' : 'Tasks'}`, name]}
              />
              <Legend
                verticalAlign="top"
                height={36}
                content={({ payload }) => (
                  <div className="flex justify-end gap-4 text-[9px] font-black uppercase tracking-wider text-slate-500">
                    {payload?.map((entry: any, index) => (
                      <div key={index} className="flex items-center gap-1.5">
                        <div className="h-1.5 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                        <span>{entry.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              />
              <Bar yAxisId="left" dataKey="Delayed Tasks" name="Delayed Tasks" fill="#ef4444" fillOpacity={0.6} radius={[4, 4, 0, 0]} maxBarSize={30} />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="Avg Delay (Days)"
                name="Avg Delay (Days)"
                stroke="#fb923c"
                strokeWidth={3}
                dot={{ r: 4, strokeWidth: 0, fill: "#fb923c" }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-slate-400">
            No delay trend data found for the selected project horizon.
          </div>
        )}
      </div>
    </div>
  );
}
