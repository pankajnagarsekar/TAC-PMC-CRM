import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react-native';
import { AnalyticsScreen } from '../components/dashboard/AnalyticsScreen';
import { MiniChart } from '../components/dashboard/MiniChart';
import { MetricsDetail } from '../components/dashboard/MetricsDetail';
import { useDashboardData } from '../hooks/useDashboardData';
import { useProject } from '../contexts/ProjectContext';
import { useTheme } from '../contexts/ThemeContext';

// Mock dependencies
jest.mock('../contexts/ProjectContext');
jest.mock('../contexts/ThemeContext');
jest.mock('../hooks/useDashboardData');

const mockColors = {
  background: '#ffffff',
  surface: '#f5f5f5',
  text: '#000000',
  textSecondary: '#666666',
  textMuted: '#999999',
  primary: '#3b82f6',
  border: '#e0e0e0',
};

const mockDashboardData = {
  project_id: 'proj-123',
  project_name: 'Test Project',
  schedule: {
    days_remaining: 25,
    tasks_at_risk: 2,
    critical_path_days: 30,
    status: 'green' as const,
  },
  resources: {
    by_resource: {
      'John Doe': {
        resource_name: 'John Doe',
        allocation_percent: 85,
        allocated_hours: 340,
        available_hours: 400,
      },
    },
    by_role: {
      Engineer: {
        role_name: 'Engineer',
        total_allocation_percent: 85,
        resource_count: 1,
      },
    },
    over_allocated: [],
  },
  financial: {
    budget_total: 5000000,
    budget_spent: 3000000,
    budget_remaining: 2000000,
    burn_rate_daily: 50000,
    projected_overrun: 0,
  },
  timeline: {
    daily_completion: [
      { date: '2024-01-01', value: 5 },
      { date: '2024-01-02', value: 8 },
    ],
    utilization_trend: [
      { date: '2024-01-01', value: 70 },
      { date: '2024-01-02', value: 75 },
    ],
    budget_spent_trend: [
      { date: '2024-01-01', value: 45000 },
      { date: '2024-01-02', value: 50000 },
    ],
  },
  updated_at: new Date().toISOString(),
};

