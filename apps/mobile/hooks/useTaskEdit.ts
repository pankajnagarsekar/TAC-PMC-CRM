// useTaskEdit hook
// Manages task editing state, validation, and API calls with optimistic updates

import { useState, useCallback } from 'react';
import { schedulerApi } from '../services/apiClient';
import type { ScheduleTask, ScheduleTaskStatus } from '../types/api';

export interface TaskEditState {
  name?: string;
  status?: ScheduleTaskStatus;
  duration_days?: number;
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
    name: task.name,
    status: task.status,
    duration_days: task.duration_days,
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const validate = (): boolean => {
    const errors: Record<string, string> = {};

    if (!editState.name?.trim()) {
      errors.name = 'Task name is required';
    }

    if (!editState.status) {
      errors.status = 'Status is required';
    }

    if (!editState.duration_days || editState.duration_days <= 0) {
      errors.duration_days = 'Duration must be greater than 0';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

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

        // Only include changed fields
        if (editState.name !== task.name) payload.name = editState.name;
        if (editState.status !== task.status) payload.status = editState.status;
        if (editState.duration_days !== task.duration_days) payload.duration_days = editState.duration_days;

        if (Object.keys(payload).length === 0) {
          // No changes
          return true;
        }

        await schedulerApi.updateTask(projectId, task.task_id, payload);
        return true;
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to save task';
        setSaveError(errorMessage);
        // Rollback to original state
        setEditStateInternal({
          name: task.name,
          status: task.status,
          duration_days: task.duration_days,
        });
        return false;
      } finally {
        setIsSaving(false);
      }
    },
    [editState, task]
  );

  const reset = useCallback(() => {
    setEditStateInternal({
      name: task.name,
      status: task.status,
      duration_days: task.duration_days,
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
