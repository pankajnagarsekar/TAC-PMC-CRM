import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react-native';
import { TaskForm } from '../../components/scheduler/TaskForm';
import type { ScheduleTask } from '../../types/api';

// Mock theme context
jest.mock('../../contexts/ThemeContext', () => ({
  useTheme: jest.fn(() => ({
    colors: {
      text: '#f1f5f9',
      surface: '#1e293b',
      border: '#1e293b',
      textMuted: '#64748b',
    },
  })),
}));

const mockTask: ScheduleTask = {
  task_id: 't1',
  name: 'Foundation Work',
  start_date: '2025-01-01',
  end_date: '2025-01-15',
  duration_days: 15,
  status: 'in_progress',
  is_critical: true,
};

describe('TaskForm', () => {
  it('renders form fields with task data', () => {
    const mockOnChange = jest.fn();
    render(
      <TaskForm
        task={mockTask}
        editState={{
          name: mockTask.name,
          status: mockTask.status,
          duration_days: mockTask.duration_days,
        }}
        validationErrors={{}}
        onEditStateChange={mockOnChange}
      />
    );

    expect(screen.getByDisplayValue('Foundation Work')).toBeTruthy();
    expect(screen.getByDisplayValue('15')).toBeTruthy();
  });

  it('calls onEditStateChange when name changes', () => {
    const mockOnChange = jest.fn();
    render(
      <TaskForm
        task={mockTask}
        editState={{ name: mockTask.name, status: mockTask.status, duration_days: mockTask.duration_days }}
        validationErrors={{}}
        onEditStateChange={mockOnChange}
      />
    );

    const nameInput = screen.getByDisplayValue('Foundation Work');
    fireEvent.changeText(nameInput, 'Updated Name');

    expect(mockOnChange).toHaveBeenCalledWith({ name: 'Updated Name' });
  });

  it('displays validation errors', () => {
    render(
      <TaskForm
        task={mockTask}
        editState={{ name: '', status: mockTask.status, duration_days: 0 }}
        validationErrors={{
          name: 'Task name is required',
          duration_days: 'Duration must be greater than 0',
        }}
        onEditStateChange={jest.fn()}
      />
    );

    expect(screen.getByText('Task name is required')).toBeTruthy();
    expect(screen.getByText('Duration must be greater than 0')).toBeTruthy();
  });

  it('calls onEditStateChange when duration changes', () => {
    const mockOnChange = jest.fn();
    render(
      <TaskForm
        task={mockTask}
        editState={{ name: mockTask.name, status: mockTask.status, duration_days: mockTask.duration_days }}
        validationErrors={{}}
        onEditStateChange={mockOnChange}
      />
    );

    const durationInput = screen.getByDisplayValue('15');
    fireEvent.changeText(durationInput, '20');

    expect(mockOnChange).toHaveBeenCalledWith({ duration_days: 20 });
  });
});
