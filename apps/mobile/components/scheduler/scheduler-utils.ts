// SCHEDULER UTILS (mobile)
// Ported from apps/web/src/components/scheduler/scheduler-utils.ts
// Mobile-only additions: buildTimelineRange, getBarLeft, getBarWidth

import {
  addDays,
  differenceInCalendarDays,
  isValid,
  parse,
  parseISO,
  startOfDay,
} from 'date-fns';
import type { ScheduleTask } from '../../types/api';

/**
 * Parse a task date string to a Date, or null.
 * Supports ISO 8601 and common dd-MM-* formats used in DPR data entry.
 * Always use this — never `new Date(string)` directly.
 */
export function parseTaskDate(value?: string | null): Date | null {
  if (!value) return null;

  const iso = parseISO(value);
  if (isValid(iso)) return startOfDay(iso);

  const patterns = [
    'dd-MM-yy',
    'dd/MM/yy',
    'dd-MM-yyyy',
    'dd/MM/yyyy',
    'dd MMM yy',
    'dd MMM yyyy',
    'MMM dd, yyyy',
  ];
  for (const pattern of patterns) {
    const parsed = parse(value, pattern, new Date());
    if (isValid(parsed)) return startOfDay(parsed);
  }

  const fallback = new Date(value);
  return isValid(fallback) ? startOfDay(fallback) : null;
}

/**
 * Compute the min/max date range across all tasks.
 * Adds a 7-day buffer on each side for visual breathing room.
 */
export function buildTimelineRange(tasks: ScheduleTask[]): {
  start: Date;
  end: Date;
  dayCount: number;
} {
  const dates: Date[] = [];
  for (const task of tasks) {
    const s = parseTaskDate(task.scheduled_start);
    const e = parseTaskDate(task.scheduled_finish);
    if (s) dates.push(s);
    if (e) dates.push(e);
  }

  if (dates.length === 0) {
    const base = startOfDay(new Date());
    const end = addDays(base, 90);
    return { start: base, end, dayCount: 91 };
  }

  const min = dates.reduce((acc, d) => (d < acc ? d : acc), dates[0]);
  const max = dates.reduce((acc, d) => (d > acc ? d : acc), dates[0]);

  const start = addDays(startOfDay(min), -7);
  const end = addDays(startOfDay(max), 7);
  const dayCount = differenceInCalendarDays(end, start) + 1;

  return { start, end, dayCount };
}

/**
 * Returns the x-offset (in pixels) of a task bar from the left edge of the timeline.
 */
export function getBarLeft(
  task: ScheduleTask,
  dayWidth: number,
  timelineStart: Date
): number {
  const start = parseTaskDate(task.scheduled_start);
  if (!start) return 0;
  return differenceInCalendarDays(start, timelineStart) * dayWidth;
}

/**
 * Returns the pixel width of a task bar.
 * Minimum 2px so zero-duration tasks remain visible.
 */
export function getBarWidth(task: ScheduleTask, dayWidth: number): number {
  const dur = task.duration > 0 ? task.duration : 1;
  return Math.max(2, dur * dayWidth);
}
