/**
 * useUndoRedo Hook
 *
 * Custom hook for managing undo/redo operations on the scheduler.
 * Handles API calls, state management, and keyboard shortcuts.
 *
 * Task #16: Frontend Integration for Undo/Redo System
 */

import { useCallback, useEffect, useState } from 'react';
import useSWR from 'swr';
import apiClient from '@/lib/api';
import type {
  HistoryEntry,
  StackInfo,
  UndoRedoResponse
} from '@/types/schedule.types';

/**
 * Custom hook for undo/redo operations
 *
 * @param projectId - Project ID to manage history for
 * @param onTasksChanged - Callback when tasks are updated via undo/redo
 */
export function useUndoRedo(
  projectId: string | null,
  onTasksChanged?: (tasks: any[]) => void
) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch history and stack info
  const historyUrl = projectId
    ? `/api/v1/scheduler/${projectId}/history`
    : null;

  const stackInfoUrl = projectId
    ? `/api/v1/scheduler/${projectId}/history/stack-info`
    : null;

  const {
    data: historyData,
    mutate: mutateHistory,
    isLoading: historyLoading,
  } = useSWR<{ data: { history: HistoryEntry[] } }>(historyUrl, null, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });

  const {
    data: stackInfoData,
    mutate: mutateStackInfo,
  } = useSWR<{ data: StackInfo }>(stackInfoUrl, null, {
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });

  const history = historyData?.data?.history || [];
  const stackInfo = stackInfoData?.data || null;

  /**
   * Perform undo operation
   */
  const undo = useCallback(async () => {
    if (!projectId || !stackInfo?.can_undo) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post<UndoRedoResponse>(
        `/v1/scheduler/${projectId}/undo`
      );

      if (response.data?.data?.tasks) {
        onTasksChanged?.(response.data.data.tasks);
      }

      // Refresh history and stack info
      await Promise.all([mutateHistory(), mutateStackInfo()]);
    } catch (err: any) {
      const message = err?.response?.data?.message || 'Undo failed';
      setError(message);
      console.error('Undo error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, stackInfo?.can_undo, onTasksChanged, mutateHistory, mutateStackInfo]);

  /**
   * Perform redo operation
   */
  const redo = useCallback(async () => {
    if (!projectId || !stackInfo?.can_redo) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post<UndoRedoResponse>(
        `/v1/scheduler/${projectId}/redo`
      );

      if (response.data?.data?.tasks) {
        onTasksChanged?.(response.data.data.tasks);
      }

      // Refresh history and stack info
      await Promise.all([mutateHistory(), mutateStackInfo()]);
    } catch (err: any) {
      const message = err?.response?.data?.message || 'Redo failed';
      setError(message);
      console.error('Redo error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, stackInfo?.can_redo, onTasksChanged, mutateHistory, mutateStackInfo]);

  /**
   * Restore to a specific version in history
   */
  const restore = useCallback(
    async (entryId: string) => {
      if (!projectId) return;

      setIsLoading(true);
      setError(null);

      try {
        const response = await apiClient.post<UndoRedoResponse>(
          `/v1/scheduler/${projectId}/history/${entryId}/restore`
        );

        if (response.data?.data?.tasks) {
          onTasksChanged?.(response.data.data.tasks);
        }

        // Refresh history and stack info
        await Promise.all([mutateHistory(), mutateStackInfo()]);
      } catch (err: any) {
        const message = err?.response?.data?.message || 'Restore failed';
        setError(message);
        console.error('Restore error:', err);
      } finally {
        setIsLoading(false);
      }
    },
    [projectId, onTasksChanged, mutateHistory, mutateStackInfo]
  );

  /**
   * Load history (manual refresh)
   */
  const loadHistory = useCallback(async () => {
    await Promise.all([mutateHistory(), mutateStackInfo()]);
  }, [mutateHistory, mutateStackInfo]);

  /**
   * Setup keyboard shortcuts
   */
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check if the user is in an input field
      const target = event.target as HTMLElement;
      const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';

      if (isInput) return;

      // Ctrl+Z for undo (Cmd+Z on Mac)
      if ((event.ctrlKey || event.metaKey) && event.key === 'z' && !event.shiftKey) {
        event.preventDefault();
        undo();
      }

      // Ctrl+Shift+Z or Ctrl+Y for redo (Cmd+Shift+Z on Mac)
      if (
        ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'z') ||
        ((event.ctrlKey || event.metaKey) && event.key === 'y')
      ) {
        event.preventDefault();
        redo();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [undo, redo]);

  return {
    // State
    history,
    stackInfo,
    isLoading: isLoading || historyLoading,
    error,

    // Methods
    undo,
    redo,
    restore,
    loadHistory,

    // Helpers
    canUndo: stackInfo?.can_undo ?? false,
    canRedo: stackInfo?.can_redo ?? false,
    currentPosition: stackInfo?.current_position ?? -1,
    totalEntries: stackInfo?.total_entries ?? 0,
  };
}

export default useUndoRedo;
