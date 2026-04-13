"use client";

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { GlassCard } from "@/components/ui/GlassCard";

interface ScheduleHealthChartProps {
  daysRemaining: number;
  tasksAtRisk: number;
  criticalPathDays: number;
}

export const ScheduleHealthChart: React.FC<ScheduleHealthChartProps> = ({
  daysRemaining,
  tasksAtRisk,
  criticalPathDays,
}) => {
  const data = [
    {
      name: "Schedule Health",
      "Days Remaining": daysRemaining,
      "Tasks at Risk": tasksAtRisk * 5, // Scale for visualization
      "Critical Path": criticalPathDays,
    },
  ];

  return (
    <GlassCard className="p-6">
      <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-4">
        Schedule Health
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--color-slate-200)"
            vertical={false}
          />
          <XAxis
            dataKey="name"
            tick={{ fill: "var(--color-slate-600)", fontSize: 12 }}
          />
          <YAxis tick={{ fill: "var(--color-slate-600)", fontSize: 12 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--color-slate-900)",
              border: "1px solid var(--color-slate-700)",
              borderRadius: "0.5rem",
            }}
            labelStyle={{ color: "var(--color-slate-100)" }}
          />
          <Legend wrapperStyle={{ paddingTop: "20px" }} />
          <Bar dataKey="Days Remaining" fill="#10b981" />
          <Bar dataKey="Tasks at Risk" fill="#f59e0b" />
          <Bar dataKey="Critical Path" fill="#3b82f6" />
        </BarChart>
      </ResponsiveContainer>
      <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
        <div className="p-2 bg-emerald-500/10 rounded">
          <p className="text-slate-600 dark:text-slate-400">Days Remaining</p>
          <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
            {daysRemaining}
          </p>
        </div>
        <div className="p-2 bg-amber-500/10 rounded">
          <p className="text-slate-600 dark:text-slate-400">At Risk</p>
          <p className="text-lg font-bold text-amber-600 dark:text-amber-400">
            {tasksAtRisk}
          </p>
        </div>
        <div className="p-2 bg-blue-500/10 rounded">
          <p className="text-slate-600 dark:text-slate-400">Critical Path</p>
          <p className="text-lg font-bold text-blue-600 dark:text-blue-400">
            {criticalPathDays}d
          </p>
        </div>
      </div>
    </GlassCard>
  );
};
