// TaskDetailModal — modal for viewing and editing task details
// Uses useTaskEdit hook for state management and optimistic updates

import React, { useState } from 'react';
import { Modal, View, Text, Pressable, StyleSheet, ActivityIndicator, ScrollView } from 'react-native';
import { format, parseISO } from 'date-fns';
import type { ScheduleTask } from '../../types/api';
import { useTaskEdit } from '../../hooks/useTaskEdit';
import { useTheme, ThemeContextType } from '../../contexts/ThemeContext';
import { TaskForm } from './TaskForm';
import { STATUS_LABELS, CRITICAL_COLOR } from './scheduler-constants';

interface TaskDetailModalProps {
  task: ScheduleTask | null;
  projectId: string;
  visible: boolean;
  onClose: () => void;
  onSaveSuccess?: (updatedTask: ScheduleTask) => void;
}

export function TaskDetailModal({
  task,
  projectId,
  visible,
  onClose,
  onSaveSuccess,
}: TaskDetailModalProps) {
  const { colors } = useTheme();
  const [isEditMode, setIsEditMode] = useState(false);
  const taskEditor = useTaskEdit(task || ({} as ScheduleTask));

  if (!task) return null;

  const handleSave = async () => {
    const success = await taskEditor.save(projectId);
    if (success) {
      setIsEditMode(false);
      // Optionally notify parent that task was saved
      if (onSaveSuccess) {
        // Create updated task object with new values
        const updatedTask = {
          ...task,
          task_name: taskEditor.editState.task_name ?? task.task_name,
          status: taskEditor.editState.status ?? task.status,
          duration: taskEditor.editState.duration ?? task.duration,
        };
        onSaveSuccess(updatedTask as ScheduleTask);
      }
    }
  };

  const handleCancel = () => {
    taskEditor.reset();
    setIsEditMode(false);
  };

  const handleClose = () => {
    taskEditor.reset();
    setIsEditMode(false);
    onClose();
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      onRequestClose={handleClose}
    >
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        {/* Header */}
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Text
            style={[styles.title, { color: colors.text }]}
            numberOfLines={1}
          >
            {task.task_name}
          </Text>
          {task.is_critical && (
            <View style={[styles.criticalBadge, { backgroundColor: CRITICAL_COLOR }]}>
              <Text style={styles.criticalBadgeText}>Critical</Text>
            </View>
          )}
          <Pressable onPress={handleClose} style={styles.closeButton}>
            <Text style={{ color: colors.primary, fontSize: 18 }}>✕</Text>
          </Pressable>
        </View>

        {/* Content */}
        <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
          {isEditMode ? (
            <TaskForm
              task={task}
              editState={taskEditor.editState}
              validationErrors={taskEditor.validationErrors}
              onEditStateChange={taskEditor.setEditState}
            />
          ) : (
            <TaskDetailView task={task} colors={colors} />
          )}

          {/* Error message */}
          {taskEditor.saveError && (
            <View style={[styles.errorContainer, { backgroundColor: '#7f1d1d' }]}>
              <Text style={{ color: '#fca5a5' }}>{taskEditor.saveError}</Text>
            </View>
          )}
        </ScrollView>

        {/* Footer */}
        <View style={[styles.footer, { borderTopColor: colors.border }]}>
          {isEditMode ? (
            <>
              <Pressable
                style={[styles.button, { backgroundColor: colors.border }]}
                onPress={handleCancel}
                disabled={taskEditor.isSaving}
              >
                <Text style={{ color: colors.text }}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[styles.button, { backgroundColor: colors.primary }]}
                onPress={handleSave}
                disabled={taskEditor.isSaving}
              >
                {taskEditor.isSaving ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={{ color: '#fff', fontWeight: '600' }}>Save</Text>
                )}
              </Pressable>
            </>
          ) : (
            <Pressable
              style={[styles.button, { backgroundColor: colors.primary }]}
              onPress={() => setIsEditMode(true)}
            >
              <Text style={{ color: '#fff', fontWeight: '600' }}>Edit</Text>
            </Pressable>
          )}
        </View>
      </View>
    </Modal>
  );
}

function TaskDetailView({ task, colors }: { task: ScheduleTask; colors: ThemeContextType['colors'] }) {
  const formatDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return '—';
    try {
      const d = parseISO(dateStr);
      return format(d, 'dd MMM yyyy');
    } catch {
      return '—';
    }
  };

  const statusLabel = STATUS_LABELS[task.status] ?? task.status;

  return (
    <View>
      <DetailRow label="Task ID" value={task.task_id} colors={colors} />
      <DetailRow label="Status" value={statusLabel} colors={colors} />
      <DetailRow label="Duration" value={`${task.duration} days`} colors={colors} />
      <DetailRow label="Start Date" value={formatDate(task.scheduled_start)} colors={colors} />
      <DetailRow label="End Date" value={formatDate(task.scheduled_finish)} colors={colors} />
      {task.progress_pct !== undefined && (
        <DetailRow label="Progress" value={`${task.progress_pct}%`} colors={colors} />
      )}
      {!!task.baseline_start && (
        <DetailRow label="Baseline Start" value={formatDate(task.baseline_start)} colors={colors} />
      )}
      {!!task.baseline_finish && (
        <DetailRow label="Baseline End" value={formatDate(task.baseline_finish)} colors={colors} />
      )}
    </View>
  );
}

function DetailRow({ label, value, colors }: { label: string; value: string; colors: ThemeContextType['colors'] }) {
  return (
    <View style={styles.detailRow}>
      <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>{label}</Text>
      <Text style={[styles.detailValue, { color: colors.text }]}>{value}</Text>
    </View>
  );
}



const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  title: {
    flex: 1,
    fontSize: 18,
    fontWeight: '700',
    marginRight: 8,
  },
  criticalBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    marginRight: 8,
  },
  criticalBadgeText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  closeButton: {
    padding: 8,
  },
  content: {
    flex: 1,
  },
  contentInner: {
    paddingHorizontal: 16,
    paddingVertical: 16,
    gap: 16,
  },
  errorContainer: {
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 6,
    marginTop: 8,
  },
  footer: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    gap: 12,
  },
  button: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    justifyContent: 'center',
    alignItems: 'center',
  },
  detailRow: {
    paddingVertical: 10,
    gap: 4,
  },
  detailLabel: {
    fontSize: 12,
    fontWeight: '600',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '500',
  },
});

export default TaskDetailModal;
