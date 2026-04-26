"use client";

import React, { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { format, parseISO } from "date-fns";

interface DayMetric {
  date: string;
  value: number;
}

interface TaskTimelineProps {
  daily_completion: DayMetric[];
  utilization_trend?: DayMetric[];
  title?: string;
}

export default function TaskTimeline({
  daily_completion,
  utilization_trend,
  title = "Task Completion Trend",
}: TaskTimelineProps) {
  const chartData = useMemo(() => {
    if (!daily_completion.length) return [];

    interface ChartDataPoint {
      date: string;
      tasks: number;
      utilization?: number;
    }

    return daily_completion.map((item, index) => {
      const dataPoint: ChartDataPoint = {
        date: format(parseISO(item.date), "MMM dd"),
        tasks: item.value,
      };

      if (utilization_trend && index < utilization_trend.length) {
        dataPoint.utilization = utilization_trend[index].value;
      }

      return dataPoint;
    });
  }, [daily_completion, utilization_trend]);

  const totalTasks = useMemo(
    () => daily_completion.reduce((sum, item) => sum + item.value, 0),
    [daily_completion]
  );

  const avgDailyCompletion = useMemo(
    () =>
      daily_completion.length > 0
        ? (totalTasks / daily_completion.length).toFixed(1)
        : "0",
    [daily_completion, totalTasks]
  );

  return (
    <div className="bg-slate-900/50 border border-white/10 rounded-lg p-6 backdrop-blur">
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white mb-1">{title}</h3>
        <div className="flex items-baseline gap-4">
          <div>
            <span className="text-2xl font-bold text-blue-400">{totalTasks}</span>
            <span className="text-xs text-slate-400 ml-2">total tasks completed</span>
          </div>
          <div>
            <span className="text-sm font-semibold text-slate-300">{avgDailyCompletion}</span>
            <span className="text-xs text-slate-400 ml-2">avg per day</span>
          </div>
        </div>
      </div>

      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="colorTasks" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="colorUtilization" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="date"
              stroke="rgba(255,255,255,0.3)"
              style={{ fontSize: "12px" }}
            />
            <YAxis
              stroke="rgba(255,255,255,0.3)"
              style={{ fontSize: "12px" }}
              label={{ value: "Count", angle: -90, position: "insideLeft" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                border: "1px solid rgba(255, 255, 255, 0.1)",
                borderRadius: "8px",
              }}
              labelFormatter={(label) => `Date: ${label}`}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="tasks"
              stroke="#3b82f6"
              fillOpacity={1}
              fill="url(#colorTasks)"
              name="Tasks Completed"
            />
            {utilization_trend && utilization_trend.length > 0 && (
              <Area
                type="monotone"
                dataKey="utilization"
                stroke="#10b981"
                fillOpacity={1}
                fill="url(#colorUtilization)"
                name="Avg Utilization %"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
          No timeline data available
        </div>
      )}
    </div>
  );
}
