// SchedulerList — virtualized task list with status chips and critical-path highlighting
// Uses FlashList (NOT FlatList) for 60fps virtualization.

import React from 'react';
import { View, Text, Pressable, StyleSheet, useColorScheme } from 'react-native';
import { useRouter } from 'expo-router';
import { FlashList } from '@shopify/flash-list';
import { format, parseISO } from 'date-fns';
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

function TaskRow({ item, colors }: { item: ScheduleTask; colors: any }) {
  const router = useRouter();
  const isCritical = item.is_critical;
  const statusColor = STATUS_COLORS[item.status] ?? '#64748b';
  const statusLabel = STATUS_LABELS[item.status] ?? item.status;

  return (
    <Pressable
      testID={isCritical ? 'critical-task-row' : 'task-row'}
      onPress={() => router.push(`/scheduler/task/${item.task_id}`)}
      style={[
        styles.row,
        isCritical && { borderLeftColor: CRITICAL_COLOR, borderLeftWidth: 3 },
      ]}
    >
      <View style={styles.rowContent}>
        <Text style={[styles.taskName, { color: colors.text }]} numberOfLines={1}>
          {item.name}
        </Text>
        <View style={styles.metaRow}>
          <View style={[styles.statusChip, { backgroundColor: statusColor + '22', borderColor: statusColor }]}>
            <Text style={[styles.statusText, { color: statusColor }]}>{statusLabel}</Text>
          </View>
          <Text style={[styles.dateRange, { color: colors.textSecondary }]}>
            {formatDate(item.start_date)} → {formatDate(item.end_date)}
          </Text>
          <Text style={[styles.duration, { color: colors.textSecondary }]}>{item.duration_days}d</Text>
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
        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No scheduled tasks yet</Text>
      </View>
    );
  }

  return (
    <FlashList
      data={tasks}
      keyExtractor={(item) => item.task_id}
      renderItem={({ item }) => <TaskRow item={item} colors={colors} />}
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
  });
}

const styles = StyleSheet.create({
  row: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: '#1e293b',
    backgroundColor: '#0f172a',
    borderLeftWidth: 0,
    borderLeftColor: 'transparent',
  },
  rowContent: {
    gap: 6,
  },
  taskName: {
    color: '#f1f5f9',
    fontSize: 14,
    fontWeight: '500',
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
  dateRange: {
    color: '#94a3b8',
    fontSize: 12,
    flex: 1,
  },
  duration: {
    color: '#64748b',
    fontSize: 12,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 40,
  },
  emptyText: {
    color: '#64748b',
    fontSize: 16,
  },
});

export default SchedulerList;
