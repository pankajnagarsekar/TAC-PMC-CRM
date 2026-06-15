"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link2, Search, X } from "lucide-react";

import { useScheduleStore } from "@/store/useScheduleStore";
import type { SchedulePredecessor, ScheduleTask } from "@/types/schedule.types";

// ─── MS Project Syntax Parser ──────────────────────────────────────

/**
 * Parses MS Project-style predecessor syntax: "14FS+2d", "task-42SS-1d", "7"
 * Returns null if the syntax is invalid.
 */
export function parsePredecessorSyntax(input: string): {
  taskId: string;
  type: SchedulePredecessor["type"];
  lag: number;
} | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  // Pattern: <taskId>[<type>][<+/->lag[d]]
  const match = trimmed.match(
    /^(.+?)(?:(FS|FF|SS|SF))?\s*([+-]\d+)?\s*d?\s*$/i
  );

  if (!match) {
    // Fallback: treat entire input as a task ID
    return { taskId: trimmed, type: "FS", lag: 0 };
  }

  const [, taskId, rawType, rawLag] = match;
  return {
    taskId: taskId.trim(),
    type: (rawType?.toUpperCase() as SchedulePredecessor["type"]) ?? "FS",
    lag: rawLag ? parseInt(rawLag, 10) : 0,
  };
}

// ─── Component ─────────────────────────────────────────────────────

