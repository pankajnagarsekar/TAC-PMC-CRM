// SchedulerList — virtualized task list with status chips and critical-path highlighting
// Uses FlashList (NOT FlatList) for 60fps virtualization.

import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { FlashList } from '@shopify/flash-list';
import { format } from 'date-fns';
import type { ScheduleTask } from '../../types/api';
import { STATUS_COLORS, STATUS_LABELS, CRITICAL_COLOR } from './scheduler-constants';
import { parseTaskDate } from './scheduler-utils';
import { useTheme } from '../../contexts/ThemeContext';

interface SchedulerListProps {
  tasks: ScheduleTask[];
}

function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  try {
    const d = parseTaskDate(value);
    if (!d) return '—';
    return format(d, 'dd MMM');
  } catch {
    return '—';
  }
}

function TaskRow({ item, colors, dynamicStyles }: { item: ScheduleTask; colors: any; dynamicStyles: any }) {
  const router = useRouter();
  const isCritical = item.is_critical;
  const statusColor = STATUS_COLORS[item.status] ?? colors.textMuted;
  const statusLabel = STATUS_LABELS[item.status] ?? item.status;

  return (
    <Pressable
      testID={isCritical ? 'critical-task-row' : 'task-row'}
      onPress={() => router.push(`/scheduler/task/${item.task_id}`)}
      style={[
        dynamicStyles.row,
        isCritical && { borderLeftColor: CRITICAL_COLOR, borderLeftWidth: 3 },
      ]}
    >
      <View style={styles.rowContent}>
        <Text style={[dynamicStyles.taskName, { color: colors.text }]} numberOfLines={1}>
          {item.name}
        </Text>
        <View style={styles.metaRow}>
          <View style={[styles.statusChip, { backgroundColor: statusColor + '22', borderColor: statusColor }]}>
            <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
          </View>
          <Text style={dynamicStyles.dateRange}>
            {formatDate(item.start_date)} → {formatDate(item.end_date)}
          </Text>
          <Text style={dynamicStyles.duration}>{item.duration_days}d</Text>
        </View>
      </View>
    </Pressable>
  );
}

export function SchedulerList({ tasks }: SchedulerListProps) {
  const { colors } = useTheme();
  const dynamicStyles = createDynamicStyles(colors);

  if (tasks.length === 0) {
    return (
      <View style={[styles.emptyContainer, { backgroundColor: colors.background }]}>
        <Text style={dynamicStyles.emptyText}>No scheduled tasks yet</Text>
      </View>
    );
  }

  return (
    <FlashList
      data={tasks}
      keyExtractor={(item) => item.task_id}
      estimatedItemSize={60}
      renderItem={({ item }) => <TaskRow item={item} colors={colors} dynamicStyles={dynamicStyles} />}
    />
  );
}

function createDynamicStyles(colors: any) {
  return StyleSheet.create({
    row: {
      paddingVertical: 10,
      paddingHorizontal: 16,
      borderBottomWidth: StyleSheet.hairlineWidth,
      borderBottomColor: colors.border,
      backgroundColor: colors.background,
      borderLeftWidth: 0,
      borderLeftColor: 'transparent',
    },
    taskName: {
      color: colors.text,
      fontSize: 14,
      fontWeight: '500',
    },
    dateRange: {
      color: colors.textSecondary,
      fontSize: 12,
      flex: 1,
    },
    duration: {
      color: colors.textMuted,
      fontSize: 12,
    },
    emptyText: {
      color: colors.textMuted,
      fontSize: 16,
    },
  });
}

const styles = StyleSheet.create({
  rowContent: {
    gap: 6,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusChip: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
});

export default SchedulerList;
