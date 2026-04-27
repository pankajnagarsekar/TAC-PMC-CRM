// SchedulerScreen — top-level screen with Gantt/List tab switcher
// Guards: redirects to /select-project if no active project is selected.
// Wraps everything in GestureHandlerRootView (required for gesture handler).

import React, { useState } from 'react';
import { View, Text, ActivityIndicator, Pressable, StyleSheet } from 'react-native';
import { Redirect } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { useProject } from '../../contexts/ProjectContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useSchedulerData } from '../../hooks/useSchedulerData';
import { SchedulerGantt } from './SchedulerGantt';
import { SchedulerList } from './SchedulerList';

type ViewMode = 'gantt' | 'list';

function SchedulerScreen() {
  const { selectedProject } = useProject();
  const { colors } = useTheme();
  const [viewMode, setViewMode] = useState<ViewMode>('list');

  const projectId = selectedProject?.project_id ?? null;
  const { tasks, projectStart, loading, error, refetch } = useSchedulerData(projectId);

  // Guard: no active project → redirect to project selection
  if (!selectedProject) {
    return <Redirect href="/(admin)/select-project" />;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        {/* Header */}
        <View style={[styles.header, { borderBottomColor: colors.border }]}>
          <Text style={[styles.projectName, { color: colors.text }]} numberOfLines={1}>
            {selectedProject.project_name}
          </Text>

          {/* Gantt / List toggle */}
          <View style={[styles.segmentControl, { borderColor: colors.border }]}>
            <Pressable
              style={[
                styles.segment,
                viewMode === 'list' && { backgroundColor: colors.primary },
              ]}
              onPress={() => setViewMode('list')}
            >
              <Text
                style={[
                  styles.segmentText,
                  { color: viewMode === 'list' ? '#fff' : colors.textMuted },
                ]}
              >
                List
              </Text>
            </Pressable>
            <Pressable
              style={[
                styles.segment,
                viewMode === 'gantt' && { backgroundColor: colors.primary },
              ]}
              onPress={() => setViewMode('gantt')}
            >
              <Text
                style={[
                  styles.segmentText,
                  { color: viewMode === 'gantt' ? '#fff' : colors.textMuted },
                ]}
              >
                Gantt
              </Text>
            </Pressable>
          </View>
        </View>

        {/* Content */}
        {loading ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={colors.primary} />
          </View>
        ) : error ? (
          <View style={styles.centered}>
            <Text style={[styles.errorText, { color: '#ef4444' }]}>
              {error}
            </Text>
            <Pressable
              style={[styles.retryButton, { borderColor: colors.primary }]}
              onPress={refetch}
            >
              <Text style={{ color: colors.primary }}>Retry</Text>
            </Pressable>
          </View>
        ) : viewMode === 'gantt' ? (
          <SchedulerGantt tasks={tasks} projectStart={projectStart} />
        ) : (
          <SchedulerList tasks={tasks} />
        )}
      </View>
    </GestureHandlerRootView>
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
  projectName: {
    fontSize: 16,
    fontWeight: '600',
    flex: 1,
    marginRight: 12,
  },
  segmentControl: {
    flexDirection: 'row',
    borderWidth: 1,
    borderRadius: 8,
    overflow: 'hidden',
  },
  segment: {
    paddingHorizontal: 14,
    paddingVertical: 6,
  },
  segmentText: {
    fontSize: 13,
    fontWeight: '600',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorText: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 16,
  },
  retryButton: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderWidth: 1,
    borderRadius: 8,
  },
});

export default SchedulerScreen;
