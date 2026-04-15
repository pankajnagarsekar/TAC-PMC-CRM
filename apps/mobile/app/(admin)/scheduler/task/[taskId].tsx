import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { View, ActivityIndicator, Text } from 'react-native';
import type { ScheduleTask } from '../../../../types/api';
import { schedulerApi } from '../../../../services/apiClient';
import { TaskDetailModal } from '../../../../components/scheduler/TaskDetailModal';
import { useProject } from '../../../../contexts/ProjectContext';

export default function TaskDetailsScreen() {
  const { taskId } = useLocalSearchParams();
  const { selectedProject } = useProject();
  const router = useRouter();
  const [task, setTask] = useState<ScheduleTask | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Stop loading if project is not selected or taskId is invalid
    if (!selectedProject || !taskId || taskId === 'undefined') {
      console.error('[TaskDetailsScreen] Invalid state:', {
        hasProject: !!selectedProject,
        taskId
      });
      setLoading(false);
      // Try to go back, but don't return early because we want to show error state if back fails
      if (router.canGoBack()) {
        router.back();
      }
      return;
    }

    // Load full task data if needed (taskId is available from route)
    // For now, just show the modal and let parent handle it
    setLoading(false);
  }, [taskId, selectedProject, router]);

  return (
    <View style={{ flex: 1, backgroundColor: 'white' }}>
      {loading ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" />
        </View>
      ) : !selectedProject || !taskId || taskId === 'undefined' ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 }}>
          <Text style={{ fontSize: 18, fontWeight: '600', marginBottom: 8 }}>Task Not Found</Text>
          <Text style={{ textAlign: 'center', color: '#666' }}>
            We couldn't load the task details. Please try again from the scheduler.
          </Text>
        </View>
      ) : (
        <TaskDetailModal
          task={null}
          projectId={selectedProject?.project_id ?? ''}
          visible={true}
          onClose={() => router.back()}
        />
      )}
    </View>
  );
}
