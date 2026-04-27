import React from 'react';
import { render, screen } from '@testing-library/react-native';
import { View } from 'react-native';
import { SchedulerList } from '../../components/scheduler/SchedulerList';
import { ThemeProvider } from '../../contexts/ThemeContext';
import type { ScheduleTask } from '../../types/api';

// Mock @shopify/flash-list to render children as a plain View to avoid native measurement
jest.mock('@shopify/flash-list', () => ({
  FlashList: ({ data, renderItem }: { data: unknown[]; renderItem: (info: { item: unknown }) => React.ReactNode }) => (
    <View>
      {data.map((item, index) => (
        <View key={index}>{renderItem({ item })}</View>
      ))}
    </View>
  ),
}));

const fixture3: ScheduleTask[] = [
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
  {
    task_id: 't3',
    name: 'Roof Tiling',
    start_date: '2025-02-11',
    end_date: '2025-02-28',
    duration_days: 18,
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
