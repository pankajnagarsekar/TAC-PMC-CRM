import { ScheduleTaskStatus } from "./schedule.types";

export type AnalyticsChartType =
  | 's_curve'
  | 'planned_vs_actual'
  | 'task_status'
  | 'milestone_trend'
  | 'critical_tasks'
  | 'schedule_variance'
  | 'cost_overview'
  | 'resource_load'
  | 'delay_trend'
  | 'cash_flow'
  | 'earned_value'
  | 'completion_forecast';

export interface AnalyticsFilters {
  dateRange: 'this_month' | 'next_30' | 'quarter' | 'full_project' | 'custom';
  customDateStart?: string;
  customDateEnd?: string;
  timeBucket: 'daily' | 'weekly' | 'monthly';
  viewLevel: 'project' | 'phase' | 'task_group' | 'wbs';
  statusFilter?: string[];
  criticalOnly: boolean;
  milestonesOnly: boolean;
  costEnabled: boolean;
  assigneeFilter?: string[];
  vendorFilter?: string[];       // filter by vendor name from WO/task data
  departmentFilter?: string[];   // filter by department/WBS-first-segment grouping
  baselineVersion?: number;
  comparePrevious: boolean;
}

export interface AnalyticsKPI {
  overallProgress: number;           // %
  plannedVsActualVariance: number;   // days or %
  totalTasks: number;
  completedTasks: number;
  delayedTasks: number;
  criticalTasks: number;
  budgetUsedPercent: number | null;  // null = data unavailable
  forecastFinishDate: string | null;
  spi: number | null;
  cpi: number | null;
}

export interface ChartConfig {
  type: AnalyticsChartType;
  label: string;
  description: string;
  icon: string;  // lucide icon name
  requiresCost: boolean;  // grayed out if no cost data
  requiresBaseline: boolean;
}

export interface AnalyticsInsight {
  id: string;
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'critical';
}
