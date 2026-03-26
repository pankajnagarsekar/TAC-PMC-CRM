import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";

import { schedulerApi } from "@/lib/api";
import type {
  ScheduleCalculationResponse,
  ScheduleChangeRequest,
  ScheduleStoreState,
  ScheduleTask,
  ScheduleTaskMap,
  UndoStackEntry,
} from "@/types/schedule.types";

const CALCULATION_DEBOUNCE_MS = 300;
let pendingRequest: ScheduleChangeRequest | null = null;
let calculationTimer: ReturnType<typeof setTimeout> | null = null;

const buildTaskMap = (tasks: ScheduleTask[]): ScheduleTaskMap => {
  return (tasks || []).reduce<ScheduleTaskMap>((acc, task) => {
    if (task && task.task_id) {
      acc[task.task_id] = { ...task };
    }
    return acc;
  }, {});
};

const buildTaskOrder = (tasks: ScheduleTask[]) =>
  (tasks || [])
    .filter(t => t && t.task_id)
    .map((task) => task.task_id);

const buildDependencyGraph = (tasks: ScheduleTask[]) => {
  const graph: Record<string, { predecessors: string[]; successors: string[] }> = {};
  tasks.forEach((task) => {
    graph[task.task_id] = graph[task.task_id] ?? { predecessors: [], successors: [] };
    task.predecessors?.forEach((pred) => {
      graph[task.task_id].predecessors.push(pred.task_id);
      graph[pred.task_id] = graph[pred.task_id] ?? { predecessors: [], successors: [] };
      graph[pred.task_id].successors.push(task.task_id);
    });
  });
  return graph;
};

const buildOptimisticPatch = (
  changes: ScheduleChangeRequest["changes"]
): Partial<ScheduleTask> => {
  const patch: Partial<ScheduleTask> = {};

  if (changes.scheduled_start !== undefined) patch.scheduled_start = changes.scheduled_start;
  if (changes.task_name !== undefined && changes.task_name !== null) patch.task_name = changes.task_name;
  if (changes.scheduled_finish !== undefined) patch.scheduled_finish = changes.scheduled_finish;
  if (changes.scheduled_duration !== undefined) patch.scheduled_duration = changes.scheduled_duration ?? undefined;
  if (changes.percent_complete !== undefined) patch.percent_complete = changes.percent_complete ?? undefined;
  if (changes.actual_start !== undefined) patch.actual_start = changes.actual_start;
  if (changes.actual_finish !== undefined) patch.actual_finish = changes.actual_finish;
  if (changes.predecessors !== undefined) patch.predecessors = changes.predecessors ?? undefined;
  if (changes.assigned_resources !== undefined) patch.assigned_resources = changes.assigned_resources ?? undefined;
  if (changes.task_mode !== undefined && changes.task_mode !== null) patch.task_mode = changes.task_mode;
  if (changes.task_status !== undefined && changes.task_status !== null) patch.task_status = changes.task_status;

  return patch;
};

import { toast } from "sonner";

const executeCalculationRequest = async (
  request: ScheduleChangeRequest,
  set: any,
  get: () => ScheduleStoreState
) => {
  const idempotencyKey = uuidv4();
  try {
    const response: ScheduleCalculationResponse = await schedulerApi.calculateChange(
      request.project_id,
      request,
      idempotencyKey
    );
    get().reconcileWithEngine(response);
  } catch (error: any) {
    const isConflict = error?.response?.status === 409;
    const responseData = error?.response?.data;

    set({
      pendingCalculation: false,
      calculationError:
        error?.response?.data?.detail?.message ?? error?.message ?? "Calculation failed",
    });

    if (isConflict && responseData?.tasks) {
      toast.warning("Schedule conflict resolved by server truth.");
      get().reconcileWithEngine(responseData);
    } else {
      get().rollbackToUndo();
    }
  }
};

const buildChanges = (changes: ScheduleChangeRequest["changes"]) => {
  const allowedFields: Array<keyof ScheduleChangeRequest["changes"]> = [
    "scheduled_start",
    "task_name",
    "wbs_code",
    "external_ref_id",
    "parent_id",
    "is_milestone",
    "scheduled_finish",
    "scheduled_duration",
    "percent_complete",
    "actual_start",
    "actual_finish",
    "predecessors",
    "assigned_resources",
    "task_mode",
    "task_status",
  ];

  return allowedFields.reduce((acc, field) => {
    if (Object.prototype.hasOwnProperty.call(changes, field)) {
      (acc as any)[field] = changes[field];
    }
    return acc;
  }, {} as ScheduleChangeRequest["changes"]);
};

