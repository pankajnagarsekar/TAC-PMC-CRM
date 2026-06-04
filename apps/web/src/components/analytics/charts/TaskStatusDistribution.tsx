"use client";

import React, { useMemo, useRef } from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { ScheduleTask, ScheduleTaskStatus } from "@/types/schedule.types";
import { useAnalyticsStore } from "@/store/useAnalyticsStore";
import { useScheduleStore } from "@/store/useScheduleStore";
import { computeTaskStatusDistribution } from "@/lib/analyticsComputeEngine";
import { useRouter, useSearchParams } from "next/navigation";
import AnalyticsExportBar from "../AnalyticsExportBar";

interface TaskStatusDistributionProps {
  tasks: ScheduleTask[];
}

export default function TaskStatusDistribution({ tasks }: TaskStatusDistributionProps) {
  const filters = useAnalyticsStore((state) => state.filters);
  const setStatusFilter = useScheduleStore((state) => state.setStatusFilter);
  const router = useRouter();
  const searchParams = useSearchParams();
  const chartRef = useRef<HTMLDivElement>(null);

  const data = useMemo(() => {
    return computeTaskStatusDistribution(tasks, filters);
  }, [tasks, filters]);

  const chartData = useMemo(() => {
    return data.filter((d) => d.value > 0);
  }, [data]);

  const totalCount = useMemo(() => {
    return data.reduce((sum, item) => sum + item.value, 0);
  }, [data]);

  const handleSegmentClick = (name: string) => {
    // Map custom display name back to ScheduleTaskStatus
    let targetStatus: ScheduleTaskStatus[] = [];
    if (name === "Completed") {
      targetStatus = ["completed", "closed"];
    } else if (name === "In Progress") {
      targetStatus = ["in_progress"];
    } else if (name === "Not Started") {
      targetStatus = ["not_started", "draft"];
    } else if (name === "On Hold") {
      targetStatus = ["on_hold" as ScheduleTaskStatus];
    } else if (name === "Cancelled") {
      targetStatus = ["cancelled" as ScheduleTaskStatus];
    } else {
      targetStatus = [];
    }

    setStatusFilter(targetStatus);
    
    // Switch tab to grid in the URL
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", "grid");
    router.replace(`?${params.toString()}`);
  };

  return (
    <div ref={chartRef} className="space-y-6 h-full w-full relative">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-white/45">Task Status Distribution</h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Breakdown of current task execution statuses (Click to drill down into Grid)
          </p>
        </div>
        {totalCount > 0 && (
          <AnalyticsExportBar
            chartRef={chartRef}
            chartData={data}
            columns={["name", "value"]}
            title="Task Status Distribution"
            fileName="Task_Status_Distribution"
          />
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
        {/* Donut Chart */}
        <div className="h-[260px] relative flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%" debounce={100}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={65}
                outerRadius={90}
                paddingAngle={4}
                dataKey="value"
                cursor="pointer"
              >
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={entry.color} 
                    onClick={() => handleSegmentClick(entry.name)}
                    className="hover:opacity-85 transition-opacity"
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "rgba(15, 23, 42, 0.9)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: "12px",
                  fontSize: "12px",
                  color: "#fff",
                  boxShadow: "0 20px 25px -5px rgb(0 0 0 / 0.1)"
                }}
                formatter={(value: any, name: any) => [Number(value || 0), name]}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="absolute flex flex-col items-center justify-center">
            <span className="text-3xl font-black text-slate-900 dark:text-white tracking-tight">{totalCount}</span>
            <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest mt-1">Total Tasks</span>
          </div>
        </div>

        {/* Legend / Status Cards */}
        <div className="space-y-2">
          {data.map((item) => {
            const percentage = totalCount > 0 ? Math.round((item.value / totalCount) * 100) : 0;
            return (
              <button
                key={item.name}
                onClick={() => handleSegmentClick(item.name)}
                className="w-full flex items-center justify-between p-3 rounded-xl border border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/[0.01] hover:bg-slate-100/50 dark:hover:bg-white/5 transition-all text-left group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  <div>
                    <span className="text-[10px] font-black uppercase tracking-wider text-slate-700 dark:text-slate-200">
                      {item.name}
                    </span>
                    <span className="text-[8px] font-bold text-slate-400 dark:text-white/20 ml-2">
                      ({item.value} tasks)
                    </span>
                  </div>
                </div>
                <span className="text-xs font-black text-slate-900 dark:text-white group-hover:text-orange-500 transition-colors">
                  {percentage}%
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
