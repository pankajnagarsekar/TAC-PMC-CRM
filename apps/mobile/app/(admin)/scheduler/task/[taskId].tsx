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
    if (!selectedProject || !taskId) {
      router.back();
      return;
    }

    // Load full task data if needed (taskId is available from route)
    // For now, just show the modal and let parent handle it
    setLoading(false);
  }, [taskId, selectedProject]);

  return (
    <View style={{ flex: 1 }}>
      {loading ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" />
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
