"use client";

import React, { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { format } from "date-fns";

import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";

export default function CashFlowChart() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const data = useMemo(() => {
    const buckets = new Map<string, number>();

    tasks.forEach((task) => {
      const finish = parseTaskDate(task.scheduled_finish || task.baseline_finish);
      if (!finish) return;
      const key = format(finish, "MMM yy");
      buckets.set(key, (buckets.get(key) ?? 0) + Number(task.wo_value ?? 0));
    });

    return Array.from(buckets.entries()).map(([name, value]) => ({ name, value }));
  }, [tasks]);

  return (
    <div className="rounded-[24px] border border-white/5 bg-slate-950/60 p-5 shadow-2xl">
      <div className="mb-4">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">Cash Flow</h3>
        <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
          Work-order value by finishing month
        </p>
      </div>
      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#f97316" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
