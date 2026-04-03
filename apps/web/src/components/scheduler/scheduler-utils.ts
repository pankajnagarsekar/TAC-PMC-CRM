import { addDays, differenceInCalendarDays, format, isValid, parse, parseISO, startOfDay } from "date-fns";
import type {
  ScheduleTask,
  ScheduleTaskStatus,
  ScheduleTaskMap,
  BaselineComparisonResult,
} from "@/types/schedule.types";

export const ROW_HEIGHT = 54;
export const TIMELINE_DAY_WIDTH = 40;
export const GRID_HEADER_HEIGHT = 44;

export const KANBAN_STATUSES: ScheduleTaskStatus[] = [
  "draft",
  "not_started",
  "in_progress",
  "completed",
  "closed",
];

export const KANBAN_META: Record<
  ScheduleTaskStatus,
  { label: string; tone: string; description: string }
> = {
  draft: {
    label: "Draft",
    tone: "text-slate-300 border-slate-500/20 bg-slate-500/10",
    description: "Pre-calculation tasks and imports waiting for CPM.",
  },
  not_started: {
    label: "Not Started",
    tone: "text-sky-300 border-sky-500/20 bg-sky-500/10",
    description: "Scheduled but not yet in execution.",
  },
  in_progress: {
    label: "In Progress",
    tone: "text-amber-300 border-amber-500/20 bg-amber-500/10",
    description: "Work is actively moving.",
  },
  completed: {
    label: "Completed",
    tone: "text-emerald-300 border-emerald-500/20 bg-emerald-500/10",
    description: "Finished and ready for closure.",
  },
  closed: {
    label: "Closed",
    tone: "text-rose-300 border-rose-500/20 bg-rose-500/10",
    description: "Immutable and locked from further edits.",
  },
};

export const VALID_STATUS_TRANSITIONS: Record<ScheduleTaskStatus, ScheduleTaskStatus[]> = {
  draft: ["not_started"],
  not_started: ["in_progress", "closed"],
  in_progress: ["completed", "not_started"],
  completed: ["in_progress", "closed"],
  closed: [],
};

export function parseTaskDate(value?: string | null): Date | null {
  if (!value) return null;

  const iso = parseISO(value);
  if (isValid(iso)) return startOfDay(iso);

  const patterns = [
    "dd-MM-yy",
    "dd/MM/yy",
    "dd-MM-yyyy",
    "dd/MM/yyyy",
    "dd MMM yy",
    "dd MMM yyyy",
    "MMM dd, yyyy"
  ];
  for (const pattern of patterns) {
    const parsed = parse(value, pattern, new Date());
    if (isValid(parsed)) return startOfDay(parsed);
  }

  const fallback = new Date(value);
  return isValid(fallback) ? startOfDay(fallback) : null;
}

export function formatTaskDate(value?: string | null, fallback = "—"): string {
  const date = parseTaskDate(value);
  return date ? format(date, "dd MMM yy") : fallback;
}

export function taskKey(task: ScheduleTask): string {
  return String(task.wbs_code || task.task_id || "");
}

export function normalizeTaskOrder(taskMap: ScheduleTaskMap, taskOrder: string[]): ScheduleTask[] {
  if (!taskMap) return [];

  const ordered = (taskOrder || [])
    .map((taskId) => taskMap[taskId])
    .filter((task): task is ScheduleTask => Boolean(task && (task.task_id || task.wbs_code)));

  const taskOrderSet = new Set(taskOrder);
  const missing = Object.values(taskMap).filter(
    (task) => task && (task.task_id || task.wbs_code) && !taskOrderSet.has(task.task_id)
  );

  return [...ordered, ...missing].sort((a, b) =>
    taskKey(a).localeCompare(taskKey(b), undefined, { numeric: true })
  );
}

export function calculateTimelineRange(tasks: ScheduleTask[]) {
  const parsedDates = (tasks || []).flatMap((task) => [
    parseTaskDate(task.scheduled_start),
    parseTaskDate(task.scheduled_finish),
    parseTaskDate(task.baseline_start),
    parseTaskDate(task.baseline_finish),
    parseTaskDate(task.early_start),
    parseTaskDate(task.late_finish),
  ]).filter((date): date is Date => Boolean(date));

  if (parsedDates.length === 0) {
    const base = startOfDay(new Date());
    return { start: base, end: addDays(base, 90) };
  }

  const min = parsedDates.reduce((acc, date) => (date < acc ? date : acc), parsedDates[0]);
  const max = parsedDates.reduce((acc, date) => (date > acc ? date : acc), parsedDates[0]);

  return {
    start: addDays(startOfDay(min), -14),
    end: addDays(startOfDay(max), 90),
  };
}

