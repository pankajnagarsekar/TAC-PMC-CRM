// useTaskEdit hook
// Manages task editing state, validation, and API calls with optimistic updates

import { useState, useCallback } from 'react';
import { schedulerApi } from '../services/apiClient';
import type { ScheduleTask, ScheduleTaskStatus } from '../types/api';

export interface TaskEditState {
  task_name?: string;
  status?: ScheduleTaskStatus;
  duration?: number;
}

export interface UseTaskEditResult {
  originalTask: ScheduleTask;
  editState: TaskEditState;
  setEditState: (updates: Partial<TaskEditState>) => void;
  validationErrors: Record<string, string>;
  isSaving: boolean;
  saveError: string | null;
  save: (projectId: string) => Promise<boolean>;
  reset: () => void;
}

export function useTaskEdit(task: ScheduleTask): UseTaskEditResult {
  const [editState, setEditStateInternal] = useState<TaskEditState>({
    task_name: task.task_name,
    status: task.status,
    duration: task.duration,
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const validate = useCallback((): boolean => {
    const errors: Record<string, string> = {};

    if (!editState.task_name?.trim()) {
      errors.task_name = 'Task name is required';
    }

    if (!editState.status) {
      errors.status = 'Status is required';
    }

    if (editState.duration === undefined || editState.duration <= 0) {
      errors.duration = 'Duration must be greater than 0';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  }, [editState]);

  const setEditState = useCallback((updates: Partial<TaskEditState>) => {
    setEditStateInternal((prev) => ({ ...prev, ...updates }));
    // Clear validation errors when user edits
    setSaveError(null);
  }, []);

  const save = useCallback(
    async (projectId: string): Promise<boolean> => {
      if (!validate()) {
        return false;
      }

      setIsSaving(true);
      setSaveError(null);

      try {
        const payload: Record<string, unknown> = {};

        // Only include changed fields - match backend expected keys (task_name, status, duration)
        if (editState.task_name !== task.task_name) payload.task_name = editState.task_name;
        if (editState.status !== task.status) payload.status = editState.status;
        if (editState.duration !== task.duration) payload.duration = editState.duration;

        if (Object.keys(payload).length === 0) {
          // No changes
          return true;
        }

        await schedulerApi.updateTask(projectId, task.task_id, payload);
        return true;
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to save task';
        setSaveError(errorMessage);
        // Rollback to original state
        setEditStateInternal({
          task_name: task.task_name,
          status: task.status,
          duration: task.duration,
        });
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [editState, task, validate]
  );

  const reset = useCallback(() => {
    setEditStateInternal({
      task_name: task.task_name,
      status: task.status,
      duration: task.duration,
    });
    setValidationErrors({});
    setSaveError(null);
  }, [task]);

  return {
    originalTask: task,
    editState,
    setEditState,
    validationErrors,
    isSaving,
    saveError,
    save,
    reset,
  };
}
