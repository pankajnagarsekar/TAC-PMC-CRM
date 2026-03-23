"use client";

import React, { useMemo } from "react";
import { Gantt, Task, ViewMode } from "gantt-task-react";
import { parse, format } from "date-fns";
import "gantt-task-react/dist/index.css";

interface GanttChartProps {
    tasks: any[];
}

export default function GanttChart({ tasks }: GanttChartProps) {
    // Transform our task format to gantt-task-react format
    const ganttTasks: Task[] = useMemo(() => {
        if (!tasks || tasks.length === 0) {
            return [];
        }

        return tasks
            .filter(t => t.start && t.finish) // Only include tasks with dates
            .map(t => {
                try {
                    // Parse DD-MM-YY format
                    const startDate = parse(t.start, "dd-MM-yy", new Date());
                    const endDate = parse(t.finish, "dd-MM-yy", new Date());

                    // Determine task type
                    let type: "task" | "milestone" | "project" = "task";
                    if (t.isMilestone || t.duration === 0) {
                        type = "milestone";
                    }

                    // Base task object
                    const ganttTask: Task = {
                        id: t.id,
                        name: t.name,
                        start: startDate,
                        end: endDate,
                        progress: t.percentComplete || 0,
                        type: type,
                        dependencies: t.predecessors || [],
                        // Custom styling based on critical path
                        styles: {
                            backgroundColor: t.is_critical ? "#CC0000" : "#4472C4",
                            backgroundSelectedColor: t.is_critical ? "#A00000" : "#2E5BA3",
                            progressColor: t.is_critical ? "#990000" : "#2E5BA3",
                            progressSelectedColor: t.is_critical ? "#700000" : "#1A3A6B"
                        }
                    };

                    return ganttTask;
                } catch (e) {
                    // Skip tasks with invalid dates
                    return null;
                }
            })
            .filter((t): t is Task => t !== null);
    }, [tasks]);

    const handleTaskChange = (task: Task) => {
        // This would require syncing back to parent state if editing is enabled
        // For now, the chart is read-only (editing via the SchedulerGrid)
        console.log("Task changed:", task);
    };

    const handleTaskDelete = (task: Task) => {
        // Delete functionality would be in the SchedulerGrid
        console.log("Task deleted:", task);
    };

    const handleProgressChange = (task: Task) => {
        // Progress changes would sync back to parent
        console.log("Progress changed:", task);
    };

    const handleDblClick = (task: Task) => {
        // Double-click handler
        console.log("Task double-clicked:", task);
    };

    return (
        <div className="glass-panel-luxury border border-white/5 rounded-2xl overflow-hidden shadow-2xl bg-slate-900/50 w-full">
            <div className="p-4 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                <h3 className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">Gantt Timeline (MS Project Style)</h3>
                <div className="flex gap-4 text-[10px] uppercase tracking-wider font-bold">
                    <div className="flex items-center gap-1.5 text-blue-500">
                        <div className="w-2 h-2 rounded bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                        Standard Task
                    </div>
                    <div className="flex items-center gap-1.5 text-red-500">
                        <div className="w-2 h-2 rounded bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                        Critical Path
                    </div>
                    <div className="flex items-center gap-1.5 text-amber-500">
                        <div className="w-2 h-2 rotate-45 bg-amber-500 shadow-[0_0_8px_rgba(217,119,6,0.5)]" />
                        Milestone
                    </div>
                </div>
            </div>

            <div className="overflow-x-auto custom-scrollbar bg-slate-950/20 p-4 rounded-b-2xl">
                {ganttTasks.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-slate-500 gap-2">
                        <div className="text-3xl opacity-20">📊</div>
                        <p className="text-xs font-medium uppercase tracking-widest opacity-40">
                            No tasks to visualize — Calculate CPM or import a schedule
                        </p>
                    </div>
                ) : (
                    <div style={{ width: "100%", minHeight: "400px" }}>
                        <Gantt
                            tasks={ganttTasks}
                            onTaskChange={handleTaskChange}
                            onTaskDelete={handleTaskDelete}
                            onProgressChange={handleProgressChange}
                            onDoubleClick={handleDblClick}
                            viewMode={ViewMode.Month}
                            listCellWidth="200px"
                            barCornerRadius={4}
                            fontFamily='ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, sans-serif'
                            fontSize="12px"
                            locale="en-US"
                        />
                    </div>
                )}
            </div>

            {/* Legend and notes */}
            <div className="p-4 border-t border-white/5 bg-white/[0.01] rounded-b-2xl">
                <p className="text-[10px] text-slate-500 uppercase tracking-widest font-medium">
                    💡 Tip: Edit tasks in the grid above. Gantt chart updates automatically. Dependency arrows show predecessor relationships. Progress bars reflect % complete.
                </p>
            </div>
        </div>
    );
}
