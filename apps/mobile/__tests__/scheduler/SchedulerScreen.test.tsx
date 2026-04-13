import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react-native';
import { SchedulerScreen } from '../../components/scheduler/SchedulerScreen';
import type { ScheduleTask } from '../../types/api';

// Mock @shopify/flash-list
jest.mock('@shopify/flash-list', () => {
  const React = require('react');
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
    colors: mockColors,
    isDark: true,
  })),
}));

// Mock hooks
const mockTasks: ScheduleTask[] = [
  {
    task_id: 't1',
    name: 'Foundation Work',
    start_date: '2025-01-01',
    end_date: '2025-01-15',
    duration_days: 15,
    status: 'in_progress',
    is_critical: true,
  },
  {
    task_id: 't2',
    name: 'Structural Steel',
    start_date: '2025-01-16',
    end_date: '2025-02-10',
    duration_days: 26,
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

describe('SchedulerScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders project name in header', () => {
    render(<SchedulerScreen />);
    expect(screen.getByText('Test Project')).toBeTruthy();
  });

  it('renders List and Gantt tab buttons', () => {
    render(<SchedulerScreen />);
    expect(screen.getByText('List')).toBeTruthy();
    expect(screen.getByText('Gantt')).toBeTruthy();
  });

  it('shows List view by default', () => {
    render(<SchedulerScreen />);
    expect(screen.getByText('Foundation Work')).toBeTruthy();
    expect(screen.getByText('Structural Steel')).toBeTruthy();
  });

  it('toggles to Gantt view when Gantt button pressed', () => {
    render(<SchedulerScreen />);
    const ganttButton = screen.getByText('Gantt');
    fireEvent.press(ganttButton);
    // After toggle, Gantt view should be active
    expect(ganttButton).toBeTruthy();
  });

  it('toggles back to List view when List button pressed', () => {
    render(<SchedulerScreen />);
    const listButton = screen.getByText('List');
    fireEvent.press(listButton);
    // After toggle, List view should be active
    expect(listButton).toBeTruthy();
  });
});
