"use client";

import React, { useMemo, useRef } from "react";
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
import { ScheduleTask } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { computeResourceLoad } from "@/lib/analyticsComputeEngine";
import AnalyticsEmptyState from "../AnalyticsEmptyState";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface ResourceLoadChartProps {
  tasks: ScheduleTask[];
}

export default function ResourceLoadChart({ tasks }: ResourceLoadChartProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const chartRef = useRef<HTMLDivElement>(null);

  const data = useMemo(() => {
    return computeResourceLoad(tasks, filters);
  }, [tasks, filters]);

  const hasAssignees = useMemo(() => {
    return data.some((d) => d.name !== "Unassigned");
  }, [data]);

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full relative">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Resource Workload</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Work volume in days allocated per project resource (Planned vs Completed vs Overdue)
          </p>
        </div>
        {hasAssignees && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={data}
            columns={["name", "planned", "completed", "overdue"]}
            title="Resource Workload"
            fileName="Resource_Workload"
          />
        )}
      </div>

      <div className="h-[340px] w-full min-w-0">
        {hasAssignees ? (
          <ResponsiveContainer width="100%" height="100%" debounce={100}>
            <BarChart
              data={data}
              layout="vertical"
              margin={{ top: 10, right: 30, left: 40, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-white/[0.03]" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fill: "#64748b", fontSize: 9 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                dataKey="name"
                type="category"
                tick={{ fill: "#64748b", fontSize: 9, fontWeight: 600 }}
                axisLine={false}
                tickLine={false}
                width={80}
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
                formatter={(value: any, name: any) => [`${Number(value || 0)} Days`, name]}
              />
              <Legend
                verticalAlign="top"
                height={36}
                content={({ payload }) => (
                  <div className="flex justify-end gap-4 text-[9px] font-black uppercase tracking-wider text-slate-500">
                    {payload?.map((entry: any) => (
                      <div key={entry.value} className="flex items-center gap-1.5">
                        <div className="h-1.5 w-3 rounded-full" style={{ backgroundColor: entry.color }} />
                        <span>{entry.value}</span>
                      </div>
                    ))}
                  </div>
                )}
              />
              <Bar dataKey="planned" name="Planned Duration" fill="#64748b" radius={[0, 4, 4, 0]} maxBarSize={20} />
              <Bar dataKey="completed" name="Completed Duration" fill="#10b981" radius={[0, 4, 4, 0]} maxBarSize={20} />
              <Bar dataKey="overdue" name="Overdue Duration" fill="#ef4444" radius={[0, 4, 4, 0]} maxBarSize={20} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="py-8">
            <AnalyticsEmptyState
              title="No Assignees Found"
              description="No assignees found. Assign tasks to team members in the Grid view to enable workload analysis."
              actionText="Go to Grid View"
              actionTab="grid"
            />
          </div>
        )}
      </div>
    </div>
  );
}
