import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  Pressable,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useProject } from '../../../contexts/ProjectContext';
import { useTheme } from '../../../contexts/ThemeContext';
import api from '../../../services/apiClient';
import { Task } from '../../../types/api';
import { Card, Badge } from '../../../components/ui';

export default function TasksIndex() {
  const router = useRouter();
  const { selectedProject } = useProject();
  const { colors: Colors } = useTheme();

  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchTasks = useCallback(async () => {
    if (!selectedProject?.project_id) return;
    try {
      const data = await api.tasks.getForProject(selectedProject.project_id);
      setTasks(data || []);
    } catch (err) {
      console.error('Error fetching tasks:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedProject?.project_id]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchTasks();
  };

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high': return '#ef4444';
      case 'normal': return '#3b82f6';
      case 'low': return '#10b981';
      default: return Colors.textMuted;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open': return '#3b82f6';
      case 'in progress': return '#f59e0b';
      case 'completed': return '#10b981';
      case 'closed': return Colors.textMuted;
      default: return Colors.textMuted;
    }
  };

  const renderTask = ({ item }: { item: Task }) => (
    <Card
      variant="elevated"
      style={styles.taskCard}
      onPress={() => router.push(`/(admin)/tasks/${item.id || item._id}` as any)}
      padding="md"
    >
      <View style={styles.taskHeader}>
        <Text style={[styles.taskSrNo, { color: Colors.textSecondary }]}>#{item.sr_no}</Text>
        <Badge
          label={item.priority}
          color={getPriorityColor(item.priority)}
          variant="outline"
        />
      </View>
      <Text style={[styles.taskDescription, { color: Colors.text }]} numberOfLines={2}>
        {item.task_description}
      </Text>
      <View style={styles.taskFooter}>
        <View style={styles.assigneeBox}>
          <Ionicons name="person-outline" size={12} color={Colors.textSecondary} />
          <Text style={[styles.assigneeName, { color: Colors.textSecondary }]}>
            {item.assigned_to_name}
          </Text>
        </View>
        <Badge
          label={item.status}
          color={getStatusColor(item.status)}
        />
      </View>
    </Card>
  );

  if (loading && !refreshing) {
    return (
      <View style={[styles.centered, { backgroundColor: Colors.background }]}>
        <ActivityIndicator size="large" color={Colors.primary} />
      </View>
    );
  }

  if (!selectedProject) {
    return (
      <View style={[styles.centered, { backgroundColor: Colors.background, padding: 20 }]}>
        <Ionicons name="alert-circle-outline" size={48} color={Colors.textMuted} />
        <Text style={[styles.emptyTitle, { color: Colors.text }]}>No Project Selected</Text>
        <Text style={[styles.emptySubtitle, { color: Colors.textMuted }]}>
          Please select a project from the dashboard to view related tasks.
        </Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: Colors.background }]}>
      <FlatList
        data={tasks}
        renderItem={renderTask}
        keyExtractor={(item: Task) => (item.id || item._id || item.task_id || '').toString()}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />
        }
        ListEmptyComponent={
          <View style={styles.emptyList}>
            <Ionicons name="clipboard-outline" size={64} color={Colors.border} />
            <Text style={[styles.emptyText, { color: Colors.textMuted }]}>No tasks found for this project</Text>
          </View>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  listContent: { padding: 16 },
  taskCard: { marginBottom: 12 },
  taskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  taskSrNo: { fontSize: 12, fontWeight: '700' },
  taskDescription: { fontSize: 16, fontWeight: '600', marginBottom: 16 },
  taskFooter: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  assigneeBox: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  assigneeName: { fontSize: 13 },
  emptyList: { padding: 40, alignItems: 'center' },
  emptyText: { marginTop: 16, fontSize: 16 },
  emptyTitle: { fontSize: 20, fontWeight: '900', marginTop: 16, marginBottom: 8 },
  emptySubtitle: { fontSize: 14, textAlign: 'center', opacity: 0.7 },
});
