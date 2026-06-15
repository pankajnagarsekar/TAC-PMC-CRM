"use client";

import React, { useEffect, useRef } from "react";
import {
  Edit3,
  CornerDownRight,
  CornerUpLeft,
  ArrowUp,
  ArrowDown,
  Trash2,
  CheckCircle2,
  Calendar,
  Layers,
  Copy,
  Clipboard,
  Link,
  Flame,
} from "lucide-react";
import { useScheduleStore } from "@/store/useScheduleStore";
import type { SchedulePredecessor } from "@/types/schedule.types";
import { toast } from "sonner";

// Global clipboard for scheduler copy/paste operations
let clipboardTaskData: {
  task_name: string;
  scheduled_duration: number;
  percent_complete: number;
  is_milestone: boolean;
  notes?: string;
} | null = null;

interface GanttContextMenuProps {
  x: number;
  y: number;
  taskId: string;
  onClose: () => void;
}

export default function GanttContextMenu({ x, y, taskId, onClose }: GanttContextMenuProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);
  const selectedTasks = useScheduleStore((state) => state.selectedTasks);
  const systemState = useScheduleStore((state) => state.systemState);
  const queueCalculation = useScheduleStore((state) => state.queueCalculation);
  const removeTask = useScheduleStore((state) => state.removeTask);
  const indentTask = useScheduleStore((state) => state.indentTask);
  const outdentTask = useScheduleStore((state) => state.outdentTask);
  const openTaskModal = useScheduleStore((state) => state.openTaskModal);
  const getDependencyChain = useScheduleStore((state) => state.getDependencyChain);
  const setHighlightedDependencyChain = useScheduleStore((state) => state.setHighlightedDependencyChain);
  const createDraftTask = useScheduleStore((state) => state.createDraftTask);

  const task = taskMap[taskId];
  const readOnly = systemState === "locked" || Boolean(task?.baseline_locked);

  // Close when clicking outside
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [onClose]);

  if (!task) return null;

  const handleEdit = () => {
    openTaskModal(taskId);
    onClose();
  };

  const handleIndent = () => {
    if (readOnly) return;
    indentTask(taskId);
    onClose();
  };

  const handleOutdent = () => {
    if (readOnly) return;
    outdentTask(taskId);
    onClose();
  };

  const handleInsertAbove = () => {
    if (readOnly) return;
    const currentOrder = [...taskOrder];
    const idx = currentOrder.indexOf(taskId);
    if (idx === -1) return;

    // Create draft
    const draft = createDraftTask(task.project_id, {
      parent_id: task.parent_id || null,
    });

    // Reorder immediately in the store
    const nextOrder = currentOrder.filter((id) => id !== draft.task_id);
    nextOrder.splice(idx, 0, draft.task_id);
    useScheduleStore.setState({ taskOrder: nextOrder });

    toast.success("Task created above");
    onClose();
  };

  const handleInsertBelow = () => {
    if (readOnly) return;
    const currentOrder = [...taskOrder];
    const idx = currentOrder.indexOf(taskId);
    if (idx === -1) return;

    // Create draft
    const draft = createDraftTask(task.project_id, {
      parent_id: task.parent_id || null,
    });

    // Reorder immediately in the store
    const nextOrder = currentOrder.filter((id) => id !== draft.task_id);
    nextOrder.splice(idx + 1, 0, draft.task_id);
    useScheduleStore.setState({ taskOrder: nextOrder });

    toast.success("Task created below");
    onClose();
  };

  const handleToggleMilestone = () => {
    if (readOnly) return;
    const nextIsMilestone = !task.is_milestone;
    queueCalculation({
      task_id: taskId,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: {
        is_milestone: nextIsMilestone,
        scheduled_duration: nextIsMilestone ? 0 : 1,
      },
      trigger_source: "gantt_edit",
    });
    toast.success(nextIsMilestone ? "Converted to Milestone" : "Converted to Task");
    onClose();
  };

  const handleToggleSummary = () => {
    if (readOnly) return;
    const nextIsSummary = !task.is_summary;
    queueCalculation({
      task_id: taskId,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: {
        is_summary: nextIsSummary,
      },
      trigger_source: "gantt_edit",
    });
    toast.success(nextIsSummary ? "Converted to Summary Task" : "Converted to Subtask");
    onClose();
  };

  const handleMarkComplete = () => {
    if (readOnly) return;
    queueCalculation({
      task_id: taskId,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: {
        percent_complete: 100,
        task_status: "completed",
      },
      trigger_source: "gantt_edit",
    });
    toast.success("Task marked 100% complete");
    onClose();
  };

  const handleDelete = () => {
    if (readOnly) return;
    removeTask(taskId);
    onClose();
  };

  const handleCopy = () => {
    clipboardTaskData = {
      task_name: task.task_name,
      scheduled_duration: task.scheduled_duration ?? 1,
      percent_complete: task.percent_complete ?? 0,
      is_milestone: !!task.is_milestone,
      notes: typeof task.notes === "string" ? task.notes : undefined,
    };
    toast.success("Task copied to clipboard");
    onClose();
  };

  const handlePaste = () => {
    if (readOnly || !clipboardTaskData) return;
    queueCalculation({
      task_id: taskId,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: {
        task_name: `${clipboardTaskData.task_name} (Copy)`,
        scheduled_duration: clipboardTaskData.scheduled_duration,
        percent_complete: clipboardTaskData.percent_complete,
        is_milestone: clipboardTaskData.is_milestone,
        notes: clipboardTaskData.notes || null,
      },
      trigger_source: "gantt_edit",
    });
    toast.success("Task values pasted");
    onClose();
  };

  const handleLinkToSelected = () => {
    if (readOnly) return;
    const selectedList = Array.from(selectedTasks).filter((id) => id !== taskId);
    if (selectedList.length === 0) {
      toast.error("Select another task first to establish a dependency link");
      return;
    }

    const targetId = selectedList[0];
    const targetTask = taskMap[targetId];
    if (!targetTask) return;

    // Add targetId as predecessor to this taskId
    const currentPredecessors = task.predecessors || [];
    if (currentPredecessors.some((p) => p.task_id === targetId)) {
      toast.warning("Link already exists");
      return;
    }

    const newPredecessor: SchedulePredecessor = {
      task_id: targetId,
      project_id: targetTask.project_id,
      type: "FS",
      lag_days: 0,
    };

    queueCalculation({
      task_id: taskId,
      project_id: task.project_id,
      version: task.version ?? 1,
      changes: {
        predecessors: [...currentPredecessors, newPredecessor],
      },
      trigger_source: "gantt_edit",
    });

    toast.success(`Linked: ${targetTask.task_name} ➔ ${task.task_name}`);
    onClose();
  };

  const handleShowCriticalPath = () => {
    const chain = getDependencyChain(taskId, "both");
    const highlightSet = new Set(chain);
    highlightSet.add(taskId);
    setHighlightedDependencyChain(highlightSet);
    toast.info("Highlighted task dependency chain");
    onClose();
  };

  // Adjust coordinates if menu goes off screen
  const screenWidth = typeof window !== "undefined" ? window.innerWidth : 1920;
  const screenHeight = typeof window !== "undefined" ? window.innerHeight : 1080;
  const menuWidth = 220;
  const menuHeight = 360;

  const adjustedX = x + menuWidth > screenWidth ? screenWidth - menuWidth - 10 : x;
  const adjustedY = y + menuHeight > screenHeight ? screenHeight - menuHeight - 10 : y;

  return (
    <div
      ref={containerRef}
      className="fixed z-50 w-[220px] rounded-2xl border border-slate-200/80 dark:border-white/10 bg-white/95 dark:bg-slate-950/95 p-1.5 shadow-2xl backdrop-blur-md animate-in fade-in zoom-in-95 duration-100"
      style={{ left: adjustedX, top: adjustedY }}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="px-2.5 py-1.5 border-b border-slate-200/60 dark:border-white/5 mb-1">
        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 dark:text-slate-500 truncate" title={task.task_name}>
          {task.task_name}
        </p>
      </div>

      <button
        onClick={handleEdit}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
      >
        <Edit3 size={13} className="text-slate-400" />
        Edit Details
      </button>

      <div className="h-px bg-slate-200/60 dark:border-white/5 my-1" />

      <button
        onClick={handleIndent}
        disabled={readOnly}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <CornerDownRight size={13} className="text-slate-400" />
        Indent Task
      </button>

      <button
        onClick={handleOutdent}
        disabled={readOnly || !task.parent_id}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <CornerUpLeft size={13} className="text-slate-400" />
        Outdent Task
      </button>

      <button
        onClick={handleInsertAbove}
        disabled={readOnly}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <ArrowUp size={13} className="text-slate-400" />
        Insert Task Above
      </button>

      <button
        onClick={handleInsertBelow}
        disabled={readOnly}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <ArrowDown size={13} className="text-slate-400" />
        Insert Task Below
      </button>

      <div className="h-px bg-slate-200/60 dark:border-white/5 my-1" />

      <button
        onClick={handleToggleMilestone}
        disabled={readOnly}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <Calendar size={13} className="text-slate-400" />
        {task.is_milestone ? "Convert to Subtask" : "Convert to Milestone"}
      </button>

      <button
        onClick={handleToggleSummary}
        disabled={readOnly}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <Layers size={13} className="text-slate-400" />
        {task.is_summary ? "Demote to Subtask" : "Promote to Summary"}
      </button>

      <button
        onClick={handleMarkComplete}
        disabled={readOnly || task.percent_complete === 100}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <CheckCircle2 size={13} className="text-emerald-500" />
        Mark Complete (100%)
      </button>

      <button
        onClick={handleLinkToSelected}
        disabled={readOnly}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <Link size={13} className="text-sky-500" />
        Link to Selected FS
      </button>

      <button
        onClick={handleShowCriticalPath}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
      >
        <Flame size={13} className="text-rose-500 animate-pulse" />
        Highlight Paths
      </button>

      <div className="h-px bg-slate-200/60 dark:border-white/5 my-1" />

      <button
        onClick={handleCopy}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 transition-all"
      >
        <Copy size={13} className="text-slate-400" />
        Copy Task
      </button>

      <button
        onClick={handlePaste}
        disabled={readOnly || !clipboardTaskData}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-white/5 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <Clipboard size={13} className="text-slate-400" />
        Paste Task Values
      </button>

      <div className="h-px bg-slate-200/60 dark:border-white/5 my-1" />

      <button
        onClick={handleDelete}
        disabled={readOnly}
        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-left text-xs font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-500/10 disabled:opacity-45 disabled:pointer-events-none transition-all"
      >
        <Trash2 size={13} />
        Delete Task
      </button>
    </div>
  );
}
