import React from 'react';
import { ActivityIndicator } from 'react-native';
import { render, screen, fireEvent } from '@testing-library/react-native';
import SchedulerScreen from '../../components/scheduler/SchedulerScreen';
import { useSchedulerData } from '../../hooks/useSchedulerData';
import type { ScheduleTask } from '../../types/api';

// Mock @shopify/flash-list
jest.mock('@shopify/flash-list', () => {
  const { View } = require('react-native');
  return {
    FlashList: ({ data, renderItem }: { data: unknown[]; renderItem: (info: { item: unknown }) => React.ReactNode }) => (
      <View>
        {data.map((item, index) => (
          <View key={index}>{renderItem({ item })}</View>
        ))}
      </View>
    ),
  };
});

// Mock expo-router
jest.mock('expo-router', () => ({
  Redirect: ({ href }: { href: string }) => null,
  useRouter: jest.fn(() => ({
    push: jest.fn(),
  })),
}));

// Mock react-native-gesture-handler
jest.mock('react-native-gesture-handler', () => ({
  GestureHandlerRootView: ({ children }: { children: React.ReactNode }) => children,
  Gesture: {
    Pan: jest.fn(() => ({
      activeOffsetX: jest.fn().mockReturnThis(),
      failOffsetY: jest.fn().mockReturnThis(),
      onChange: jest.fn().mockReturnThis(),
    })),
    Pinch: jest.fn(() => ({
      onChange: jest.fn().mockReturnThis(),
    })),
    Simultaneous: jest.fn((pan, pinch) => ({ pan, pinch })),
  },
  GestureDetector: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock react-native-reanimated
jest.mock('react-native-reanimated', () => ({
  ...jest.requireActual('react-native-reanimated'),
  useSharedValue: (val: number) => ({ value: val }),
  useAnimatedStyle: (callback: () => any) => callback(),
  useAnimatedProps: (callback: () => any) => callback(),
  createAnimatedComponent: (component: any) => component,
}));

// Mock scheduler components to avoid internal dependency issues
jest.mock('../../components/scheduler/SchedulerGantt', () => {
  const { View, Text } = require('react-native');
  return {
    SchedulerGantt: ({ tasks }: { tasks: ScheduleTask[] }) => (
      <View testID="scheduler-gantt">
        <Text>Gantt View ({tasks.length} tasks)</Text>
      </View>
    ),
  };
});

jest.mock('../../components/scheduler/SchedulerList', () => {
  const { View, Text } = require('react-native');
  return {
    SchedulerList: ({ tasks }: { tasks: ScheduleTask[] }) => (
      <View testID="scheduler-list">
        {tasks.map((t: ScheduleTask) => (
          <Text key={t.task_id}>{t.task_name}</Text>
        ))}
        {tasks.length === 0 && <Text>No scheduled tasks yet</Text>}
      </View>
    ),
  };
});

// Mock contexts
const mockProject = { project_id: 'p1', project_name: 'Test Project' };
const mockColors = {
  background: '#0f172a',
  text: '#f1f5f9',
  textSecondary: '#94a3b8',
  border: '#1e293b',
  primary: '#2563eb',
  textMuted: '#64748b',
  surface: '#1e293b',
};

jest.mock('../../contexts/ProjectContext', () => ({
  useProject: jest.fn(() => ({
    selectedProject: mockProject,
  })),
}));

jest.mock('../../contexts/ThemeContext', () => ({
  useTheme: jest.fn(() => ({
    colors: {
      ...mockColors,
      textInverse: '#ffffff',
    },
    typography: {
      heading2: { fontSize: 24, fontWeight: 'bold' },
      overline: { fontSize: 10, letterSpacing: 1 },
    },
    isDark: true,
  })),
}));

// Mock hooks
const mockTasks: ScheduleTask[] = [
  {
    task_id: 't1',
    task_name: 'Foundation Work',
    scheduled_start: '2025-01-01',
    scheduled_finish: '2025-01-15',
    duration: 15,
    status: 'in_progress',
    is_critical: true,
  },
  {
    task_id: 't2',
    task_name: 'Structural Steel',
    scheduled_start: '2025-01-16',
    scheduled_finish: '2025-02-10',
    duration: 26,
    status: 'not_started',
    is_critical: false,
  },
];

jest.mock('../../hooks/useSchedulerData', () => ({
  useSchedulerData: jest.fn((projectId: string | null) => ({
    tasks: projectId ? mockTasks : [],
    projectStart: '2025-01-01',
    loading: false,
    error: null,
    refetch: jest.fn(),
  })),
}));

const mockUseSchedulerData = useSchedulerData as jest.Mock;

describe('SchedulerScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Default mock implementation
    mockUseSchedulerData.mockReturnValue({
      tasks: mockTasks,
      projectStart: '2025-01-01',
      loading: false,
      error: null,
      refetch: jest.fn(),
    });
  });

  it('renders project name and task list in list view', () => {
    render(<SchedulerScreen />);
    expect(screen.getByText('Test Project')).toBeTruthy();
    expect(screen.getByText('Foundation Work')).toBeTruthy();
    expect(screen.getByText('Structural Steel')).toBeTruthy();
  });

  it('toggles between list and gantt view modes', () => {
    render(<SchedulerScreen />);

    // Initially in list view
    expect(screen.getByTestId('scheduler-list')).toBeTruthy();
    expect(screen.queryByTestId('scheduler-gantt')).toBeFalsy();

    // Press Gantt button
    fireEvent.press(screen.getByTestId('view-mode-gantt'));
    expect(screen.getByTestId('scheduler-gantt')).toBeTruthy();
    expect(screen.queryByTestId('scheduler-list')).toBeFalsy();

    // Press List button
    fireEvent.press(screen.getByTestId('view-mode-list'));
    expect(screen.getByTestId('scheduler-list')).toBeTruthy();
    expect(screen.queryByTestId('scheduler-gantt')).toBeFalsy();
  });

  it('shows loading state while fetching data', () => {
    mockUseSchedulerData.mockReturnValue({
      tasks: [],
      projectStart: null,
      loading: true,
      error: null,
      refetch: jest.fn(),
    });

    const { UNSAFE_getByType } = render(<SchedulerScreen />);
    expect(UNSAFE_getByType(ActivityIndicator)).toBeTruthy();
    expect(screen.queryByTestId('scheduler-list')).toBeFalsy();
  });

  it('shows error message with retry button and calls refetch', () => {
    const mockRefetch = jest.fn();
    mockUseSchedulerData.mockReturnValue({
      tasks: [],
      projectStart: null,
      loading: false,
      error: 'Failed to load tasks',
      refetch: mockRefetch,
    });

    render(<SchedulerScreen />);
    expect(screen.getByText('Failed to load tasks')).toBeTruthy();

    const retryButton = screen.getByTestId('retry-button');
    expect(retryButton).toBeTruthy();
    fireEvent.press(retryButton);
    expect(mockRefetch).toHaveBeenCalledTimes(1);
  });

  it('renders tasks in both list and gantt modes', () => {
    render(<SchedulerScreen />);

    // List mode should render tasks (both names appear in the list view)
    expect(screen.getByTestId('scheduler-list')).toBeTruthy();
    expect(screen.getByText('Foundation Work')).toBeTruthy();
    expect(screen.getByText('Structural Steel')).toBeTruthy();

    // Switch to Gantt mode
    fireEvent.press(screen.getByTestId('view-mode-gantt'));
    expect(screen.getByTestId('scheduler-gantt')).toBeTruthy();
    expect(screen.queryByTestId('scheduler-list')).toBeFalsy();
  });
});
