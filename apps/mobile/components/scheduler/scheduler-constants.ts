// SCHEDULER CONSTANTS
// Mobile-optimized values (tighter than web)

import type { ScheduleTaskStatus } from '../../types/api';

export const ROW_HEIGHT = 48;
export const DAY_WIDTH_INITIAL = 32;
export const DAY_WIDTH_MIN = 12;
export const DAY_WIDTH_MAX = 120;
export const HEADER_HEIGHT = 50;

// Raw hex fills — react-native-svg needs raw values, not Tailwind classes
export const STATUS_COLORS: Record<ScheduleTaskStatus, string> = {
  draft: '#64748b',
  not_started: '#0ea5e9',
  in_progress: '#f59e0b',
  completed: '#10b981',
  closed: '#f43f5e',
};

export const STATUS_LABELS: Record<ScheduleTaskStatus, string> = {
  draft: 'Draft',
  not_started: 'Not Started',
  in_progress: 'In Progress',
  completed: 'Completed',
  closed: 'Closed',
};

export const CRITICAL_COLOR = '#ef4444';
export const BAR_COLOR_DEFAULT = '#0ea5e9';
export const GRID_LINE_COLOR = 'rgba(255, 255, 255, 0.05)';
export const LABEL_COLOR = 'rgba(255, 255, 255, 0.7)';
