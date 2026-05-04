import React from 'react';
import { render, screen } from '@testing-library/react-native';
import { SchedulerList } from '../../components/scheduler/SchedulerList';
import { ThemeProvider } from '../../contexts/ThemeContext';
import type { ScheduleTask } from '../../types/api';

// Mock @shopify/flash-list to render children as a plain View to avoid native measurement
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

const fixture3: ScheduleTask[] = [
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
  {
    task_id: 't3',
    task_name: 'Roof Tiling',
    scheduled_start: '2025-02-11',
    scheduled_finish: '2025-02-28',
    duration: 18,
    status: 'not_started',
    is_critical: false,
  },
];

describe('SchedulerList', () => {
  it('renders all 3 task names', () => {
    render(<ThemeProvider><SchedulerList tasks={fixture3} /></ThemeProvider>);
    expect(screen.getByText('Foundation Work')).toBeTruthy();
    expect(screen.getByText('Structural Steel')).toBeTruthy();
    expect(screen.getByText('Roof Tiling')).toBeTruthy();
  });

  it('critical task row has red left border style applied', () => {
    const { getByTestId } = render(<ThemeProvider><SchedulerList tasks={fixture3} /></ThemeProvider>);
    const criticalRow = getByTestId('critical-task-row');
    const style = Array.isArray(criticalRow.props.style)
      ? Object.assign({}, ...criticalRow.props.style)
      : criticalRow.props.style;
    expect(style.borderLeftColor).toBe('#ef4444');
    expect(style.borderLeftWidth).toBe(3);
  });

  it('shows empty state when no tasks', () => {
    render(<ThemeProvider><SchedulerList tasks={[]} /></ThemeProvider>);
    expect(screen.getByText('No scheduled tasks yet')).toBeTruthy();
  });
});
