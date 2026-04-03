export type DependencyType = "FS" | "SS" | "FF" | "SF";
export type ConstraintType =
  | "ASAP"
  | "ALAP"
  | "SNET"
  | "SNLT"
  | "FNET"
  | "FNLT"
  | "MSO"
  | "MFO";

export type ActionItem = {
  task_name: string;
  assignee: string | null;
  deadline: string | null;
};

export type MomResult = {
  action_items: ActionItem[];
  suggested_duration_days: number;
  confidence_score: number;
};

export type ChangeSource =
  | "gantt_drag"
  | "kanban_drop"
  | "grid_edit"
  | "drawer_edit"
  | "import"
  | "api"
  | "ai_suggestion"
  | "task_delete";

export type CostVarianceFlag = "on_budget" | "overrun" | "underrun";
export type ScheduleTaskStatus =
  | "draft"
  | "not_started"
  | "in_progress"
  | "completed"
  | "closed";

export type SchedulePredecessor = {
  task_id: string;
  project_id: string | null;
  type: DependencyType;
  lag_days?: number;
  is_external?: boolean;
  strength?: "hard" | "soft";
};

export type ScheduleTask = {
  task_id: string;
  project_id: string;
  task_name: string;
  task_status?: ScheduleTaskStatus;
  wbs_code?: string;
  external_ref_id?: string;
  parent_id?: string | null;
  is_summary?: boolean;
  summary_type?: "auto" | "manual";
  task_mode?: "Auto" | "Manual";
  version?: number;
  constraint_type?: ConstraintType;
  constraint_date?: string | null;
  deadline?: string | null;
  scheduled_start?: string | null;
  scheduled_finish?: string | null;
  scheduled_duration?: number | null;
  baseline_start?: string | null;
  baseline_finish?: string | null;
  baseline_cost?: number | null;
  actual_start?: string | null;
  actual_finish?: string | null;
  percent_complete?: number;
  assigned_resources?: string[];
  is_milestone?: boolean;
  predecessors?: SchedulePredecessor[];
  successors?: string[];
  early_start?: string | null;
  early_finish?: string | null;
  late_start?: string | null;
  late_finish?: string | null;
  total_slack?: number;
  is_critical?: boolean;
  weightage_percent?: number;
  wo_value?: number;
  wo_retention_value?: number;
  payment_value?: number;
  cost_variance?: number;
  cost_variance_flag?: CostVarianceFlag;
  ai_suggested_duration?: number | null;
  ai_confidence_score?: number | null;
  ai_status_flag?: string | null;
  calc_reason?: string;
  [key: string]: unknown;
};

export type ScheduleTaskMap = Record<string, ScheduleTask>;

export type DependencyGraph = Record<
  string,
  {
    predecessors: string[];
    successors: string[];
  }
>;

export type ScheduleCalculationResponse = {
  project_id: string;
  calculation_version: string;
  schedule_version: number;
  system_state: "draft" | "initialized" | "active" | "locked";
  calculated_at: string;
  status: "success" | "partial_failure" | "failure";
  errors?: { task_id: string; error: string }[];
  warnings?: { type: string; detail: string }[];
  critical_path: string[];
  tasks: ScheduleTask[];
  verification?: Record<string, unknown>;
};

export type ScheduleChangeRequest = {
  project_id: string;
  task_id: string;
  changes: {
    task_name?: string | null;
    wbs_code?: string | null;
    external_ref_id?: string | null;
    parent_id?: string | null;
    is_milestone?: boolean | null;
    scheduled_start?: string | null;
    scheduled_finish?: string | null;
    scheduled_duration?: number | null;
    percent_complete?: number | null;
    actual_start?: string | null;
    actual_finish?: string | null;
    predecessors?: SchedulePredecessor[] | null;
    assigned_resources?: string[] | null;
    task_mode?: "Auto" | "Manual" | null;
    task_status?: ScheduleTaskStatus | null;
    ai_suggested_duration?: number | null;
    ai_confidence_score?: number | null;
    ai_status_flag?: string | null;
  };
  version: number;
  trigger_source: ChangeSource;
};

export type UndoStackEntry = {
  taskIds: string[];
  previousValues: Partial<ScheduleTask>[];
  optimisticValues: Partial<ScheduleTask>[];
  timestamp: number;
};

export type ActiveFilters = {
  searchTerm?: string;
  column?: string;
  value?: string | number;
};

export type BaselineComparisonResult = {
  task_id: string;
  wbs_code: string;
  task_name: string;
  baseline_a_start: string | null;
  baseline_a_finish: string | null;
  baseline_b_start: string | null;
  baseline_b_finish: string | null;
  schedule_variance_days: number;
  baseline_a_cost: number;
  baseline_b_cost: number;
  cost_variance_percent: number;
};

export interface ScheduleStoreState {
  taskMap: ScheduleTaskMap;
  taskOrder: string[];
  dependencyGraph: DependencyGraph;
  activeFilters: ActiveFilters;
  selectedTasks: Set<string>;
  systemState: ScheduleCalculationResponse["system_state"] | null;
  undoStack: UndoStackEntry[];
  pendingCalculation: boolean;
  lastConfirmedVersion: string | null;
  calculationError: string | null;
  collapsedParents: Set<string>;

  // Baseline Comparison
  comparisonData: BaselineComparisonResult[] | null;
  selectedBaselineA: number | null;
  selectedBaselineB: number | null;

  loadSchedule: (payload: ScheduleCalculationResponse) => void;
  reconcileWithEngine: (response: ScheduleCalculationResponse) => void;
  queueCalculation: (payload: ScheduleChangeRequest) => void;
  createDraftTask: (projectId: string) => ScheduleTask;
  removeTask: (taskId: string) => void;
  openTask: (taskId: string | null) => void;
  rollbackToUndo: () => void;
  undo: () => void;
  selectTask: (taskId: string) => void;
  deselectTask: (taskId: string) => void;
  toggleParentCollapse: (taskId: string) => void;

  // Comparison Actions
  fetchBaselineComparison: (projectId: string, baselineA: number, baselineB?: number) => Promise<void>;
  clearComparison: () => void;
}
