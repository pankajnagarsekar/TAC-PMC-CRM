// SchedulerScreen — top-level screen with Gantt/List tab switcher
// Guards: redirects to /select-project if no active project is selected.
// Luxury Industrial Design System Enforcement

import React, { useState, Component, ReactNode } from 'react';
import { View, Text, ActivityIndicator, Pressable, StyleSheet, StatusBar } from 'react-native';
import { Redirect } from 'expo-router';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { Ionicons } from '@expo/vector-icons';
import { useProject } from '../../contexts/ProjectContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useSchedulerData } from '../../hooks/useSchedulerData';
import { SchedulerGantt } from './SchedulerGantt';
import { SchedulerList } from './SchedulerList';

type ViewMode = 'gantt' | 'list';

/**
 * Simple Error Boundary to catch crashes in sub-components
 */
class ErrorBoundary extends Component<{ children: ReactNode; colors: any }, { hasError: boolean }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError() { return { hasError: true }; }
  render() {
    if (this.state.hasError) {
      return (
        <View style={[styles.centered, { backgroundColor: this.props.colors.background }]}>
          <Ionicons name="alert-circle" size={48} color="#ef4444" />
          <Text style={{ color: this.props.colors.text, marginTop: 16, textAlign: 'center' }}>
            Something went wrong rendering the schedule.
          </Text>
          <Pressable style={styles.retryButton} onPress={() => this.setState({ hasError: false })}>
            <Text style={{ color: this.props.colors.primary }}>Try Again</Text>
          </Pressable>
        </View>
      );
    }
    return this.children;
  }
}

function SchedulerScreen() {
  const { selectedProject } = useProject();
  const { colors: Colors, typography: Typography, isDark } = useTheme();
  const [viewMode, setViewMode] = useState<ViewMode>('list');

  const projectId = selectedProject?.project_id ?? null;
  const { tasks, projectStart, loading, error, refetch } = useSchedulerData(projectId);

  // Guard: no active project → redirect to project selection
  if (!selectedProject) {
    return <Redirect href="/(admin)/select-project" />;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <StatusBar barStyle={isDark ? "light-content" : "dark-content"} />
      <View style={[styles.container, { backgroundColor: Colors.background }]}>
        
        {/* Luxury Header */}
        <View style={[styles.header, { borderBottomColor: Colors.border }]}>
          <View style={styles.headerInfo}>
            <Text style={[styles.projectName, { color: Colors.text, ...Typography.heading2 }]} numberOfLines={1}>
                {selectedProject.project_name}
            </Text>
            <Text style={[styles.headerSubtitle, { color: Colors.textMuted, ...Typography.overline }]}>
                PROJECT SCHEDULE
            </Text>
          </View>

          {/* Premium View Switcher */}
          <View style={[styles.segmentControl, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
            <Pressable
              style={[
                styles.segment,
                viewMode === 'list' && { backgroundColor: Colors.primary },
              ]}
              onPress={() => setViewMode('list')}
            >
              <Ionicons 
                name="list-outline" 
                size={16} 
                color={viewMode === 'list' ? Colors.textInverse : Colors.textMuted} 
              />
            </Pressable>
            <Pressable
              style={[
                styles.segment,
                viewMode === 'gantt' && { backgroundColor: Colors.primary },
              ]}
              onPress={() => setViewMode('gantt')}
            >
              <Ionicons 
                name="stats-chart-outline" 
                size={16} 
                color={viewMode === 'gantt' ? Colors.textInverse : Colors.textMuted} 
              />
            </Pressable>
          </View>
        </View>

        {/* Content with Error Boundary Protection */}
        <ErrorBoundary colors={Colors}>
            {loading ? (
            <View style={styles.centered}>
                <ActivityIndicator size="large" color={Colors.primary} />
                <Text style={{ color: Colors.textSecondary, marginTop: 12 }}>Optimizing view...</Text>
            </View>
            ) : error ? (
            <View style={styles.centered}>
                <Ionicons name="cloud-offline-outline" size={48} color={Colors.textMuted} />
                <Text style={[styles.errorText, { color: Colors.textSecondary, marginTop: 16 }]}>
                {error}
                </Text>
                <Pressable
                style={[styles.retryButton, { borderColor: Colors.primary }]}
                onPress={refetch}
                >
                <Text style={{ color: Colors.primary, fontWeight: '700' }}>Retry Sync</Text>
                </Pressable>
            </View>
            ) : viewMode === 'gantt' ? (
            <SchedulerGantt tasks={tasks} projectStart={projectStart} />
            ) : (
            <SchedulerList tasks={tasks} />
            )}
        </ErrorBoundary>
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
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
  },
  headerInfo: {
    flex: 1,
    marginRight: 16,
  },
  projectName: {
    fontWeight: '800',
  },
  headerSubtitle: {
    marginTop: 2,
    letterSpacing: 1,
  },
  segmentControl: {
    flexDirection: 'row',
    borderWidth: 1,
    borderRadius: 12,
    overflow: 'hidden',
    padding: 2,
  },
  segment: {
    width: 40,
    height: 36,
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 10,
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  errorText: {
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderWidth: 1,
    borderRadius: 12,
  },
});

export default SchedulerScreen;
