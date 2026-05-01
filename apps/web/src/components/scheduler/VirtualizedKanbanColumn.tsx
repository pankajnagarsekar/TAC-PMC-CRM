"use client";

import React, { useMemo } from "react";
import type { ScheduleTask } from "@/types/schedule.types";
import { useVirtualizedGrid } from "./useVirtualizedGrid";
import { Eye } from "lucide-react";
import { Button } from "@/components/ui/button";

interface VirtualizedKanbanColumnProps {
    tasks: ScheduleTask[];
    onTaskClick: (taskId: string) => void;
    onOpenModal: (taskId: string) => void;
    onDragStart: (event: React.DragEvent<HTMLElement>, taskId: string) => void;
    selectedTasks: Set<string>;
    readOnly: boolean;
    rowHeight?: number;
}

export function VirtualizedKanbanColumn({
    tasks,
    onTaskClick,
    onOpenModal,
    onDragStart,
    selectedTasks,
    readOnly,
    rowHeight = 110, // Approximate height of a Kanban card
}: VirtualizedKanbanColumnProps) {
    const { viewportRef, onScroll, startIndex, endIndex, topSpacer, bottomSpacer } = useVirtualizedGrid({
        itemCount: tasks.length,
        rowHeight: rowHeight,
    });

    const visibleTasks = useMemo(() => tasks.slice(startIndex, endIndex), [tasks, startIndex, endIndex]);

    return (
        <div
            ref={viewportRef}
            onScroll={onScroll}
            className="space-y-4 overflow-y-auto px-1 custom-scrollbar pb-10 transition-all duration-300 relative"
            style={{
                height: 'calc(100vh - 320px)',
                minHeight: '400px',
                contain: 'layout style'
            }}
        >
            <div style={{ height: topSpacer }} />
            {visibleTasks.map((task) => {
                const isSelected = selectedTasks.has(task.task_id);

                return (
                    <article
                        key={task.task_id}
                        draggable={!readOnly}
                        onDragStart={(event) => onDragStart(event, task.task_id)}
                        onClick={() => onTaskClick(task.task_id)}
                        className={`cursor-pointer rounded-2xl border px-3 py-3 transition hover:border-slate-300 dark:hover:border-white/20 active:scale-[0.98] ${isSelected
                            ? "border-sky-400/40 bg-sky-500/10 dark:bg-sky-500/15 ring-2 ring-sky-500/20"
                            : "border-slate-200 dark:border-white/5 bg-white dark:bg-white/[0.03]"
                            }`}
                        style={{ height: rowHeight - 16, marginBottom: 16 }} // Ensure consistent height for virtualization
                    >
                        <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                                <p className="truncate text-xs font-semibold text-slate-900 dark:text-white" title={task.task_name}>{task.task_name}</p>
                                <p className="mt-1 text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-white/45">
                                    {task.wbs_code || task.task_id}
                                </p>
                            </div>
                            <div className="flex items-center gap-1">
                                <Button
                                    type="button"
                                    variant="ghost"
                                    size="icon"
                                    className="h-7 w-7 rounded-lg text-slate-400 hover:text-sky-500 hover:bg-sky-500/10"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        onOpenModal(task.task_id);
                                    }}
                                    title="View details"
                                >
                                    <Eye size={12} />
                                </Button>
                                <span className="rounded-full border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-white/5 px-2 py-1 text-[10px] font-black uppercase text-slate-600 dark:text-white/70">
                                    {task.percent_complete ?? 0}%
                                </span>
                            </div>
                        </div>
                        <div className="mt-3 flex flex-col gap-2">
                            <div className="h-1.5 w-full rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                                <div
                                    className="h-full bg-sky-500 dark:bg-sky-400 transition-all duration-300"
                                    style={{ width: `${task.percent_complete ?? 0}%` }}
                                />
                            </div>
                            <div className="flex items-center justify-between gap-2 text-[10px] uppercase tracking-[0.16em] text-slate-500 dark:text-white/50">
                                <span>{task.task_mode ?? "Auto"}</span>
                                <span>{task.scheduled_duration ?? 0}d</span>
                            </div>
                        </div>
                    </article>
                );
            })}
            <div style={{ height: Math.max(0, bottomSpacer) }} />
        </div>
    );
}
