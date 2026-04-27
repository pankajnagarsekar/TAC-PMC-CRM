import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams } from 'expo-router';
import { Feather } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import api from '../../../services/apiClient';
import { Task } from '../../../types/api';
import { Card, Badge } from '../../../components/ui';

export default function TaskDetail() {
  const { id } = useLocalSearchParams();
  const { colors: Colors } = useTheme();

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTask = useCallback(async () => {
    if (!id) return;
    try {
      const data = await api.tasks.getById(id as string);
      setTask(data);
    } catch (err) {
      console.error('Error fetching task:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useEffect(() => {
    fetchTask();
  }, [fetchTask]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchTask();
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'high': return '#ef4444';
      case 'normal': return '#3b82f6';
      case 'low': return '#10b981';
      default: return Colors.textMuted;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'open': return '#3b82f6';
      case 'in progress': return '#f59e0b';
      case 'completed': return '#10b981';
      case 'closed': return Colors.textMuted;
      default: return Colors.textMuted;
    }
  };

  if (loading && !refreshing) {
    return (
      <View style={[styles.centered, { backgroundColor: Colors.background }]}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (!task) {
    return (
      <View style={[styles.centered, { backgroundColor: Colors.background }]}>
        <Text style={{ color: Colors.text }}>Task not found</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: Colors.background }]}
      contentContainerStyle={styles.scrollContent}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
      }
    >
      {/* Header Info */}
      <Card variant="elevated" style={styles.card} padding="md">
        <View style={styles.metaRow}>
          <Text style={[styles.srNo, { color: Colors.textSecondary }]}>#{task.sr_no}</Text>
          <Badge label={task.priority} color={getPriorityColor(task.priority)} variant="outline" />
        </View>
        <Text style={[styles.description, { color: Colors.text }]}>{task.task_description}</Text>
        <Badge label={task.status} color={getStatusColor(task.status)} />
      </Card>

      {/* Details Section */}
      <View style={styles.sectionHeader}>
        <Text style={[styles.sectionTitle, { color: Colors.textSecondary }]}>DETAILS</Text>
      </View>
      <Card variant="elevated" style={styles.card} padding="md">
        <View style={styles.detailItem}>
          <Feather name="user" size={16} color={Colors.textSecondary} />
          <View style={styles.detailText}>
            <Text style={[styles.detailLabel, { color: Colors.textSecondary }]}>Assigned To</Text>
            <Text style={[styles.detailValue, { color: Colors.text }]}>{task.assigned_to_name}</Text>
          </View>
        </View>
        <View style={[styles.detailItem, styles.marginTop]}>
          <Feather name="calendar" size={16} color={Colors.textSecondary} />
          <View style={styles.detailText}>
            <Text style={[styles.detailLabel, { color: Colors.textSecondary }]}>Deadline</Text>
            <Text style={[styles.detailValue, { color: Colors.text }]}>
              {task.deadline ? new Date(task.deadline).toLocaleDateString() : 'No deadline'}
            </Text>
          </View>
        </View>
        <View style={[styles.detailItem, styles.marginTop]}>
          <Feather name="edit-3" size={16} color={Colors.textSecondary} />
          <View style={styles.detailText}>
            <Text style={[styles.detailLabel, { color: Colors.textSecondary }]}>Created By</Text>
            <Text style={[styles.detailValue, { color: Colors.text }]}>{task.created_by_name}</Text>
          </View>
        </View>
      </Card>

      {/* Audit Log / History */}
      <View style={styles.sectionHeader}>
        <Text style={[styles.sectionTitle, { color: Colors.textSecondary }]}>HISTORY</Text>
      </View>
      <View style={styles.logContainer}>
        {task.audit_log?.map((log: { action: string, timestamp: string, user: string, detail: string }, index: number) => (
          <View key={index} style={styles.logItem}>
            <View style={styles.logTimeline}>
              <View style={[styles.logDot, { backgroundColor: Colors.primary }]} />
              {index < task.audit_log.length - 1 && <View style={[styles.logLine, { backgroundColor: Colors.border }]} />}
            </View>
            <View style={styles.logContent}>
              <View style={styles.logHeader}>
                <Text style={[styles.logUser, { color: Colors.text }]}>{log.user}</Text>
                <Text style={[styles.logDate, { color: Colors.textSecondary }]}>
                  {new Date(log.timestamp).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                </Text>
              </View>
              <Text style={[styles.logDetail, { color: Colors.textSecondary }]}>{log.detail || log.action}</Text>
            </View>
          </View>
        ))}
        {(!task.audit_log || task.audit_log.length === 0) && (
          <Text style={[styles.emptyLogs, { color: Colors.textMuted }]}>No history available for this task.</Text>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scrollContent: { padding: 16, paddingBottom: 40 },
  card: { marginBottom: 20 },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  srNo: { fontSize: 13, fontWeight: '700' },
  description: { fontSize: 18, fontWeight: '600', marginBottom: 16, lineHeight: 24 },
  sectionHeader: { marginBottom: 12 },
  sectionTitle: { fontSize: 11, fontWeight: '800', letterSpacing: 1 },
  detailItem: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  detailText: { flex: 1 },
  detailLabel: { fontSize: 11, fontWeight: '700', textTransform: 'uppercase', marginBottom: 2 },
  detailValue: { fontSize: 15, fontWeight: '500' },
  marginTop: { marginTop: 16 },
  logContainer: { paddingLeft: 8 },
  logItem: { flexDirection: 'row', minHeight: 60 },
  logTimeline: { width: 30, alignItems: 'center' },
  logDot: { width: 8, height: 8, borderRadius: 4, marginTop: 6, zIndex: 1 },
  logLine: { position: 'absolute', top: 12, bottom: -6, width: 2, left: 14 },
  logContent: { flex: 1, paddingBottom: 20, paddingLeft: 8 },
  logHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  logUser: { fontSize: 14, fontWeight: '700' },
  logDate: { fontSize: 12 },
  logDetail: { fontSize: 13, lineHeight: 18 },
  emptyLogs: { fontSize: 14, fontStyle: 'italic', textAlign: 'center', marginTop: 12 },
});
