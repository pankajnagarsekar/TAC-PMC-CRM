// TaskForm — reusable form for editing task details
// Input fields: name (TextInput), status (Picker), duration (TextInput)

import React from 'react';
import { View, Text, TextInput, StyleSheet } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import type { ScheduleTask, ScheduleTaskStatus } from '../../types/api';
import { useTheme, ThemeContextType } from '../../contexts/ThemeContext';
import { STATUS_LABELS } from './scheduler-constants';

interface TaskEditState {
  name?: string;
  status?: ScheduleTaskStatus;
  duration_days?: number;
}

interface TaskFormProps {
  task: ScheduleTask;
  editState: TaskEditState;
  validationErrors: Record<string, string>;
  onEditStateChange: (updates: TaskEditState) => void;
}

const STATUS_OPTIONS: ScheduleTaskStatus[] = [
  'draft',
  'not_started',
  'in_progress',
  'completed',
  'closed',
];

export function TaskForm({
  task,
  editState,
  validationErrors,
  onEditStateChange,
}: TaskFormProps) {
  const { colors } = useTheme();
  const dynamicStyles = createDynamicStyles(colors);

  return (
    <View style={styles.form}>
      {/* Task Name */}
      <FormField label="Task Name" error={validationErrors.name} colors={colors}>
        <TextInput
          style={[styles.input, dynamicStyles.input, validationErrors.name && styles.inputError]}
          placeholder="Enter task name"
          placeholderTextColor={colors.textMuted}
          value={editState.name ?? task.name}
          onChangeText={(value) => onEditStateChange({ name: value })}
          editable
        />
      </FormField>

      {/* Status */}
      <FormField label="Status" error={validationErrors.status} colors={colors}>
        <View style={[styles.pickerContainer, dynamicStyles.pickerContainer]}>
          <Picker
            selectedValue={editState.status ?? task.status}
            onValueChange={(value: ScheduleTaskStatus) => onEditStateChange({ status: value })}
            style={[styles.picker, { color: colors.text }]}
          >
            {STATUS_OPTIONS.map((status) => (
              <Picker.Item
                key={status}
                label={STATUS_LABELS[status] ?? status}
                value={status}
              />
            ))}
          </Picker>
        </View>
      </FormField>

      {/* Duration */}
      <FormField
        label="Duration (days)"
        error={validationErrors.duration_days}
        colors={colors}
      >
        <TextInput
          style={[styles.input, dynamicStyles.input, validationErrors.duration_days && styles.inputError]}
          placeholder="Enter duration in days"
          placeholderTextColor={colors.textMuted}
          value={String(editState.duration_days ?? task.duration_days)}
          onChangeText={(value) => onEditStateChange({ duration_days: parseInt(value, 10) || 0 })}
          keyboardType="number-pad"
          editable
        />
      </FormField>
    </View>
  );
}

interface FormFieldProps {
  label: string;
  error?: string;
  children: React.ReactNode;
  colors: ThemeContextType['colors'];
}

function FormField({ label, error, children, colors }: FormFieldProps) {
  return (
    <View style={styles.fieldContainer}>
      <Text style={[styles.label, { color: colors.text }]}>{label}</Text>
      {children}
      {error && <Text style={styles.errorText}>{error}</Text>}
    </View>
  );
}

function createDynamicStyles(colors: ThemeContextType['colors']) {
  return StyleSheet.create({
    input: {
      backgroundColor: colors.surface,
      borderColor: colors.border,
      color: colors.text,
    },
    pickerContainer: {
      backgroundColor: colors.surface,
      borderColor: colors.border,
      borderWidth: 1,
      borderRadius: 6,
    },
  });
}

const styles = StyleSheet.create({
  form: {
    gap: 16,
  },
  fieldContainer: {
    gap: 6,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
  },
  input: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderRadius: 6,
    fontSize: 14,
  },
  inputError: {
    borderColor: '#ef4444',
  },
  errorText: {
    color: '#ef4444',
    fontSize: 12,
    fontWeight: '500',
  },
  pickerContainer: {
    overflow: 'hidden',
    borderWidth: 1,
    borderRadius: 6,
  },
  picker: {
    height: 50,
  },
});

export default TaskForm;
