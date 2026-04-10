import { renderHook, act, waitFor } from '@testing-library/react-native';
import { useSchedulerData } from '../../hooks/useSchedulerData';
import { schedulerApi } from '../../services/apiClient';
import type { ScheduleTask } from '../../types/api';

jest.mock('../../services/apiClient', () => ({
  schedulerApi: {
    loadSchedule: jest.fn(),
  },
}));

const mockLoadSchedule = schedulerApi.loadSchedule as jest.Mock;

const mockTasks: ScheduleTask[] = [
  {
    task_id: 't1',
    name: 'Foundation',
    start_date: '2025-01-01',
    end_date: '2025-01-15',
    duration_days: 15,
    status: 'not_started',
    is_critical: true,
  },
];

describe('useSchedulerData', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('starts in loading state and resolves to tasks', async () => {
    mockLoadSchedule.mockResolvedValueOnce({
      tasks: mockTasks,
      project_start: '2025-01-01',
    });

    const { result } = renderHook(() => useSchedulerData('proj-1'));

    // Initial state — loading
    expect(result.current.loading).toBe(true);
    expect(result.current.tasks).toHaveLength(0);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.tasks[0].name).toBe('Foundation');
    expect(result.current.error).toBeNull();
    expect(result.current.projectStart).toBe('2025-01-01');
  });

  it('sets error on API failure', async () => {
    mockLoadSchedule.mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useSchedulerData('proj-2'));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Network error');
    expect(result.current.tasks).toHaveLength(0);
  });

  it('does not fetch when projectId is null', () => {
    renderHook(() => useSchedulerData(null));
    expect(mockLoadSchedule).not.toHaveBeenCalled();
  });

  it('refetch() triggers a new API call', async () => {
    mockLoadSchedule.mockResolvedValue({
      tasks: mockTasks,
      project_start: '2025-01-01',
    });

    const { result } = renderHook(() => useSchedulerData('proj-3'));

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockLoadSchedule).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refetch();
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(mockLoadSchedule).toHaveBeenCalledTimes(2);
  });
});