type DependencyAutocompleteProps = {
  /** The task we're adding a dependency to */
  targetTaskId: string;
  /** Called when a dependency is confirmed */
  onAddDependency?: (predecessor: SchedulePredecessor) => void;
  /** Called when a task is selected but not yet added */
  onSelectTaskId?: (taskId: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Whether the input is disabled */
  disabled?: boolean;
  className?: string;
};

export default function DependencyAutocomplete({
  targetTaskId,
  onAddDependency,
  onSelectTaskId,
  placeholder = "Search tasks or use syntax: 14FS+2d",
  disabled = false,
  className = "",
}: DependencyAutocompleteProps) {
  const taskMap = useScheduleStore((state) => state.taskMap);
  const taskOrder = useScheduleStore((state) => state.taskOrder);

  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Build searchable task list (exclude the target task itself)
  const searchableTasks = useMemo(() => {
    return taskOrder
      .filter((tid) => tid !== targetTaskId)
      .map((tid) => taskMap[tid])
      .filter(Boolean) as ScheduleTask[];
  }, [taskOrder, taskMap, targetTaskId]);

  // Filter results based on query
  const filteredTasks = useMemo(() => {
    if (!query.trim()) return searchableTasks.slice(0, 20);

    const parsedSyntax = parsePredecessorSyntax(query);
    const searchTerm = (parsedSyntax?.taskId ?? query).toLowerCase();

    return searchableTasks
      .filter((task) => {
        const nameMatch = task.task_name?.toLowerCase().includes(searchTerm);
        const wbsMatch = task.wbs_code?.toLowerCase().includes(searchTerm);
        const idMatch = task.task_id.toLowerCase().includes(searchTerm);
        return nameMatch || wbsMatch || idMatch;
      })
      .slice(0, 15);
  }, [query, searchableTasks]);

  const handleSelect = useCallback(
    (task: ScheduleTask) => {
      const parsed = parsePredecessorSyntax(query);
      const isSyntax = parsed && (parsed.type !== "FS" || parsed.lag !== 0 || query.toUpperCase().includes("FS") || query.toUpperCase().includes("SS") || query.toUpperCase().includes("FF") || query.toUpperCase().includes("SF"));

      if (isSyntax && onAddDependency) {
        const predecessor: SchedulePredecessor = {
          task_id: task.task_id,
          project_id: task.project_id,
          type: parsed.type,
          lag_days: parsed.lag,
          is_external: false,
          strength: "hard",
        };
        onAddDependency(predecessor);
        setQuery("");
        if (onSelectTaskId) {
          onSelectTaskId("");
        }
      } else {
        setQuery(`${task.wbs_code || task.task_id} - ${task.task_name}`);
        if (onSelectTaskId) {
          onSelectTaskId(task.task_id);
        }
      }
      setIsOpen(false);
      setHighlightedIndex(0);
    },
    [query, onAddDependency, onSelectTaskId]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen || filteredTasks.length === 0) {
        if (e.key === "ArrowDown") {
          setIsOpen(true);
        }
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightedIndex((prev) =>
          Math.min(prev + 1, filteredTasks.length - 1)
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const selected = filteredTasks[highlightedIndex];
        if (selected) handleSelect(selected);
      } else if (e.key === "Escape") {
        setIsOpen(false);
      }
    },
    [isOpen, filteredTasks, highlightedIndex, handleSelect]
  );

  // Scroll highlighted item into view
  useEffect(() => {
    if (!listRef.current) return;
    const item = listRef.current.children[highlightedIndex] as HTMLElement;
    item?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest("[data-dep-autocomplete]")) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div data-dep-autocomplete className={`relative ${className}`}>
      {/* Input */}
      <div className="relative">
        <Search
          size={14}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            const val = e.target.value;
            setQuery(val);
            setIsOpen(true);
            setHighlightedIndex(0);
            if (!val && onSelectTaskId) {
              onSelectTaskId("");
            }
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          className="w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] pl-9 pr-3 py-2.5 text-xs font-medium text-slate-900 dark:text-white outline-none focus:border-orange-400/40 transition-all"
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              if (onSelectTaskId) {
                onSelectTaskId("");
              }
              inputRef.current?.focus();
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 h-5 w-5 flex items-center justify-center rounded text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
          >
            <X size={12} />
          </button>
        )}
      </div>

      {/* Syntax help hint */}
      {isOpen && query && (
        <div className="mt-1 px-3 py-1.5 text-[9px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
          Syntax: <span className="text-orange-400">taskID</span>
          <span className="text-sky-400">FS</span>
          <span className="text-emerald-400">+2d</span> — e.g.{" "}
          <span className="text-white/60">14FS+2d</span>
        </div>
      )}

      {/* Dropdown */}
      {isOpen && filteredTasks.length > 0 && (
        <div
          ref={listRef}
          className="absolute z-[70] w-full mt-1 max-h-64 overflow-y-auto rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-950 shadow-2xl p-1.5 animate-in fade-in zoom-in-95 duration-150"
        >
          {filteredTasks.map((task, idx) => (
            <button
              key={task.task_id}
              type="button"
              onClick={() => handleSelect(task)}
              onMouseEnter={() => setHighlightedIndex(idx)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-colors ${
                idx === highlightedIndex
                  ? "bg-orange-50 dark:bg-orange-500/10"
                  : "hover:bg-slate-50 dark:hover:bg-white/[0.03]"
              }`}
            >
              {/* Status dot */}
              <div
                className={`h-2 w-2 rounded-full shrink-0 ${
                  task.is_critical
                    ? "bg-rose-500"
                    : task.is_milestone
                    ? "bg-amber-500"
                    : "bg-sky-500"
                }`}
              />

              {/* Task info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-black text-slate-400 dark:text-slate-500 tracking-wider shrink-0">
                    {task.wbs_code || task.task_id}
                  </span>
                  <span className="text-[11px] font-semibold text-slate-900 dark:text-white truncate">
                    {task.task_name}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  {task.scheduled_duration != null && (
                    <span className="text-[9px] text-slate-400">
                      {task.scheduled_duration}d
                    </span>
                  )}
                  {task.is_milestone && (
                    <span className="text-[8px] font-black uppercase tracking-wider text-amber-500 bg-amber-500/10 px-1.5 py-0.5 rounded">
                      Milestone
                    </span>
                  )}
                  {task.is_summary && (
                    <span className="text-[8px] font-black uppercase tracking-wider text-indigo-500 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                      Summary
                    </span>
                  )}
                </div>
              </div>

              {/* Link icon */}
              <Link2 size={12} className="text-slate-300 dark:text-slate-600 shrink-0" />
            </button>
          ))}
        </div>
      )}

      {/* No results */}
      {isOpen && query && filteredTasks.length === 0 && (
        <div className="absolute z-[70] w-full mt-1 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-slate-950 shadow-xl p-6 text-center">
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            No matching tasks found
          </p>
        </div>
      )}
    </div>
  );
}
