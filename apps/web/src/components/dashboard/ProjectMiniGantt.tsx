"use client";

import React, { useMemo } from "react";
import { format, startOfMonth, addMonths, differenceInDays } from "date-fns";
import { GanttChartSquare } from "lucide-react";
import { ScheduleTask } from "@/types/schedule.types";
import { parseTaskDate } from "@/components/scheduler/scheduler-utils";

interface ProjectMiniGanttProps {
    tasks: ScheduleTask[];
}

export default function ProjectMiniGantt({ tasks }: ProjectMiniGanttProps) {
    // 1. Calculate Timeline Range (Next 6 months starting from current month)
    const start = startOfMonth(new Date());
    const months = useMemo(() => {
        return Array.from({ length: 6 }).map((_, i) => addMonths(start, i));
    }, [start]);

    const end = addMonths(start, 6);

    const totalDays = useMemo(() => {
        return differenceInDays(end, start);
    }, [start, end]);

    const getPosition = (date: Date) => {
        const daysFromStart = differenceInDays(date, start);
        return (daysFromStart / totalDays) * 100;
    };

    // 2. Filter and sort tasks that fall within this range
    const visibleTasks = useMemo(() => {
        return tasks
            .filter(t => {
                const s = parseTaskDate(t.scheduled_start);
                const f = parseTaskDate(t.scheduled_finish);
                if (!s || !f) return false;
                // Show if it overlaps with [start, end]
                return s < end && f > start;
            })
            .sort((a, b) => {
                const da = parseTaskDate(a.scheduled_start)?.getTime() || 0;
                const db = parseTaskDate(b.scheduled_start)?.getTime() || 0;
                return da - db;
            })
            .slice(0, 30); // Support taller view with more tasks
    }, [tasks, start, end]);

    return (
        <div className="bg-transparent h-full flex flex-col font-sans select-none">
            <div className="flex items-center justify-between mb-6 shrink-0">
                <div>
                    <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400 flex items-center gap-2">
                        <GanttChartSquare className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" /> Project Schedule & Gantt
                    </h3>
                </div>
            </div>

            <div className="relative flex-1 flex flex-col min-h-0">
                {/* Timeline Header */}
                <div className="flex border-b border-slate-200 dark:border-white/5 mb-4 shrink-0">
                    <div className="w-32 shrink-0 py-1.5 text-[8px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400">
                        Task Stream
                    </div>
                    <div className="flex-1 flex">
                        {months.map(m => (
                            <div key={m.toISOString()} className="flex-1 py-1.5 text-center text-[8px] font-black uppercase tracking-[0.2em] text-slate-500 dark:text-slate-400 border-l border-slate-200 dark:border-white/5">
                                {format(m, "MMM")}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Task Rows */}
                <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                    {visibleTasks.map((t) => {
                        const startDate = parseTaskDate(t.scheduled_start)!;
                        const finishDate = parseTaskDate(t.scheduled_finish)!;

                        const left = Math.max(0, getPosition(startDate));
                        const right = Math.min(100, getPosition(finishDate));
                        const width = Math.max(1, right - left);

                        const progress = Number(t.percent_complete ?? 0);

                        return (
                            <div key={t.task_id} className="flex items-center group/row h-8">
                                <div className="w-32 shrink-0 pr-4">
                                    <p className="text-[9px] font-bold text-slate-700 dark:text-white/40 group-hover/row:text-indigo-600 dark:group-hover/row:text-primary transition-colors truncate" title={t.task_name}>
                                        {t.task_name}
                                    </p>
                                </div>
                                <div className="flex-1 relative h-2 bg-slate-200/50 dark:bg-white/[0.03] rounded-full overflow-hidden">
                                    {/* Bar */}
                                    <div
                                        className={`absolute h-full rounded-full transition-all duration-500 ${t.is_critical ? 'bg-indigo-600 dark:bg-indigo-500 shadow-[0_0_10px_rgba(99,102,241,0.3)]' : 'bg-slate-300 dark:bg-slate-700'
                                            }`}
                                        style={{ left: `${left}%`, width: `${width}%` }}
                                    >
                                        {/* Progress Overlay */}
                                        <div
                                            className="h-full bg-white/40 dark:bg-white/20 rounded-full"
                                            style={{ width: `${progress}%` }}
                                        />
                                    </div>
                                </div>
                            </div>
                        );
                    })}

                    {visibleTasks.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-32 opacity-20">
                            <GanttChartSquare size={32} className="mb-2 text-slate-400 dark:text-white" />
                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 dark:text-white">No active tasks in range</p>
                        </div>
                    )}
                </div>

                {/* Legend */}
                <div className="mt-4 flex items-center justify-end gap-4 border-t border-slate-200 dark:border-white/5 pt-3 shrink-0">
                    <div className="flex items-center gap-1.5">
                        <div className="w-2 h-2 rounded-full bg-indigo-600 dark:bg-indigo-500" />
                        <span className="text-[8px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">Critical Path</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <div className="w-2 h-2 rounded-full bg-slate-400 dark:bg-slate-700" />
                        <span className="text-[8px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">Scheduled</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
