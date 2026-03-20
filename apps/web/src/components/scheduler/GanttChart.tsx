"use client";

import React, { useMemo } from "react";
import { format, parse, differenceInDays, addDays, startOfMonth, endOfMonth, eachMonthOfInterval, isSameMonth } from "date-fns";
import { Info } from "lucide-react";

interface GanttChartProps {
    tasks: any[];
}

export default function GanttChart({ tasks }: GanttChartProps) {
    // 1. Determine timeline range
    const { minDate, maxDate } = useMemo(() => {
        if (tasks.length === 0) return { minDate: new Date(), maxDate: addDays(new Date(), 30) };

        const dates = tasks.flatMap(t => {
            try {
                return [
                    parse(t.start, "dd-MM-yy", new Date()),
                    parse(t.finish, "dd-MM-yy", new Date())
                ];
            } catch (e) {
                return [];
            }
        });

        if (dates.length === 0) return { minDate: new Date(), maxDate: addDays(new Date(), 30) };

        return {
            minDate: startOfMonth(new Date(Math.min(...dates.map(d => d.getTime())))),
            maxDate: endOfMonth(new Date(Math.max(...dates.map(d => d.getTime()))))
        };
    }, [tasks]);

    const months = useMemo(() => {
        return eachMonthOfInterval({ start: minDate, end: maxDate });
    }, [minDate, maxDate]);

    const totalDays = differenceInDays(maxDate, minDate) + 1;
    const dayWidth = 20; // px
    const chartWidth = totalDays * dayWidth;
    const rowHeight = 40;
    const headerHeight = 60;

    return (
        <div className="glass-panel-luxury border border-white/5 rounded-2xl overflow-hidden shadow-2xl bg-slate-900/50">
            <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Timeline Visualization</h3>
                <div className="flex gap-4 text-[10px] uppercase tracking-wider font-bold">
                    <div className="flex items-center gap-1.5 text-orange-500">
                        <div className="w-2 h-2 rounded bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.5)]" />
                        Standard Task
                    </div>
                    <div className="flex items-center gap-1.5 text-red-500">
                        <div className="w-2 h-2 rounded bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                        Critical Path
                    </div>
                </div>
            </div>

            <div className="overflow-x-auto custom-scrollbar bg-slate-950/20">
                {tasks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
                        <Info size={24} className="opacity-20" />
                        <p className="text-xs font-medium uppercase tracking-widest opacity-40">No tasks to visualize in Gantt</p>
                    </div>
                ) : (
                    <div style={{ width: chartWidth, minHeight: tasks.length * rowHeight + headerHeight }} className="relative">
                        {/* Header */}
                        <svg width={chartWidth} height={headerHeight} className="sticky top-0 z-20 bg-slate-950 border-b border-white/10">
                            {months.map((month, idx) => {
                                const monthStart = startOfMonth(month);
                                const xStart = differenceInDays(monthStart > minDate ? monthStart : minDate, minDate) * dayWidth;
                                const daysInMonth = differenceInDays(endOfMonth(month), monthStart) + 1;
                                return (
                                    <g key={idx}>
                                        <line x1={xStart} y1={0} x2={xStart} y2={headerHeight} stroke="rgba(255,255,255,0.05)" />
                                        <text
                                            x={xStart + 10}
                                            y={30}
                                            className="fill-slate-400 text-[10px] font-bold uppercase tracking-widest"
                                        >
                                            {format(month, "MMMM yyyy")}
                                        </text>
                                    </g>
                                );
                            })}
                        </svg>

                        {/* Task Grid & Bars */}
                        <div className="relative pt-2 pb-8">
                            {tasks.map((task, idx) => {
                                let start, finish;
                                try {
                                    start = parse(task.start, "dd-MM-yy", new Date());
                                    finish = parse(task.finish, "dd-MM-yy", new Date());
                                } catch (e) {
                                    return null;
                                }

                                const left = differenceInDays(start, minDate) * dayWidth;
                                const width = Math.max((differenceInDays(finish, start) + 1) * dayWidth, 10);
                                const top = idx * rowHeight;

                                return (
                                    <div
                                        key={task.id}
                                        className="group"
                                        style={{
                                            position: "absolute",
                                            left,
                                            top,
                                            width,
                                            height: rowHeight - 10,
                                        }}
                                    >
                                        {/* Task Bar */}
                                        <div
                                            className={`h-full rounded-md shadow-lg transition-all duration-300 relative overflow-hidden flex items-center px-2 cursor-pointer
                      ${task.is_critical
                                                    ? 'bg-gradient-to-r from-red-600 to-red-400 border border-red-400/50 shadow-red-900/20'
                                                    : 'bg-gradient-to-r from-orange-600 to-amber-500 border border-orange-400/50 shadow-orange-900/20'}
                      hover:scale-[1.02] hover:z-20 hover:brightness-110`}
                                        >
                                            <span className="text-[9px] font-bold text-white truncate drop-shadow-sm uppercase tracking-tighter">
                                                {task.name}
                                            </span>

                                            {/* Glass sheen */}
                                            <div className="absolute inset-0 bg-gradient-to-tr from-white/10 to-transparent pointer-events-none" />
                                        </div>

                                        {/* Dependencies/Connectors could go here in future */}
                                    </div>
                                );
                            })}

                            {/* Background Grid Lines */}
                            <svg width={chartWidth} height={tasks.length * rowHeight} className="absolute inset-0 pointer-events-none opacity-20">
                                {months.map((month, idx) => {
                                    const x = differenceInDays(startOfMonth(month), minDate) * dayWidth;
                                    return <line key={idx} x1={x} y1={0} x2={x} y2="100%" stroke="white" strokeWidth="0.5" strokeDasharray="4 4" />;
                                })}
                            </svg>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