const clearPendingCalculation = () => {
  pendingRequest = null;
  if (calculationTimer) {
    clearTimeout(calculationTimer);
    calculationTimer = null;
  }
};

export const useScheduleStore = create<ScheduleStoreState>()((set, get) => {
  const dispatchCalculation = () => {
    const request = pendingRequest;
    pendingRequest = null;
    calculationTimer = null;
    if (!request) {
      set({ pendingCalculation: false });
      return;
    }
    set({ pendingCalculation: true, calculationError: null });
    executeCalculationRequest(request, set, get);
  };

  return {
    taskMap: {},
    taskOrder: [],
    dependencyGraph: {},
    activeFilters: {},
    selectedTasks: new Set(),
    systemState: null,
    undoStack: [],
    pendingCalculation: false,
    lastConfirmedVersion: null,
    calculationError: null,
    collapsedParents: new Set(),
    comparisonData: null,
    selectedBaselineA: null,
    selectedBaselineB: null,

    loadSchedule: (response) => {
      clearPendingCalculation();
      set({
        taskMap: buildTaskMap(response.tasks),
        taskOrder: buildTaskOrder(response.tasks),
        dependencyGraph: buildDependencyGraph(response.tasks),
        systemState: response.system_state,
        lastConfirmedVersion: response.calculation_version,
        pendingCalculation: false,
        calculationError: null,
        undoStack: [],
        selectedTasks: new Set(),
      });
    },

    reconcileWithEngine: (response) => {
      clearPendingCalculation();

      const nextTaskMap = buildTaskMap(response.tasks);
      const nextTaskOrder = buildTaskOrder(response.tasks);
      const nextGraph = buildDependencyGraph(response.tasks);

      // Handle ID mapping for selections (e.g. task-1 -> mongo_id)
      const nextSelectedTasks = new Set<string>();
      const currentTaskMap = get().taskMap;
      const idMap = new Map<string, string>(); // external_ref_id -> new_task_id

      response.tasks.forEach((task) => {
        if (task.external_ref_id) {
          idMap.set(task.external_ref_id, task.task_id);
        }
      });

      get().selectedTasks.forEach((oldId) => {
        const task = currentTaskMap[oldId];
        if (task?.external_ref_id && idMap.has(task.external_ref_id)) {
          nextSelectedTasks.add(idMap.get(task.external_ref_id)!);
        } else if (nextTaskMap[oldId]) {
          nextSelectedTasks.add(oldId);
        }
      });

      set({
        taskMap: nextTaskMap,
        taskOrder: nextTaskOrder,
        dependencyGraph: nextGraph,
        selectedTasks: nextSelectedTasks,
        systemState: response.system_state,
        lastConfirmedVersion: response.calculation_version,
        pendingCalculation: false,
        calculationError: null,
      });
    },

    createDraftTask: (projectId) => {
      const existingIds = Object.keys(get().taskMap);
      const nextNumericId = existingIds.reduce((max, taskId) => {
        const match = taskId.match(/(\d+)/g);
        if (!match) return max;
        const value = Number(match[match.length - 1]);
        return Number.isFinite(value) ? Math.max(max, value) : max;
      }, 0);

      const task_id = `task-${nextNumericId + 1}`;
      const draftTask: ScheduleTask = {
        task_id,
        project_id: projectId,
        external_ref_id: task_id, // Linkage ID
        task_name: "New Task",
        task_status: "draft",
        task_mode: "Auto",
        percent_complete: 0,
        scheduled_start: null,
        scheduled_finish: null,
        scheduled_duration: 1,
        predecessors: [],
        assigned_resources: [],
        is_milestone: false,
        is_summary: false,
        summary_type: "auto",
        version: 1,
      };

      set((state) => ({
        taskMap: { ...state.taskMap, [task_id]: draftTask },
        taskOrder: [...state.taskOrder, task_id],
        dependencyGraph: {
          ...state.dependencyGraph,
          [task_id]: state.dependencyGraph[task_id] ?? { predecessors: [], successors: [] },
        },
      }));

      // Auto-trigger calculation to persist the new task
      get().queueCalculation({
        project_id: projectId,
        task_id: task_id,
        changes: { ...draftTask } as any,
        version: 1,
        trigger_source: "api",
      });

      return draftTask;
    },

    removeTask: (taskId) => {
      set((state) => {
        if (!state.taskMap[taskId]) {
          return {};
        }

        const nextTaskMap = { ...state.taskMap };
        delete nextTaskMap[taskId];
        const nextGraph: typeof state.dependencyGraph = {};
        Object.entries(state.dependencyGraph).forEach(([id, node]) => {
          if (id === taskId) return;
          nextGraph[id] = {
            predecessors: node.predecessors.filter((pred) => pred !== taskId),
            successors: node.successors.filter((succ) => succ !== taskId),
          };
        });

        return {
          taskMap: nextTaskMap,
          taskOrder: state.taskOrder.filter((id) => id !== taskId),
          dependencyGraph: nextGraph,
          selectedTasks: new Set([...state.selectedTasks].filter((id) => id !== taskId)),
        };
      });
    },

    queueCalculation: (payload) => {
      const previousTask = get().taskMap[payload.task_id];
      if (!previousTask) {
        return;
      }

      const previousClone = { ...previousTask };
      const optimistic = { ...previousClone, ...buildOptimisticPatch(payload.changes) };

      set((state) => ({
        taskMap: { ...state.taskMap, [payload.task_id]: optimistic },
        undoStack: [
          {
            taskIds: [payload.task_id],
            previousValues: [previousClone],
            optimisticValues: [optimistic],
            timestamp: Date.now(),
          },
          ...state.undoStack,
        ].slice(0, 50),
        pendingCalculation: true,
        calculationError: null,
      }));

      const projectId =
        payload.project_id ?? previousTask.project_id ?? "";
      pendingRequest = {
        ...payload,
        project_id: projectId,
        version: payload.version ?? previousTask.version ?? 0,
        changes: buildChanges(payload.changes),
      };
      if (calculationTimer) {
        clearTimeout(calculationTimer);
      }
      calculationTimer = setTimeout(dispatchCalculation, CALCULATION_DEBOUNCE_MS);
    },

    rollbackToUndo: () => {
      set((state) => {
        if (state.undoStack.length === 0) {
          return { pendingCalculation: false };
        }

        const [entry, ...rest] = state.undoStack;
        const updatedMap = { ...state.taskMap };

        entry.taskIds.forEach((taskId, idx) => {
          updatedMap[taskId] = {
            ...updatedMap[taskId],
            ...entry.previousValues[idx],
          };
        });

        return {
          taskMap: updatedMap,
          undoStack: rest,
          pendingCalculation: false,
        };
      });
    },

    undo: () => {
      const entry = get().undoStack[0];
      if (!entry) return;

      set((state) => {
        const updatedMap = { ...state.taskMap };
        entry.taskIds.forEach((taskId, idx) => {
          updatedMap[taskId] = {
            ...updatedMap[taskId],
            ...entry.previousValues[idx],
          };
        });

        return {
          taskMap: updatedMap,
          undoStack: state.undoStack.slice(1),
          pendingCalculation: true,
        };
      });

      const changeRequest: ScheduleChangeRequest = {
        task_id: entry.taskIds[0],
        project_id: get().taskMap[entry.taskIds[0]]?.project_id ?? "",
        version: get().taskMap[entry.taskIds[0]]?.version ?? 0,
        changes: buildChanges(entry.previousValues[0] ?? {}),
        trigger_source: "grid_edit",
      };
      if (Object.keys(changeRequest.changes).length > 0 && changeRequest.project_id) {
        executeCalculationRequest(changeRequest, set, get);
      } else {
        set({ pendingCalculation: false });
      }
    },

    selectTask: (taskId) => {
      set((state) => {
        const setCopy = new Set(state.selectedTasks);
        setCopy.add(taskId);
        return { selectedTasks: setCopy };
      });
    },

    deselectTask: (taskId) => {
      set((state) => {
        const setCopy = new Set(state.selectedTasks);
        setCopy.delete(taskId);
        return { selectedTasks: setCopy };
      });
    },

    openTask: (taskId) => {
      set((state) => {
        const selected = taskId ? new Set([taskId]) : new Set<string>();
        return { selectedTasks: selected };
      });
    },

    toggleParentCollapse: (taskId) => {
      set((state) => {
        const next = new Set(state.collapsedParents);
        if (next.has(taskId)) {
          next.delete(taskId);
        } else {
          next.add(taskId);
        }
        return { collapsedParents: next };
      });
    },

    fetchBaselineComparison: async (projectId: string, baselineA: number, baselineB?: number) => {
      set({ pendingCalculation: true });
      try {
        const results = await schedulerApi.compareBaselines(projectId, baselineA, baselineB);
        set({
          comparisonData: results,
          selectedBaselineA: baselineA,
          selectedBaselineB: baselineB ?? null,
          pendingCalculation: false
        });
      } catch (err: any) {
        set({ pendingCalculation: false });
        toast.error("Failed to fetch baseline comparison.");
      }
    },

    clearComparison: () => {
      set({
        comparisonData: null,
        selectedBaselineA: null,
        selectedBaselineB: null
      });
    },

  };
});
