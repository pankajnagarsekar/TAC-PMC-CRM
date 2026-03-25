"use client";

import React, { useMemo } from "react";

import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder } from "@/components/scheduler/scheduler-utils";

export default function ResourceHeatmap() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const data = useMemo(() => {
    const resourceIds = new Set<string>();
    const weekBuckets = new Map<string, Map<string, number>>();

    tasks.forEach((task) => {
      (task.assigned_resources ?? []).forEach((resourceId) => {
        resourceIds.add(resourceId);
        const week = task.scheduled_start ?? "unplanned";
        const row = weekBuckets.get(week) ?? new Map<string, number>();
        row.set(resourceId, (row.get(resourceId) ?? 0) + 1);
        weekBuckets.set(week, row);
      });
    });

    return {
      resourceIds: Array.from(resourceIds),
      weekBuckets: Array.from(weekBuckets.entries()),
    };
  }, [tasks]);

  return (
    <div className="rounded-[24px] border border-white/5 bg-slate-950/60 p-5 shadow-2xl">
      <div className="mb-4">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">Resource Heatmap</h3>
        <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
          Assignment density by resource and task start bucket
        </p>
      </div>

      {data.resourceIds.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-white/10 px-4 py-8 text-center text-xs text-slate-500">
          No resource assignments in the current schedule.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <div className="min-w-[480px] space-y-2">
            {data.weekBuckets.map(([week, counts]) => (
              <div key={week} className="grid grid-cols-[160px_repeat(auto-fit,minmax(70px,1fr))] gap-2">
                <div className="px-2 py-3 text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">
                  {week}
                </div>
                {data.resourceIds.map((resourceId) => {
                  const value = counts.get(resourceId) ?? 0;
                  const intensity = Math.min(1, value / 4);
                  return (
                    <div
                      key={`${week}-${resourceId}`}
                      className="rounded-xl border border-white/5 px-2 py-3 text-center text-[10px] font-black text-white"
                      style={{
                        backgroundColor: `rgba(249, 115, 22, ${0.08 + intensity * 0.35})`,
                      }}
                      title={`${resourceId}: ${value}`}
                    >
                      {value || "0"}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
