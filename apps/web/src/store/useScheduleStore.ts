import { create } from "zustand";
import { toast } from "sonner";

import { schedulerApi } from "@/lib/api";
import {
  ScheduleCalculationResponse,
  ScheduleChangeRequest,
  ScheduleStoreState,
  ScheduleTask,
  ScheduleTaskMap,
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

const executeCalculationRequest = async (
  request: ScheduleChangeRequest,
  set: (state: Partial<ScheduleStoreState>) => void,
  get: () => ScheduleStoreState
) => {
  try {
    const { taskMap } = get();
    const tasks = Object.values(taskMap);

    // S-BUG #3: Use calculateChange for granular edits to avoid massive payloads
    // Check if it's a granular edit (single task_id present in request)
    const isGranular = request.task_id && !request.trigger_source?.includes("import");

    let response;
    const idempotencyKey = `calc-${Date.now()}`;

    if (isGranular) {
      response = await schedulerApi.calculateChange(
        request.project_id,
        request,
        idempotencyKey
      );
    } else {
      // Full-schedule fallback (imports, task deletes, undo).
      // S-BUG #4: projectStart must be stable — use the project's own scheduled_start
      // if available, to prevent a single task drag from shifting the entire schedule.
      const toISODate = (dateStr: string | null | undefined): string | null => {
        if (!dateStr) return null;
        if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return dateStr.split("T")[0];
        const parsed = new Date(dateStr);
        return isNaN(parsed.getTime()) ? null : parsed.toISOString().split("T")[0];
      };

      // Priority: (1) explicit project start stored on the task's project,
      // (2) the earliest non-null scheduled_start across all tasks (legacy fallback).
      // The project start is stored on tasks as project.scheduled_start via the load response.
      const firstTask = tasks[0];
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const projectRecord = (firstTask as any)?.project;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const stableStart =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        toISODate((projectRecord as any)?.scheduled_start) ||
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        toISODate((firstTask as any)?.project_scheduled_start);

      let projectStart: string;
      if (stableStart) {
        projectStart = stableStart;
      } else {
        // Legacy: derive from tasks — least-bad option when project record is unavailable
        const starts = tasks
          .map((t) => toISODate(t.scheduled_start))
          .filter(Boolean)
          .sort() as string[];
        projectStart = starts.length > 0 ? starts[0] : new Date().toISOString().split("T")[0];
      }

      response = await schedulerApi.calculate(
        request.project_id,
        tasks,
        projectStart
      );
    }

    // S-BUG #7: Handle explicit backend errors (like circular dependencies)
    const backendError = (response as { error?: string }).error;
    if (backendError) {
      set({
        pendingCalculation: false,
        calculationError: backendError
      });
      get().rollbackToUndo();
      toast.error(`Engine Error: ${backendError}`);
      return;
    }

    get().reconcileWithEngine({
      ...response,
      project_id: request.project_id,
      calculation_version: response.calculation_version || "fallback_version",
      system_state: response.system_state || "active",
      schedule_version: response.schedule_version || 1
    });

    // AUTO-SAVE: Persist changes to DB immediately after engine reconciliation
    try {
      const { taskMap } = get();
      const updatedTasks = Object.values(taskMap);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const projectStart = response.project_start || (updatedTasks[0] as any)?.project_scheduled_start;

      await schedulerApi.save(
        request.project_id,
        updatedTasks,
        projectStart || "",
        0 // totalCost placeholder
      );
      console.log("SCHEDULER_STORE: Auto-save successful");
    } catch (saveError) {
      console.error("SCHEDULER_STORE: Auto-save failed", saveError);
      // We don't toast here to avoid UI noise, the calculation result is already reconciled
    }
  } catch (error: unknown) {
    const err = error as {
      response?: {
        status?: number;
        data?: ScheduleCalculationResponse & { detail?: { message?: string } }
      };
      message?: string
    };
    const isConflict = err?.response?.status === 409;
    const responseData = err?.response?.data;

    set({
      pendingCalculation: false,
      calculationError: (() => {
        const detail = err?.response?.data?.detail;
        if (typeof detail === "string") return detail;
        if (typeof detail === "object" && detail?.message) return detail.message;
        return err?.message ?? "Calculation failed";
      })(),
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
      (acc as Record<string, unknown>)[field] = changes[field];
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
      const decoratedTasks = (response.tasks || []).map(t => ({
        ...t,
        project_id: t.project_id || response.project_id,
        // S-BUG #4: Cache project's canonical start date on every task so
        // the full-recalc path can use a stable projectStart anchor
        project_scheduled_start: (response as any).project_start || t.project_scheduled_start,
      }));

      set({
        taskMap: buildTaskMap(decoratedTasks),
        taskOrder: buildTaskOrder(decoratedTasks),
        dependencyGraph: buildDependencyGraph(decoratedTasks),
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

      const decoratedTasks = (response.tasks || []).map(t => ({
        ...t,
        project_id: t.project_id || response.project_id
      }));

      const nextTaskMap = buildTaskMap(decoratedTasks);
      const nextTaskOrder = buildTaskOrder(decoratedTasks);
      const nextGraph = buildDependencyGraph(decoratedTasks);

      // Handle ID mapping for selections (e.g. task-1 -> mongo_id)
      const nextSelectedTasks = new Set<string>();
      const currentTaskMap = get().taskMap;
      const idMap = new Map<string, string>(); // external_ref_id -> new_task_id

      decoratedTasks.forEach((task) => {
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
        changes: { ...draftTask } as ScheduleChangeRequest["changes"],
        version: 1,
        trigger_source: "api",
      });

      return draftTask;
    },

    removeTask: async (taskId) => {
      const task = get().taskMap[taskId];
      if (!task) return;

      const projectId = task.project_id;

      // Optimistic removal
      set((state) => {
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

      try {
        await schedulerApi.deleteTask(projectId, taskId);
        toast.success("Task deleted permanently.");

        // Trigger a recalculation of the remaining schedule to fix dependencies
        const { taskMap } = get();
        const tasks = Object.values(taskMap);
        if (tasks.length === 0) return;
        try {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          await schedulerApi.save(tasks[0].project_id, tasks, (tasks[0] as any).project_scheduled_start || "", 0);
          toast.success("Schedule committed to database.");
        } catch (e) {
          console.error("Failed to commit schedule after delete", e);
        }

        get().queueCalculation({
          project_id: projectId,
          task_id: tasks[0]?.task_id || "resync",
          changes: {},
          version: 1,
          trigger_source: "task_delete"
        });
      } catch (err) {
        console.error("Failed to delete task:", err);
        toast.error("Failed to delete task from server. Reverting local change.");
        // We should ideally reload the schedule here
        const currentProject = get().taskMap[Object.keys(get().taskMap)[0]]?.project_id;
        if (currentProject) {
          const data = await schedulerApi.load(currentProject);
          get().loadSchedule(data);
        }
      }
    },

    queueCalculation: (payload) => {
      const state = get();
      const currentTask = state.taskMap[payload.task_id];
      if (!currentTask) {
        return;
      }

      const previousClone = { ...currentTask };
      const optimistic = { ...previousClone, ...buildOptimisticPatch(payload.changes) };

      // S-BUG #6: Optimistic Parent Rollup
      const updatedMap = { ...state.taskMap, [payload.task_id]: optimistic };
      if (optimistic.parent_id && updatedMap[optimistic.parent_id]) {
        const parent = updatedMap[optimistic.parent_id];
        if (parent.summary_type === "auto") {
          const siblings = Object.values(updatedMap).filter(t => t.parent_id === optimistic.parent_id);
          const starts = siblings.map(s => s.scheduled_start).filter(Boolean) as string[];
          const finishes = siblings.map(s => s.scheduled_finish).filter(Boolean) as string[];

          if (starts.length > 0) {
            parent.scheduled_start = starts.sort()[0];
          }
          if (finishes.length > 0) {
            parent.scheduled_finish = finishes.sort().reverse()[0];
          }

          // Progress Rollup
          const durations = siblings.map(s => s.scheduled_duration ?? 0);
          const totalDuration = durations.reduce((a, b) => a + b, 0);
          if (totalDuration > 0) {
            const weightedSum = siblings.reduce((acc, s) => {
              return acc + ((s.scheduled_duration ?? 0) * (s.percent_complete ?? 0));
            }, 0);
            parent.percent_complete = Math.round(weightedSum / totalDuration);
          }
        }
      }

      set((state) => ({
        taskMap: updatedMap,
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

      const projectId = payload.project_id || currentTask.project_id;
      if (!projectId) {
        console.warn("SCHEDULER_STORE: Missing project_id for calculation. Aborting request.", payload);
        set({ pendingCalculation: false });
        return;
      }

      pendingRequest = {
        ...payload,
        project_id: projectId,
        version: payload.version ?? currentTask.version ?? 0,
        changes: buildChanges(payload.changes),
      };

      if (calculationTimer) {
        clearTimeout(calculationTimer);
      }
      calculationTimer = setTimeout(() => dispatchCalculation(), CALCULATION_DEBOUNCE_MS);
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

      const currentItem = get().taskMap[entry.taskIds[0]];
      if (!currentItem) return;

      set((state) => {
        const updatedMap = { ...state.taskMap };
        entry.taskIds.forEach((taskId, idx) => {
          if (updatedMap[taskId]) {
            updatedMap[taskId] = {
              ...updatedMap[taskId],
              ...entry.previousValues[idx],
            };
          }
        });

        return {
          taskMap: updatedMap,
          undoStack: state.undoStack.slice(1),
          pendingCalculation: true,
        };
      });

      const changeRequest: ScheduleChangeRequest = {
        task_id: entry.taskIds[0],
        project_id: currentItem.project_id || "",
        version: currentItem.version ?? 0,
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
      set(() => {
        const selected = taskId ? new Set([taskId]) : new Set<string>();
        return { selectedTasks: selected };
      });
    },

    toggleParentCollapse: (taskId) => {
      set((_state) => {
        const next = new Set(get().collapsedParents);
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
      } catch {
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