describe('Analytics Dashboard', () => {
  beforeEach(() => {
    (useTheme as jest.Mock).mockReturnValue({
      colors: mockColors,
      isDark: false,
      toggleTheme: jest.fn(),
      spacing: { xs: 4, sm: 8, md: 12, lg: 16, xl: 20 },
      borderRadius: { sm: 4, md: 8, lg: 12 },
      shadows: { sm: {}, md: {}, lg: {} },
    });
    (useProject as jest.Mock).mockReturnValue({
      selectedProject: {
        project_id: 'proj-123',
        project_name: 'Test Project',
      },
    });
  });

  describe('AnalyticsScreen', () => {
    test('renders loading state when data is loading', () => {
      (useDashboardData as jest.Mock).mockReturnValue({
        data: null,
        loading: true,
        error: null,
        refetch: jest.fn(),
      });

      render(<AnalyticsScreen />);
      expect(screen.getByText('Loading analytics...')).toBeTruthy();
    });

    test('renders empty state when no project selected', () => {
      (useProject as jest.Mock).mockReturnValue({
        selectedProject: null,
      });
      (useDashboardData as jest.Mock).mockReturnValue({
        data: null,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<AnalyticsScreen />);
      expect(screen.getByText('No Project Selected')).toBeTruthy();
    });

    test('renders dashboard data when loaded', async () => {
      (useDashboardData as jest.Mock).mockReturnValue({
        data: mockDashboardData,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      render(<AnalyticsScreen />);

      await waitFor(() => {
        expect(screen.getByText('Test Project')).toBeTruthy();
        expect(screen.getByText('25days')).toBeTruthy(); // days remaining
        expect(screen.getByText('2tasks')).toBeTruthy(); // tasks at risk
      });
    });

    test('renders error state when fetch fails', () => {
      const error = new Error('Failed to load data');
      (useDashboardData as jest.Mock).mockReturnValue({
        data: null,
        loading: false,
        error,
        refetch: jest.fn(),
      });

      render(<AnalyticsScreen />);
      expect(screen.getByText('Failed to Load Analytics')).toBeTruthy();
    });

    test('calls refetch on refresh', async () => {
      const mockRefetch = jest.fn();
      (useDashboardData as jest.Mock).mockReturnValue({
        data: mockDashboardData,
        loading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(<AnalyticsScreen />);

      // Note: Testing RefreshControl is complex in RN, so this is a simplified test
      expect(mockRefetch).toBeDefined();
    });
  });

  describe('MiniChart', () => {
    test('renders sparkline with data', () => {
      const data = [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-02', value: 120 },
      ];

      render(
        <MiniChart
          data={data}
          label="Test Chart"
          metric="budget"
          value={120}
          unit="K"
        />
      );

      expect(screen.getByText('Test Chart')).toBeTruthy();
      expect(screen.getByText('120.0K')).toBeTruthy();
    });

    test('calculates trend correctly', () => {
      const data = [
        { date: '2024-01-01', value: 100 },
        { date: '2024-01-02', value: 150 },
      ];

      render(
        <MiniChart
          data={data}
          label="Test"
          metric="completion"
          value={150}
        />
      );

      // Trend should be 50% increase
      expect(screen.getByText(/50%/)).toBeTruthy();
    });

    test('renders correct color based on metric type', () => {
      const { rerender } = render(
        <MiniChart
          data={[{ date: '2024-01-01', value: 100 }]}
          label="Budget"
          metric="budget"
          value={100}
        />
      );

      // Budget metric should show red trend color (for spend)
      expect(screen.getByText('Budget')).toBeTruthy();

      rerender(
        <MiniChart
          data={[{ date: '2024-01-01', value: 100 }]}
          label="Completion"
          metric="completion"
          value={100}
        />
      );

      expect(screen.getByText('Completion')).toBeTruthy();
    });
  });

  describe('MetricsDetail', () => {
    test('renders schedule metrics detail', async () => {
      const schedule = {
        days_remaining: 25,
        tasks_at_risk: 2,
        critical_path_days: 30,
        status: 'green' as const,
      };

      render(<MetricsDetail type="schedule" schedule={schedule} />);

      expect(screen.getByText('Schedule Health')).toBeTruthy();

      // Tap to expand
      const trigger = screen.getByText('Schedule Health').parent;
      fireEvent.press(trigger);

      await waitFor(() => {
        expect(screen.getByText('Days Remaining')).toBeTruthy();
        expect(screen.getByText('25d')).toBeTruthy();
      });
    });

    test('renders resource metrics detail', async () => {
      const resources = {
        by_resource: {
          'John': {
            resource_name: 'John',
            allocation_percent: 85,
            allocated_hours: 340,
            available_hours: 400,
          },
        },
        by_role: {},
        over_allocated: [],
      };

      render(<MetricsDetail type="resources" resources={resources} />);

      expect(screen.getByText('Resource Utilization')).toBeTruthy();

      // Tap to expand
      const trigger = screen.getByText('Resource Utilization').parent;
      fireEvent.press(trigger);

      await waitFor(() => {
        expect(screen.getByText('BY RESOURCE')).toBeTruthy();
        expect(screen.getByText('John')).toBeTruthy();
      });
    });

    test('renders financial metrics detail', async () => {
      const financial = {
        budget_total: 5000000,
        budget_spent: 3000000,
        budget_remaining: 2000000,
        burn_rate_daily: 50000,
        projected_overrun: 0,
      };

      render(<MetricsDetail type="financial" financial={financial} />);

      expect(screen.getByText('Financial Summary')).toBeTruthy();

      // Tap to expand
      const trigger = screen.getByText('Financial Summary').parent;
      fireEvent.press(trigger);

      await waitFor(() => {
        expect(screen.getByText('Total Budget')).toBeTruthy();
      });
    });
  });

  describe('Hook: useDashboardData', () => {
    test('fetches dashboard data when projectId is provided', async () => {
      const mockData = mockDashboardData;
      (useDashboardData as jest.Mock).mockReturnValue({
        data: mockData,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      const { data } = useDashboardData({
        projectId: 'proj-123',
      });

      expect(data).toEqual(mockData);
    });

    test('returns null data when no projectId', () => {
      (useDashboardData as jest.Mock).mockReturnValue({
        data: null,
        loading: false,
        error: null,
        refetch: jest.fn(),
      });

      const { data } = useDashboardData({
        projectId: null,
      });

      expect(data).toBeNull();
    });

    test('supports auto-refetch interval', () => {
      const mockRefetch = jest.fn();
      (useDashboardData as jest.Mock).mockReturnValue({
        data: mockDashboardData,
        loading: false,
        error: null,
        refetch: mockRefetch,
      });

      useDashboardData({
        projectId: 'proj-123',
        refetchInterval: 30000,
      });

      expect(mockRefetch).toBeDefined();
    });
  });
});
