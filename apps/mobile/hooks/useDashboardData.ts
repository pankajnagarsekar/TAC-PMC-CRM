import { useState, useEffect, useCallback } from 'react';
import { ProjectDashboardData } from '../types/api';
import apiClient from '../services/apiClient';

interface UseDashboardDataOptions {
  projectId: string | null | undefined;
  refetchInterval?: number;
}

interface UseDashboardDataResult {
  data: ProjectDashboardData | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useDashboardData({ projectId, refetchInterval }: UseDashboardDataOptions): UseDashboardDataResult {
  const [data, setData] = useState<ProjectDashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchDashboard = useCallback(async () => {
    if (!projectId) {
      setData(null);
      setError(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Call reporting dashboard endpoint
      const response = await apiClient.reporting.getDashboard(projectId);
      setData(response);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      setError(error);
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchDashboard();

    let interval: ReturnType<typeof setInterval> | undefined;
    if (refetchInterval && refetchInterval > 0) {
      interval = setInterval(fetchDashboard, refetchInterval);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [projectId, refetchInterval, fetchDashboard]);

  return {
    data,
    loading,
    error,
    refetch: fetchDashboard,
  };
}
