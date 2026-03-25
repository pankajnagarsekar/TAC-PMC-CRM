"use client";

import React, { memo, useEffect, useMemo, useRef, useState } from "react";
import { GripVertical, MoveHorizontal, Pencil } from "lucide-react";
import { toast } from "sonner";
import { addDays, format } from "date-fns";

import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTask } from "@/types/schedule.types";
import {
  buildCalendarColumns,
  calculateTimelineRange,
  getBaselineBarPosition,
  getComparisonBarPosition,
  getTaskBarPosition,
  getTaskDurationDays,
  normalizeTaskOrder,
  parseTaskDate,
  ROW_HEIGHT,
  TIMELINE_DAY_WIDTH,
} from "./scheduler-utils";
import { GanttDependencyOverlay, type GanttDependencyEdge, type GanttDependencyNode } from "./GanttDependencyOverlay";

type DragMode = "move" | "start" | "finish" | null;

type DragState = {
  taskId: string;
  mode: DragMode;
  startX: number;
  originalStart: string | null;
  originalFinish: string | null;
  deltaDays?: number;
} | null;

const Bar = memo(function Bar({
  task,
  left,
  width,
  emphasizeCritical,
  onSelect,
  onStartDrag,
}: {
  task: ScheduleTask;
  left: number;
  width: number;
  emphasizeCritical: boolean;
  onSelect: (taskId: string) => void;
  onStartDrag: (task: ScheduleTask, mode: DragMode, startX: number) => void;
}) {
  const isMilestone = Boolean(task.is_milestone || task.scheduled_duration === 0);
  const barLeft = Math.max(0, left);
  const isCriticalHighlighted = Boolean(emphasizeCritical && task.is_critical);

  const beginDrag = (mode: DragMode) => (event: React.PointerEvent<HTMLButtonElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onStartDrag(task, mode, event.clientX);
  };

  return (
    <div
      className="absolute top-1/2 z-20 -translate-y-1/2"
      style={{ left: barLeft, width }}
      onClick={() => onSelect(task.task_id)}
    >
      <div
        className={`group relative h-8 rounded-xl border px-3 py-1.5 shadow-lg transition-transform duration-150 ${isCriticalHighlighted ? "border-rose-400/40 bg-rose-500/25" : "border-sky-400/30 bg-sky-500/20"} ${isMilestone ? "rounded-full" : ""}`}
      >
        <div className="flex h-full items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-[10px] font-bold uppercase tracking-[0.14em] text-white">
              {task.task_name}
            </p>
            <p className="text-[9px] text-white/50">
              {formatTaskDurationLabel(task)}
            </p>
          </div>
          <div className="flex items-center gap-1 text-white/60">
            <button
              type="button"
              className="rounded-md p-1 hover:bg-white/10"
              onPointerDown={beginDrag("move")}
              title="Move task"
            >
              <MoveHorizontal size={12} />
            </button>
            <button
              type="button"
              className="rounded-md p-1 hover:bg-white/10"
              onPointerDown={beginDrag("start")}
              title="Adjust start"
            >
              <GripVertical size={12} />
            </button>
            <button
              type="button"
              className="rounded-md p-1 hover:bg-white/10"
              onPointerDown={beginDrag("finish")}
              title="Adjust finish"
            >
              <Pencil size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

function formatTaskDurationLabel(task: ScheduleTask) {
  const duration = getTaskDurationDays(task);
  return `${duration} working day${duration === 1 ? "" : "s"}`;
}

export default function GanttChart() {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
  const selectTask = useScheduleStore((state) => state.selectTask);
  const openTask = useScheduleStore((state) => state.openTask);
  const systemState = useScheduleStore((state) => state.systemState);

  // Baseline Comparison Store
  const comparisonData = useScheduleStore((state) => state.comparisonData);
  const selectedBaselineA = useScheduleStore((state) => state.selectedBaselineA);
  const fetchBaselineComparison = useScheduleStore((state) => state.fetchBaselineComparison);
  const clearComparison = useScheduleStore((state) => state.clearComparison);

  const tasks = useMemo(
    () => normalizeTaskOrder(taskMap, taskOrder).filter((task) => task.scheduled_start || task.scheduled_finish),
    [taskMap, taskOrder],
  );

  const comparisonMap = useMemo(() => {
    if (!comparisonData) return new Map<string, any>();
    const map = new Map<string, any>();
    comparisonData.forEach(item => map.set(item.task_id, item));
    return map;
  }, [comparisonData]);

  const readOnly = systemState === "locked";
  const { start: rangeStart, end: rangeEnd } = useMemo(() => calculateTimelineRange(tasks), [tasks]);
  const days = useMemo(() => buildCalendarColumns(rangeStart, rangeEnd), [rangeStart, rangeEnd]);

  const [scrollTop, setScrollTop] = useState(0);
  const [showBaseline, setShowBaseline] = useState(false);
  const [activeBaselineNum, setActiveBaselineNum] = useState<number>(1);

  const handleBaselineToggle = () => {
    if (showBaseline) {
      clearComparison();
      setShowBaseline(false);
    } else {
      if (tasks.length > 0) {
        fetchBaselineComparison(tasks[0].project_id, activeBaselineNum);
      }
      setShowBaseline(true);
    }
  };

  const handleBaselineChange = (num: number) => {
    setActiveBaselineNum(num);
    if (showBaseline && tasks.length > 0) {
      fetchBaselineComparison(tasks[0].project_id, num);
    }
  };

  const [highlightCritical, setHighlightCritical] = useState(true);
  const [previewDeltaDays, setPreviewDeltaDays] = useState(0);
  const [activeDragTaskId, setActiveDragTaskId] = useState<string | null>(null);

  const dragStateRef = useRef<DragState>(null);
  const viewportHeight = 420;
  const visibleCount = Math.ceil(viewportHeight / ROW_HEIGHT) + 6;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 3);
  const endIndex = Math.min(tasks.length, startIndex + visibleCount);
  const visibleTasks = tasks.slice(startIndex, endIndex);
  const topSpacer = startIndex * ROW_HEIGHT;
  const bottomSpacer = Math.max(0, (tasks.length - endIndex) * ROW_HEIGHT);
  const timelineWidth = days.length * TIMELINE_DAY_WIDTH;
  const visibleHeight = visibleTasks.length * ROW_HEIGHT;

  const getPreviewTask = (task: ScheduleTask): ScheduleTask => {
    if (activeDragTaskId !== task.task_id || !dragStateRef.current || previewDeltaDays === 0) {
      return task;
    }

    const { mode } = dragStateRef.current;
    const originalStart = parseTaskDate(task.scheduled_start);
    const originalFinish = parseTaskDate(task.scheduled_finish);
    if (!originalStart || !originalFinish) return task;

    let nextStart = originalStart;
    let nextFinish = originalFinish;

    if (mode === "move") {
      nextStart = addDays(originalStart, previewDeltaDays);
      nextFinish = addDays(originalFinish, previewDeltaDays);
    } else if (mode === "start") {
      nextStart = addDays(originalStart, previewDeltaDays);
      if (nextStart > nextFinish) nextStart = nextFinish;
    } else if (mode === "finish") {
      nextFinish = addDays(originalFinish, previewDeltaDays);
      if (nextFinish < nextStart) nextFinish = nextStart;
    }

    return {
      ...task,
      scheduled_start: format(nextStart, "yyyy-MM-dd"),
      scheduled_finish: format(nextFinish, "yyyy-MM-dd"),
    };
  };

  const dependencyNodes = useMemo(() => {
    const nodes = new Map<string, GanttDependencyNode>();
    visibleTasks.forEach((task, index) => {
      const previewTask = getPreviewTask(task);
      const { left, width } = getTaskBarPosition(previewTask, rangeStart);
      nodes.set(task.task_id, {
        taskId: task.task_id,
        rowIndex: index,
        left,
        width,
      });
    });
    return nodes;
  }, [rangeStart, visibleTasks, activeDragTaskId, previewDeltaDays]);

  const dependencyEdges = useMemo(() => {
    const edges: GanttDependencyEdge[] = [];

    // Performance-first subset: draw only edges where both tasks are currently rendered.
    for (const task of visibleTasks) {
      if (!task.predecessors) continue;
      for (const predecessor of task.predecessors) {
        if (!dependencyNodes.has(predecessor.task_id)) continue;
        edges.push({
          fromTaskId: predecessor.task_id,
          toTaskId: task.task_id,
          type: predecessor.type,
          lagDays: predecessor.lag_days,
          isCritical: Boolean(highlightCritical && task.is_critical && taskMap[predecessor.task_id]?.is_critical),
        });
      }
    }

    return edges;
  }, [dependencyNodes, highlightCritical, taskMap, visibleTasks]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const current = dragStateRef.current;
      if (!current) return;
      const delta = Math.round((event.clientX - current.startX) / TIMELINE_DAY_WIDTH);
      current.deltaDays = delta;
      setPreviewDeltaDays(delta);
    };

    const handlePointerUp = () => {
      const current = dragStateRef.current as DragState & { deltaDays?: number } | null;
      dragStateRef.current = null;
      const taskId = current?.taskId;
      const deltaDays = current?.deltaDays ?? 0;
      const mode = current?.mode;

      setActiveDragTaskId(null);
      setPreviewDeltaDays(0);

      if (taskId && mode && !readOnly) {
        const task = taskMap[taskId];
        if (task) {
          commitDrag(task, mode, deltaDays);
        }
      }
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [readOnly, taskMap]);

  const commitDrag = (task: ScheduleTask, mode: DragMode, deltaDays: number) => {
    if (!mode || readOnly) return;

    const originalStart = parseTaskDate(task.scheduled_start);
    const originalFinish = parseTaskDate(task.scheduled_finish);
    if (!originalStart || !originalFinish) return;

    let nextStart = originalStart;
    let nextFinish = originalFinish;

    if (mode === "move") {
      nextStart = addDays(originalStart, deltaDays);
      nextFinish = addDays(originalFinish, deltaDays);
    } else if (mode === "start") {
      nextStart = addDays(originalStart, deltaDays);
      if (nextStart > nextFinish) {
        nextStart = nextFinish;
      }
    } else if (mode === "finish") {
      nextFinish = addDays(originalFinish, deltaDays);
      if (nextFinish < nextStart) {
        nextFinish = nextStart;
      }
    }

    queueCalculation({
      task_id: task.task_id,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: {
        scheduled_start: format(nextStart, "yyyy-MM-dd"),
        scheduled_finish: format(nextFinish, "yyyy-MM-dd"),
        scheduled_duration: Math.max(0, getTaskDurationDays({
          ...task,
          scheduled_start: format(nextStart, "yyyy-MM-dd"),
          scheduled_finish: format(nextFinish, "yyyy-MM-dd"),
        })),
      },
      trigger_source: "gantt_drag",
    });
  };

  const startDrag = (task: ScheduleTask, mode: DragMode, startX: number) => {
    if (readOnly || !mode) return;
    dragStateRef.current = {
      taskId: task.task_id,
      mode,
      startX,
      originalStart: task.scheduled_start ?? null,
      originalFinish: task.scheduled_finish ?? null,
    };
  };

  const handleSelect = (taskId: string) => {
    selectTask(taskId);
    openTask(taskId);
  };

  const headerLabels = useMemo(
    () => days.map((day) => format(day, "dd MMM")),
    [days],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 px-2">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-white/45">
            Store-Driven Gantt Canvas
          </h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-500">
            Drag bars to update the schedule, then the store debounces the API write
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
          <span className="rounded-full border border-white/5 bg-white/[0.03] px-2 py-1">
            {tasks.length.toLocaleString("en-US")} visible tasks
          </span>
          {selectedTasks.size > 0 && (
            <span className="rounded-full border border-sky-400/20 bg-sky-500/10 px-2 py-1 text-sky-300">
              {selectedTasks.size} selected
            </span>
          )}
          <div className="flex items-center gap-1.5 rounded-full border border-white/5 bg-white/[0.03] p-0.5">
            <button
              type="button"
              className={`rounded-full px-2 py-0.5 transition-colors ${showBaseline ? "bg-white/[0.08] text-white" : "text-slate-400 hover:text-slate-200"}`}
              aria-pressed={showBaseline}
              onClick={handleBaselineToggle}
              title="Toggle baseline overlay"
            >
              Baseline
            </button>
            {showBaseline && (
              <select
                className="bg-transparent text-xs font-bold text-sky-400 focus:outline-none"
                value={activeBaselineNum}
                onChange={(e) => handleBaselineChange(Number(e.target.value))}
              >
                {[...Array(11)].map((_, i) => (
                  <option key={i + 1} value={i + 1} className="bg-slate-900 text-white">
                    B{i + 1}
                  </option>
                ))}
              </select>
            )}
          </div>
          <button
            type="button"
            className={`rounded-full border px-2 py-1 transition-colors ${highlightCritical ? "border-rose-400/25 bg-rose-500/10 text-rose-200" : "border-white/5 bg-white/[0.03] text-slate-400 hover:border-white/10 hover:bg-white/[0.05]"}`}
            aria-pressed={highlightCritical}
            onClick={() => setHighlightCritical((value) => !value)}
            title="Toggle critical path highlighting"
          >
            Critical Path
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-[28px] border border-white/5 bg-slate-950/60 shadow-2xl">
        <div className="flex border-b border-white/5 bg-white/[0.03]">
          <div className="w-[280px] shrink-0 border-r border-white/5 px-4 py-3 text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
            Task
          </div>
          <div className="relative overflow-hidden" style={{ width: `calc(100% - 280px)` }}>
            <div className="flex" style={{ width: timelineWidth }}>
              {headerLabels.map((label, index) => (
                <div
                  key={`${label}-${index}`}
                  className="flex h-11 items-center justify-center border-r border-white/5 px-2 text-[10px] font-black uppercase tracking-[0.16em] text-slate-400"
                  style={{ width: TIMELINE_DAY_WIDTH }}
                >
                  {label}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div
          onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
          className="custom-scrollbar max-h-[72vh] overflow-y-auto"
        >
          <div style={{ height: topSpacer }} />
          <div className="relative" style={{ height: visibleHeight }}>
            <div className="pointer-events-none absolute left-[280px] right-0 top-0 z-10 h-full overflow-hidden">
              <div style={{ width: timelineWidth, height: visibleHeight }}>
                <GanttDependencyOverlay
                  nodes={dependencyNodes}
                  edges={dependencyEdges}
                  rowHeight={ROW_HEIGHT}
                  width={timelineWidth}
                  height={visibleHeight}
                />
              </div>
            </div>

            {visibleTasks.map((task) => {
              const previewTask = getPreviewTask(task);
              const { left, width } = getTaskBarPosition(previewTask, rangeStart);

              // Multi-Baseline Logic
              const comparison = comparisonMap.get(task.task_id);
              const baselinePos = comparison ? getComparisonBarPosition(comparison, rangeStart, true) : null;

              const emphasizeCritical = Boolean(highlightCritical && task.is_critical);
              const variance = comparison?.schedule_variance_days ?? 0;

              return (
                <div
                  key={task.task_id}
                  className="flex border-b border-white/5"
                  style={{ height: ROW_HEIGHT }}
                  onClick={() => handleSelect(task.task_id)}
                >
                  <div className="flex w-[280px] shrink-0 items-center gap-3 border-r border-white/5 px-4">
                    <div
                      className={`h-2.5 w-2.5 rounded-full ${emphasizeCritical ? "bg-rose-400" : "bg-sky-400"}`}
                    />
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-white">{task.task_name}</p>
                      <div className="flex items-center gap-2">
                        <p className="text-[10px] uppercase tracking-[0.14em] text-slate-500">
                          {task.wbs_code || task.task_id}
                        </p>
                        {showBaseline && variance !== 0 && (
                          <span className={`text-[9px] font-bold ${variance > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                            {variance > 0 ? `+${variance}d` : `${variance}d`}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="relative flex-1 overflow-hidden">
                    <div className="absolute inset-0 flex" style={{ width: timelineWidth }}>
                      {days.map((day) => (
                        <div
                          key={`${task.task_id}-${day.toISOString()}`}
                          className="border-r border-white/[0.02]"
                          style={{ width: TIMELINE_DAY_WIDTH }}
                        />
                      ))}
                    </div>

                    {baselinePos && (
                      <div
                        className="absolute top-1/2 z-10 -translate-y-1/2 opacity-40 shadow-[0_0_8px_rgba(255,255,255,0.1)]"
                        style={{ left: Math.max(0, baselinePos.left), width: baselinePos.width }}
                      >
                        <div className="h-2.5 rounded-full border border-white/20 bg-slate-400/20" />
                      </div>
                    )}

                    <Bar
                      task={previewTask}
                      left={left}
                      width={width}
                      emphasizeCritical={highlightCritical}
                      onSelect={handleSelect}
                      onStartDrag={startDrag}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ height: bottomSpacer }} />
        </div>
      </div>

      <p className="px-2 text-[10px] uppercase tracking-[0.16em] text-slate-500">
        Dragging is optimistic. The bar updates locally first, then the store debounces the recalculation request by 300ms.
      </p>
    </div>
  );
}
