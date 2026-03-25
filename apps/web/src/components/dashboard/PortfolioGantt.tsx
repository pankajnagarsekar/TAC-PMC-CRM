"use client";

import React, { useMemo } from "react";
import { format, parseISO, startOfMonth, addMonths, differenceInDays } from "date-fns";
import { Timer, LayoutDashboard } from "lucide-react";

interface Milestone {
    task_id: string;
    project_id: string;
    project_name: string;
    task_name: string;
    finish_date: string;
    is_critical: boolean;
}

export default function PortfolioGantt({ milestones }: { milestones: Milestone[] }) {
    // 1. Calculate Timeline Range (6 months)
    const start = startOfMonth(new Date());
    const months = useMemo(() => {
        return Array.from({ length: 6 }).map((_, i) => addMonths(start, i));
    }, [start]);

    const totalDays = useMemo(() => {
        const lastMonth = months[months.length - 1];
        const nextMonth = addMonths(lastMonth, 1);
        return differenceInDays(nextMonth, start);
    }, [months, start]);

    const getPosition = (dateStr: string) => {
        const date = parseISO(dateStr);
        const daysFromStart = differenceInDays(date, start);
        return (daysFromStart / totalDays) * 100;
    };

    // 2. Group by Project
    const projects = useMemo(() => {
        const groups: Record<string, { name: string; milestones: Milestone[] }> = {};
        milestones.forEach(m => {
            if (!groups[m.project_id]) {
                groups[m.project_id] = { name: m.project_name, milestones: [] };
            }
            groups[m.project_id].milestones.push(m);
        });
        return Object.values(groups);
    }, [milestones]);

    return (
        <div className="bg-slate-950 border border-white/5 rounded-[28px] p-8 shadow-2xl overflow-hidden">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h3 className="text-sm font-black uppercase tracking-[0.2em] text-white/45 flex items-center gap-2">
                        <LayoutDashboard className="w-4 h-4" /> Cross-Project Timeline
                    </h3>
                    <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
                        Executive view of upcoming milestones across the portfolio
                    </p>
                </div>
            </div>

            <div className="relative">
                {/* Timeline Header */}
                <div className="flex border-b border-white/5 mb-6">
                    <div className="w-48 shrink-0 py-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                        Project / Streams
                    </div>
                    <div className="flex-1 flex">
                        {months.map(m => (
                            <div key={m.toISOString()} className="flex-1 py-2 text-center text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 border-l border-white/5">
                                {format(m, "MMM yyyy")}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Project Rows */}
                <div className="space-y-4">
                    {projects.map((p, idx) => (
                        <div key={idx} className="flex items-center group">
                            <div className="w-48 shrink-0">
                                <p className="text-xs font-bold text-white group-hover:text-sky-400 transition-colors truncate pr-4">
                                    {p.name}
                                </p>
                                <p className="text-[9px] text-slate-600 font-mono">
                                    {p.milestones.length} milestones
                                </p>
                            </div>
                            <div className="flex-1 relative h-12 bg-white/[0.02] rounded-xl border border-white/5 overflow-hidden">
                                {/* Grid Lines */}
                                <div className="absolute inset-0 flex">
                                    {months.map(m => (
                                        <div key={m.toISOString()} className="flex-1 border-l border-white/5 h-full" />
                                    ))}
                                </div>

                                {/* Milestones */}
                                {p.milestones.map((m, mi) => {
                                    const pos = getPosition(m.finish_date);
                                    if (pos < 0 || pos > 100) return null;

                                    return (
                                        <div
                                            key={mi}
                                            className="absolute top-1/2 -translate-y-1/2 group/m"
                                            style={{ left: `${pos}%` }}
                                        >
                                            <div
                                                className={`w-3 h-3 rotate-45 border-2 shadow-lg transition-all duration-300 group-hover/m:scale-125 ${m.is_critical ? "bg-rose-500 border-rose-400 shadow-rose-500/20" : "bg-sky-500 border-sky-400 shadow-sky-500/20"}`}
                                                title={`${m.task_name} (${m.finish_date})`}
                                            />

                                            {/* Tooltip-like label */}
                                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 opacity-0 group-hover/m:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                                                <div className="bg-slate-900 border border-white/10 px-2 py-1 rounded text-[9px] font-bold text-white shadow-2xl">
                                                    {m.task_name}
                                                    <span className="ml-2 text-slate-400">{m.finish_date}</span>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    ))}
                </div>

                {/* Legend */}
                <div className="mt-8 flex items-center justify-end gap-6 border-t border-white/5 pt-4">
                    <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rotate-45 bg-rose-500 border border-rose-400" />
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-500 text-rose-400">Critical Milestone</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rotate-45 bg-sky-500 border border-sky-400" />
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-500">Standard Milestone</span>
                    </div>
                </div>
            </div>
        </div>
    );
};
