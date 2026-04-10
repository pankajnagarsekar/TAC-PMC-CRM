import { parseTaskDate, buildTimelineRange, getBarLeft, getBarWidth } from '../../components/scheduler/scheduler-utils';
import type { ScheduleTask } from '../../types/api';

const makeTask = (overrides: Partial<ScheduleTask>): ScheduleTask => ({
  task_id: 't1',
  name: 'Task 1',
  start_date: '2025-01-01',
  end_date: '2025-01-10',
  duration_days: 10,
  status: 'not_started',
  is_critical: false,
  ...overrides,
});

describe('parseTaskDate', () => {
  it('parses ISO date string', () => {
    const d = parseTaskDate('2025-06-15');
    expect(d).not.toBeNull();
    expect(d!.getFullYear()).toBe(2025);
    expect(d!.getMonth()).toBe(5); // 0-indexed
    expect(d!.getDate()).toBe(15);
  });

  it('parses dd-MM-yyyy format', () => {
    const d = parseTaskDate('15-06-2025');
    expect(d).not.toBeNull();
    expect(d!.getFullYear()).toBe(2025);
  });

  it('returns null for null input', () => {
    expect(parseTaskDate(null)).toBeNull();
  });

  it('returns null for undefined input', () => {
    expect(parseTaskDate(undefined)).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(parseTaskDate('')).toBeNull();
  });
});

describe('buildTimelineRange', () => {
  it('returns correct dayCount for 3-task fixture', () => {
    const tasks: ScheduleTask[] = [
      makeTask({ start_date: '2025-01-01', end_date: '2025-01-10', duration_days: 10 }),
      makeTask({ task_id: 't2', start_date: '2025-01-05', end_date: '2025-01-20', duration_days: 16 }),
      makeTask({ task_id: 't3', start_date: '2025-01-15', end_date: '2025-02-01', duration_days: 18 }),
    ];
    const { start, end, dayCount } = buildTimelineRange(tasks);
    // start = 2025-01-01 - 7 days = 2024-12-25
    // end = 2025-02-01 + 7 days = 2025-02-08
    expect(dayCount).toBeGreaterThan(0);
    expect(end.getTime()).toBeGreaterThan(start.getTime());
    // 2024-12-25 to 2025-02-08 = 45 days + 1 = 46 dayCount
    expect(dayCount).toBe(46);
  });

  it('returns fallback range for empty tasks', () => {
    const { dayCount } = buildTimelineRange([]);
    expect(dayCount).toBe(91);
  });
});

describe('getBarLeft', () => {
  it('returns 0 when task starts at timelineStart', () => {
    const timelineStart = new Date('2025-01-01');
    const task = makeTask({ start_date: '2025-01-01' });
    expect(getBarLeft(task, 24, timelineStart)).toBe(0);
  });

  it('returns dayWidth * offset for later start', () => {
    const timelineStart = new Date('2025-01-01');
    const task = makeTask({ start_date: '2025-01-11' });
    // 10 days offset * 24px = 240
    expect(getBarLeft(task, 24, timelineStart)).toBe(240);
  });
});

describe('getBarWidth', () => {
  it('returns duration_days * dayWidth', () => {
    const task = makeTask({ duration_days: 5 });
    expect(getBarWidth(task, 24)).toBe(120);
  });

  it('returns minimum 2px for zero-duration tasks', () => {
    const task = makeTask({ duration_days: 0 });
    // duration_days 0 → uses 1 (minimum), 1 * 1 = 1, but Math.max(2, 1) = 2
    expect(getBarWidth(task, 1)).toBe(2);
  });
});
