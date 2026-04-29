"use client";

import React, { memo, useEffect, useMemo, useRef, useState, useCallback } from "react";
import { GripVertical, MoveHorizontal, Pencil, Eye } from "lucide-react";
import { addDays, format, startOfDay, differenceInCalendarDays } from "date-fns";

import { useScheduleStore } from "@/store/useScheduleStore";
import type { ScheduleTask, BaselineComparisonResult } from "@/types/schedule.types";
import {
  buildCalendarColumns,
  calculateTimelineRange,
  getComparisonBarPosition,
  getTaskBarPosition,
  getTaskDurationDays,
  normalizeTaskOrder,
  parseTaskDate,
  ROW_HEIGHT,
  getTimescaleWidth,
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
  isDragging,
  onSelect,
  onOpenModal,
  onStartDrag,
}: {
  task: ScheduleTask;
  left: number;
  width: number;
  emphasizeCritical: boolean;
  isDragging: boolean;
  onSelect: (taskId: string) => void;
  onOpenModal: (taskId: string) => void;
  onStartDrag: (task: ScheduleTask, mode: DragMode, startX: number) => void;
}) {
  const isMilestone = Boolean(task.is_milestone || task.scheduled_duration === 0);
  const isSummary = Boolean(task.is_summary);
  const barLeft = Math.max(0, left);
  const isCriticalHighlighted = Boolean(emphasizeCritical && task.is_critical);
  const percent = task.percent_complete ?? 0;

  const beginDrag = (mode: DragMode) => (event: React.PointerEvent<HTMLButtonElement | HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    onStartDrag(task, mode, event.clientX);
  };

  if (isMilestone) {
    return (
      <div
        className="absolute top-1/2 z-30 -translate-y-1/2 cursor-pointer group"
        style={{ left: left - 8, width: 16, height: 16 }}
        onClick={() => onSelect(task.task_id)}
      >
        <div
          className={`h-full w-full rotate-45 border-2 shadow-xl transition-all ${isCriticalHighlighted ? 'bg-rose-600 border-rose-400' : 'bg-slate-900 dark:bg-white border-slate-700 dark:border-slate-300'} group-hover:scale-125`}
        />
        <div className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap opacity-0 group-hover:opacity-100 bg-slate-900 dark:bg-slate-950 text-white text-[8px] font-black uppercase px-2 py-1 rounded-lg border border-white/10 shadow-2xl transition-opacity z-50">
          {task.task_name} (M)
        </div>
      </div>
    );
  }

  if (isSummary) {
    return (
      <div
        className="absolute top-1/2 z-20 -translate-y-1/2 group cursor-pointer"
        style={{ left: barLeft, width }}
        onClick={() => onSelect(task.task_id)}
      >
        {/* MS Project Style Summary Bar (Bracket) */}
        <div className="relative h-6 w-full">
          <div className="absolute top-0 h-2 w-full bg-slate-900 dark:bg-slate-200 rounded-sm shadow-sm" />
          <div className="absolute left-0 top-0 h-4 w-1.5 bg-slate-900 dark:bg-slate-200 rounded-bl-sm" />
          <div className="absolute right-0 top-0 h-4 w-1.5 bg-slate-900 dark:bg-slate-200 rounded-br-sm" />
          
          {/* Progress Overlay for Summary */}
          {percent > 0 && (
            <div 
              className="absolute top-0 h-1 bg-sky-500 rounded-sm transition-all duration-500" 
              style={{ width: `${percent}%` }}
            />
          )}
        </div>
        <div className="absolute left-0 top-full mt-1 whitespace-nowrap opacity-0 group-hover:opacity-100 text-[8px] font-bold text-slate-500 uppercase tracking-widest transition-opacity">
          Summary: {task.task_name} ({percent}%)
        </div>
      </div>
    );
  }

  return (
    <div
      className="absolute top-1/2 z-20 -translate-y-1/2"
      style={{ left: barLeft, width }}
      onClick={() => onSelect(task.task_id)}
    >
      <div
        className={`group relative h-9 rounded-xl border px-3 py-1.5 shadow-lg transition-transform duration-150 cursor-grab active:cursor-grabbing overflow-hidden ${isDragging
          ? "scale-[1.03] ring-2 ring-orange-400/60 shadow-orange-400/20 shadow-xl opacity-90"
          : isCriticalHighlighted
            ? "border-rose-400/40 bg-rose-500/10"
            : "border-slate-300/50 dark:border-white/10 bg-white dark:bg-slate-900"
          }`}
      >
        {/* Progress Fill */}
        <div 
          className={`absolute inset-0 z-0 h-full transition-all duration-700 ${isCriticalHighlighted ? 'bg-rose-500/20' : 'bg-sky-500/15'}`}
          style={{ width: `${percent}%` }}
        />

        <div className="relative z-10 flex h-full items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-[10px] font-black uppercase tracking-[0.14em] text-slate-900 dark:text-white leading-none">
              {task.task_name}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className={`text-[8px] font-black px-1 rounded-sm ${percent === 100 ? 'bg-emerald-500/20 text-emerald-600' : 'bg-slate-200 dark:bg-white/10 text-slate-500'}`}>
                {percent}%
              </span>
              <p className="text-[8px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-tighter">
                {formatTaskDurationLabel(task)}
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              type="button"
              className="rounded-md p-1 hover:bg-slate-200 dark:hover:bg-white/10 text-sky-500"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onOpenModal(task.task_id);
              }}
            >
              <Eye size={12} />
            </button>
            <div
              className="rounded-md p-1 hover:bg-slate-200 dark:hover:bg-white/10 cursor-move"
              onPointerDown={beginDrag("move")}
            >
              <MoveHorizontal size={12} />
            </div>
          </div>
        </div>
        
        {/* Drag Handles */}
        <div 
          className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-orange-500/30 transition-colors"
          onPointerDown={beginDrag("start")}
        />
        <div 
          className="absolute right-0 top-0 bottom-0 w-1.5 cursor-ew-resize hover:bg-orange-500/30 transition-colors"
          onPointerDown={beginDrag("finish")}
        />
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
  const setSelectedTask = useScheduleStore((state) => state.setSelectedTask);
  const openTaskModal = useScheduleStore((state) => state.openTaskModal);
  const systemState = useScheduleStore((state) => state.systemState);
  const timescale = useScheduleStore((state) => state.timescale);
  const setTimescale = useScheduleStore((state) => state.setTimescale);
  const projectCalendar = useScheduleStore((state) => state.projectCalendar);

  const unitWidth = getTimescaleWidth(timescale);

  // Baseline Comparison Store
  const comparisonData = useScheduleStore((state) => state.comparisonData);
  const fetchBaselineComparison = useScheduleStore((state) => state.fetchBaselineComparison);
  const clearComparison = useScheduleStore((state) => state.clearComparison);

  const readOnly = systemState === "locked";

  const commitDrag = useCallback((task: ScheduleTask, mode: DragMode, deltaDays: number) => {
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
  }, [readOnly, queueCalculation]);

  const tasks = useMemo(
    () => normalizeTaskOrder(taskMap, taskOrder),
    [taskMap, taskOrder],
  );

  const comparisonMap = useMemo(() => {
    if (!comparisonData) return new Map<string, BaselineComparisonResult>();
    const map = new Map<string, BaselineComparisonResult>();
    comparisonData.forEach(item => map.set(item.task_id, item));
    return map;
  }, [comparisonData]);

  const { start: rangeStart, end: rangeEnd } = useMemo(() => calculateTimelineRange(tasks), [tasks]);
  const days = useMemo(() => buildCalendarColumns(rangeStart, rangeEnd), [rangeStart, rangeEnd]);

  // S-BUG #38: Auto-scroll to today on mount
  useEffect(() => {
    if (scrollContainerRef.current && days.length > 0) {
      const today = startOfDay(new Date());
      const left = differenceInCalendarDays(today, rangeStart) * (unitWidth / (timescale === "day" ? 1 : 7));
      // Check if today is within range
      if (left >= 0 && left <= days.length * unitWidth) {
        scrollContainerRef.current.scrollLeft = Math.max(0, left - 400);
      }
    }
  }, [rangeStart, days.length, timescale, unitWidth]);

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
  const taskMapRef = useRef(taskMap);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const topScrollRef = useRef<HTMLDivElement>(null);

  const handleScroll = useCallback(() => {
    if (scrollContainerRef.current && topScrollRef.current) {
      topScrollRef.current.scrollLeft = scrollContainerRef.current.scrollLeft;
    }
  }, []);

  useEffect(() => {
    taskMapRef.current = taskMap;
  }, [taskMap]);
  const viewportHeight = 420;
  const visibleCount = Math.ceil(viewportHeight / ROW_HEIGHT) + 6;
  const startIndex = Math.max(0, Math.floor(scrollTop / ROW_HEIGHT) - 3);
  const endIndex = Math.min(tasks.length, startIndex + visibleCount);
  const visibleTasks = tasks.slice(startIndex, endIndex);
  const topSpacer = startIndex * ROW_HEIGHT;
  const bottomSpacer = Math.max(0, (tasks.length - endIndex) * ROW_HEIGHT);
  
  const dayWidth = timescale === "day" ? unitWidth : 
                   timescale === "week" ? unitWidth / 7 :
                   timescale === "month" ? unitWidth / 30 :
                   unitWidth / 90;

  const timelineWidth = days.length * dayWidth;
  const visibleHeight = visibleTasks.length * ROW_HEIGHT;

  const getPreviewTask = useCallback((task: ScheduleTask): ScheduleTask => {
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
  }, [activeDragTaskId, previewDeltaDays]);

  const dependencyNodes = useMemo(() => {
    const nodes = new Map<string, GanttDependencyNode>();
    visibleTasks.forEach((task, index) => {
      const previewTask = getPreviewTask(task);
      const { left, width } = getTaskBarPosition(previewTask, rangeStart, timescale);
      nodes.set(task.task_id, {
        taskId: task.task_id,
        rowIndex: index,
        left,
        width,
      });
    });
    return nodes;
  }, [rangeStart, visibleTasks, getPreviewTask, timescale]);

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

  const monthHeaders = useMemo(() => {
    const headers: { label: string; width: number }[] = [];
    if (days.length === 0) return [];

    let currentLabel = "";
    let lastObj: { label: string, width: number } | null = null;

    days.forEach((day) => {
      let label = "";
      if (timescale === "day" || timescale === "week") {
        label = format(day, "MMMM yyyy");
      } else if (timescale === "month") {
        label = format(day, "yyyy");
      } else {
        label = `FY ${format(day, "yy")}`;
      }

      if (label !== currentLabel) {
        currentLabel = label;
        lastObj = { label, width: dayWidth };
        headers.push(lastObj);
      } else if (lastObj) {
        lastObj.width += dayWidth;
      }
    });
    return headers;
  }, [days, timescale, dayWidth]);

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const current = dragStateRef.current;
      if (!current) return;
      const delta = Math.round((event.clientX - current.startX) / dayWidth);
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
        const task = taskMapRef.current[taskId];
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
  }, [readOnly, commitDrag]);

  const startDrag = (task: ScheduleTask, mode: DragMode, startX: number) => {
    if (readOnly || !mode) return;
    dragStateRef.current = {
      taskId: task.task_id,
      mode,
      startX,
      originalStart: task.scheduled_start ?? null,
      originalFinish: task.scheduled_finish ?? null,
    };
    setActiveDragTaskId(task.task_id); // S-BUG #14: Immediate feedback
  };

  const handleSelect = (taskId: string) => {
    setSelectedTask(taskId);
  };

  const handleOpenModal = (taskId: string) => {
    openTaskModal(taskId);
  };


  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 px-2">
        <div>
          <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-900 dark:text-slate-200">
            Project Planning Surface
          </h3>
          <p className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-600">
            Interactive Gantt with Critical Path & Progress Rollups
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">
          <span className="rounded-full border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-2 py-1">
            {tasks.length.toLocaleString("en-US")} visible tasks
          </span>
          {selectedTasks.size > 0 && (
            <span className="rounded-full border border-sky-400/20 bg-sky-500/10 px-2 py-1 text-sky-300">
              {selectedTasks.size} selected
            </span>
          )}
          <div className="flex items-center gap-1.5 rounded-full border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] p-0.5">
            {[
              { id: 'day', label: 'D' },
              { id: 'week', label: 'W' },
              { id: 'month', label: 'M' },
              { id: 'quarter', label: 'Q' }
            ].map(scale => (
              <button
                key={scale.id}
                onClick={() => setTimescale(scale.id as any)}
                className={`w-7 h-7 flex items-center justify-center rounded-full text-[9px] font-black transition-all ${timescale === scale.id ? 'bg-orange-600 text-white shadow-lg shadow-orange-500/20' : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'}`}
              >
                {scale.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1.5 rounded-full border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] p-0.5">
            <button
              type="button"
              className={`rounded-full px-2 py-0.5 transition-colors ${showBaseline ? "bg-slate-200 dark:bg-white/[0.08] text-slate-900 dark:text-white" : "text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"}`}
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
                  <option key={i + 1} value={i + 1}>
                    B{i + 1}
                  </option>
                ))}
              </select>
            )}
          </div>
          <button
            type="button"
            className={`rounded-full border px-2 py-1 transition-colors ${highlightCritical ? "border-rose-400/50 bg-rose-500/10 text-rose-700 dark:text-rose-200" : "border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-white/[0.03] text-slate-500 dark:text-slate-400 hover:border-slate-300 dark:hover:border-white/10 hover:bg-slate-100 dark:hover:bg-white/[0.05]"}`}
            aria-pressed={highlightCritical}
            onClick={() => setHighlightCritical((value) => !value)}
            title="Toggle critical path highlighting"
          >
            Critical Path
          </button>
        </div>
      </div>

      {/* Top scroll sync indicator */}
      <div
        ref={topScrollRef}
        className="overflow-x-auto overflow-y-hidden h-4 rounded-t-[28px] border border-b-0 border-slate-200 dark:border-white/5 bg-slate-50 dark:bg-slate-900/30"
        style={{ scrollBehavior: 'smooth' }}
      >
        <div style={{ minWidth: 280 + timelineWidth }} className="h-4" />
      </div>

      <div ref={scrollContainerRef} onScroll={handleScroll} className="overflow-x-auto overflow-y-hidden rounded-b-[28px] border border-slate-200 dark:border-white/5 bg-white/60 dark:bg-slate-950/60 shadow-2xl">
        <div style={{ minWidth: 280 + timelineWidth }}>
          <div className="flex border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-40">
            <div className="w-[280px] shrink-0 border-r border-slate-200 dark:border-slate-800 px-4 flex items-center text-[10px] font-black uppercase tracking-[0.2em] text-slate-600 dark:text-slate-300 sticky left-0 z-50 bg-white dark:bg-slate-900">
              Task Stream
            </div>
            <div className="relative" style={{ width: timelineWidth }}>
              {/* Header: Months & Days */}
              <div className="flex flex-col">
                {/* Month Row */}
                <div className="flex border-b border-slate-200 dark:border-white/10 bg-slate-100 dark:bg-white/[0.05]">
                  {monthHeaders.map((m, i) => (
                    <div
                      key={i}
                      className="h-9 flex items-center border-r border-slate-200 dark:border-white/10 text-[10px] font-black uppercase tracking-[0.2em] text-slate-800 dark:text-slate-200 whitespace-nowrap px-4 bg-slate-50/50 dark:bg-white/[0.02] relative"
                      style={{ width: m.width }}
                    >
                      <span className="sticky left-4 z-10 block">
                        {m.label}
                      </span>
                    </div>
                  ))}
                </div>
                {/* Day Row */}
                <div className="flex">
                  {days.map((day, index) => {
                    const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                    return (
                      <div
                        key={index}
                        className={`flex h-10 items-center justify-center border-r border-slate-200 dark:border-white/5 px-2 text-[10px] font-black tracking-tight ${isWeekend ? 'text-rose-500/60 dark:text-rose-400/40 bg-slate-50 dark:bg-white/[0.01]' : 'text-slate-700 dark:text-slate-300'}`}
                        style={{ width: dayWidth }}
                      >
                        {timescale === "day" ? format(day, "dd") : format(day, "d")}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>

          <div
            onScroll={(event) => setScrollTop(event.currentTarget.scrollTop)}
            className="custom-scrollbar max-h-[72vh] overflow-y-auto"
          >
            <div style={{ height: topSpacer }} />
            <div className="relative" style={{ height: visibleHeight }}>
              {/* Background Grid Lines */}
              <div className="pointer-events-none absolute left-[280px] top-0 z-0 h-full flex">
                {days.map((day, i) => {
                  const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                  const isHoliday = projectCalendar?.exceptions.some(ex => {
                    const d = format(day, 'yyyy-MM-dd');
                    return d >= ex.start_date && d <= ex.end_date;
                  });
                  const isNonWorking = !projectCalendar?.working_days.includes(day.getDay());

                  return (
                    <div 
                      key={i} 
                      className={`h-full border-r border-slate-200/40 dark:border-white/[0.03] ${isHoliday || isNonWorking || isWeekend ? 'bg-slate-100/30 dark:bg-white/[0.02]' : ''}`} 
                      style={{ width: dayWidth }} 
                    >
                      {isHoliday && i % 2 === 0 && (
                        <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05] bg-[repeating-linear-gradient(45deg,transparent,transparent_5px,#000_5px,#000_10px)]" />
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Today Marker */}
              <div 
                className="absolute top-0 z-40 h-full w-px bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.5)] pointer-events-none"
                style={{ left: 280 + (differenceInCalendarDays(new Date(), rangeStart) * dayWidth) }}
              >
                <div className="absolute -left-1.5 top-0 h-3 w-3 rounded-full bg-orange-500 shadow-lg" />
              </div>

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
                const { left, width } = getTaskBarPosition(previewTask, rangeStart, timescale);

                // Multi-Baseline Logic
                const comparison = comparisonMap.get(task.task_id);
                const baselinePos = comparison ? getComparisonBarPosition(comparison, rangeStart, true, timescale) : null;

                const emphasizeCritical = Boolean(highlightCritical && task.is_critical);
                const variance = comparison?.schedule_variance_days ?? 0;

                return (
                  <div
                    key={task.task_id}
                    className={`flex border-b border-slate-200 dark:border-white/5 transition-colors ${task.is_summary ? 'bg-slate-50/30 dark:bg-white/[0.01]' : 'hover:bg-slate-50 dark:hover:bg-white/[0.02]'}`}
                    style={{ height: ROW_HEIGHT }}
                    onClick={() => handleSelect(task.task_id)}
                  >
                    <div className="flex w-[280px] shrink-0 items-center gap-3 border-r border-slate-200 dark:border-white/5 px-4 sticky left-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur-sm shadow-[4px_0_8px_rgba(0,0,0,0.05)]">
                      <div
                        className={`h-2.5 w-2.5 rounded-full ${emphasizeCritical ? "bg-rose-500 dark:bg-rose-400" : "bg-sky-500 dark:bg-sky-400"}`}
                      />
                      <div className="min-w-0">
                        <p className="truncate text-xs font-semibold text-slate-900 dark:text-white leading-tight">{task.task_name}</p>
                        <div className="flex items-center gap-2">
                          <p className="text-[10px] uppercase tracking-[0.14em] text-slate-600 font-bold">
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
                        {days.map((day) => {
                          const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                          const isNonWorking = projectCalendar && !projectCalendar.working_days.includes(day.getDay());
                          return (
                            <div
                              key={`${task.task_id}-${day.toISOString()}`}
                              className={`border-r border-slate-200 dark:border-white/[0.05] ${isWeekend || isNonWorking ? 'bg-slate-100/50 dark:bg-white/[0.01]' : ''}`}
                              style={{ width: dayWidth }}
                            />
                          );
                        })}
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
                        isDragging={activeDragTaskId === task.task_id}
                        onSelect={handleSelect}
                        onOpenModal={handleOpenModal}
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
      </div>

      <p className="px-2 pt-2 text-[10px] uppercase tracking-[0.16em] text-slate-600">
        Dragging is optimistic. The bar updates locally first, then the store debounces the recalculation request by 300ms.
      </p>
    </div>
  );
}

