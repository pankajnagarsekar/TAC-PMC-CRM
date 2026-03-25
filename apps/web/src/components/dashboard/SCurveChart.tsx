"use client";

import React, { useMemo } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend } from "recharts";
import { format } from "date-fns";

import { useScheduleStore } from "@/store/useScheduleStore";
import { normalizeTaskOrder, parseTaskDate } from "@/components/scheduler/scheduler-utils";

function getMonthKey(date: Date) {
  return format(date, "yyyy-MM");
}

export default function SCurveChart() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const tasks = useMemo(() => normalizeTaskOrder(taskMap, taskOrder), [taskMap, taskOrder]);

  const data = useMemo(() => {
    const buckets = new Map<string, { key: string; name: string; PV: number; EV: number }>();

    tasks.forEach((task) => {
      const finish = parseTaskDate(task.baseline_finish || task.scheduled_finish);
      const baselineCost = Number(task.baseline_cost ?? 0);
      const ev = (Number(task.percent_complete ?? 0) / 100) * baselineCost;
      if (!finish) return;

      const key = getMonthKey(finish);
      const current = buckets.get(key) ?? {
        key,
        name: format(finish, "MMM yy"),
        PV: 0,
        EV: 0,
      };

      current.PV += baselineCost;
      current.EV += ev;
      buckets.set(key, current);
    });

    return Array.from(buckets.values()).sort((a, b) => a.key.localeCompare(b.key));
  }, [tasks]);

  return (
    <div className="rounded-[24px] border border-white/5 bg-slate-950/60 p-5 shadow-2xl">
      <div className="mb-4">
        <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">S-Curve</h3>
        <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
          Planned vs earned value from the live schedule store
        </p>
      </div>
      <div className="h-[320px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="PV" stroke="#f59e0b" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="EV" stroke="#38bdf8" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
