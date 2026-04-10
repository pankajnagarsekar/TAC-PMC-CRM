// useSchedulerData hook
// Fetches schedule data from schedulerApi and manages loading/error state.

import { useState, useEffect, useCallback } from 'react';
import { schedulerApi } from '../services/apiClient';
import type { ScheduleTask } from '../types/api';

export interface UseSchedulerDataResult {
  tasks: ScheduleTask[];
  projectStart: string | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useSchedulerData(projectId: string | null): UseSchedulerDataResult {
  const [tasks, setTasks] = useState<ScheduleTask[]>([]);
  const [projectStart, setProjectStart] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!projectId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    schedulerApi
      .loadSchedule(projectId)
      .then((data) => {
        if (cancelled) return;
        setTasks(data.tasks ?? []);
        setProjectStart(data.project_start ?? null);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setError(err.message || 'Failed to load schedule');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [projectId, refreshKey]);

  const refetch = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  return { tasks, projectStart, loading, error, refetch };
}
