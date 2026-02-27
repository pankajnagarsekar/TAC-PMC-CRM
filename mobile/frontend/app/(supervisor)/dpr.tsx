// SUPERVISOR DPR SCREEN
// Uses shared DPRForm component with project from context

import React, { useEffect } from 'react';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useProject } from '../../contexts/ProjectContext';
import DPRForm from '../../components/DPRForm';
import { Colors } from '../../constants/theme';

export default function SupervisorDPRScreen() {
  const router = useRouter();
  const { selectedProject } = useProject();

  // Redirect if no project selected - defer to avoid navigating before layout mounts
  useEffect(() => {
    if (!selectedProject) {
      // Use requestAnimationFrame to ensure layout is mounted first
      requestAnimationFrame(() => {
        router.replace('/(supervisor)/select-project');
      });
    }
  }, [selectedProject]);

  const handleSuccess = () => {
    router.back();
  };

  const handleCancel = () => {
    router.back();
  };

  if (!selectedProject) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.accent} />
        </View>
      </SafeAreaView>
    );
  }

  const projectId = (selectedProject as any).project_id || (selectedProject as any)._id || '';
  const projectName = selectedProject.project_name || 'Project';
  const projectCode = (selectedProject as any).project_code;

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <DPRForm
        projectId={projectId}
        projectName={projectName}
        projectCode={projectCode}
        onSuccess={handleSuccess}
        onCancel={handleCancel}
        showHeader={true}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
});