export function getTaskDurationDays(task: ScheduleTask): number {
  if (typeof task.scheduled_duration === "number" && task.scheduled_duration >= 0) {
    return task.scheduled_duration;
  }
  const start = parseTaskDate(task.scheduled_start);
  const finish = parseTaskDate(task.scheduled_finish);
  if (!start || !finish) return 0;
  return Math.max(0, differenceInCalendarDays(finish, start) + 1);
}

export function getTaskStatus(task: ScheduleTask): ScheduleTaskStatus {
  return task.task_status ?? "draft";
}

export function buildCalendarColumns(start: Date, end: Date) {
  const days: Date[] = [];
  let current = startOfDay(start);
  const normalizedEnd = startOfDay(end);

  while (current <= normalizedEnd) {
    days.push(current);
    current = addDays(current, 1);
  }

  return days;
}

export function getTaskBarPosition(task: ScheduleTask, rangeStart: Date) {
  const start = parseTaskDate(task.scheduled_start);
  const finish = parseTaskDate(task.scheduled_finish);
  if (!start || !finish) {
    return { left: 0, width: 0 };
  }

  const left = differenceInCalendarDays(start, rangeStart) * TIMELINE_DAY_WIDTH;
  const width = Math.max(
    TIMELINE_DAY_WIDTH,
    (differenceInCalendarDays(finish, start) + 1) * TIMELINE_DAY_WIDTH,
  );

  return { left, width };
}

export function getComparisonBarPosition(
  comparison: BaselineComparisonResult,
  rangeStart: Date,
  isA: boolean = true
) {
  const start = parseTaskDate(isA ? comparison.baseline_a_start : comparison.baseline_b_start);
  const finish = parseTaskDate(isA ? comparison.baseline_a_finish : comparison.baseline_b_finish);
  if (!start || !finish) {
    return null;
  }

  const left = differenceInCalendarDays(start, rangeStart) * TIMELINE_DAY_WIDTH;
  const width = Math.max(
    TIMELINE_DAY_WIDTH,
    (differenceInCalendarDays(finish, start) + 1) * TIMELINE_DAY_WIDTH,
  );

  return { left, width };
}

export function getBaselineBarPosition(task: ScheduleTask, rangeStart: Date) {
  const start = parseTaskDate(task.baseline_start);
  const finish = parseTaskDate(task.baseline_finish);
  if (!start || !finish) {
    return null;
  }

  const left = differenceInCalendarDays(start, rangeStart) * TIMELINE_DAY_WIDTH;
  const width = Math.max(
    TIMELINE_DAY_WIDTH,
    (differenceInCalendarDays(finish, start) + 1) * TIMELINE_DAY_WIDTH,
  );

  return { left, width };
}

export function createTaskPatch(
  task: ScheduleTask,
  changes: Partial<ScheduleTask>,
): Partial<ScheduleTask> {
  return {
    ...task,
    ...changes,
  };
}

export function buildTaskStatusTransition(
  task: ScheduleTask,
  nextStatus: ScheduleTaskStatus,
) {
  const currentStatus = getTaskStatus(task);
  if (currentStatus === nextStatus) {
    return null;
  }

  if (!VALID_STATUS_TRANSITIONS[currentStatus]?.includes(nextStatus)) {
    return null;
  }

  const today = format(new Date(), "yyyy-MM-dd");

  if (nextStatus === "completed") {
    return {
      task_status: nextStatus,
      percent_complete: 100,
      actual_finish: today,
    } satisfies Partial<ScheduleTask>;
  }

  if (nextStatus === "in_progress") {
    return {
      task_status: nextStatus,
      actual_start: task.actual_start ?? today,
      actual_finish: null,
      percent_complete: Math.min(task.percent_complete ?? 0, 99),
    } satisfies Partial<ScheduleTask>;
  }

  if (nextStatus === "not_started") {
    return {
      task_status: nextStatus,
      actual_start: null,
      actual_finish: null,
      percent_complete: Math.min(task.percent_complete ?? 0, 99),
    } satisfies Partial<ScheduleTask>;
  }

  if (nextStatus === "closed") {
    return {
      task_status: nextStatus,
    } satisfies Partial<ScheduleTask>;
  }

  return {
    task_status: nextStatus,
  } satisfies Partial<ScheduleTask>;
}
