import React, { useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  SafeAreaView,
  Pressable,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useProject } from '../../contexts/ProjectContext';
import { useDashboardData } from '../../hooks/useDashboardData';
import { Card } from '../ui';
import { MiniChart } from './MiniChart';
import { MetricsDetail } from './MetricsDetail';

export function AnalyticsScreen() {
  const { selectedProject } = useProject();
  const { colors: Colors } = useTheme();
  const { data, loading, error, refetch } = useDashboardData(
    {
      projectId: selectedProject?.project_id,
      refetchInterval: 30000, // 30s
    }
  );

  const [refreshing, setRefreshing] = React.useState(false);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await refetch();
    setRefreshing(false);
  }, [refetch]);

  if (!selectedProject) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <View style={styles.emptyState}>
          <Ionicons name="bar-chart-outline" size={48} color={Colors.primary} />
          <Text style={[styles.emptyTitle, { color: Colors.text }]}>
            No Project Selected
          </Text>
          <Text style={[styles.emptySubtitle, { color: Colors.textSecondary }]}>
            Select an active project to view analytics
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (loading && !data) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <View style={styles.loadingState}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={[styles.loadingText, { color: Colors.textSecondary }]}>
            Loading analytics...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  if (error) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <View style={styles.errorState}>
          <Ionicons name="alert-circle-outline" size={48} color="#ef4444" />
          <Text style={[styles.errorTitle, { color: Colors.text }]}>
            Failed to Load Analytics
          </Text>
          <Text style={[styles.errorMessage, { color: Colors.textSecondary }]}>
            {error.message || 'An unexpected error occurred'}
          </Text>
          <Pressable
            onPress={onRefresh}
            style={[styles.retryButton, { backgroundColor: Colors.primary }]}
          >
            <Text style={styles.retryText}>Try Again</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  if (!data) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <View style={styles.emptyState}>
          <Ionicons name="bar-chart-outline" size={48} color={Colors.primary} />
          <Text style={[styles.emptyTitle, { color: Colors.text }]}>
            No Data Available
          </Text>
          <Text style={[styles.emptySubtitle, { color: Colors.textSecondary }]}>
            Analytics data will appear when available
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
      <ScrollView
        contentContainerStyle={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={[styles.projectName, { color: Colors.textSecondary }]}>
              PROJECT ANALYTICS
            </Text>
            <Text style={[styles.projectTitle, { color: Colors.text }]}>
              {data.project_name}
            </Text>
          </View>
          <View style={[styles.lastUpdated, { backgroundColor: Colors.surface }]}>
            <Ionicons name="time-outline" size={12} color={Colors.textSecondary} />
            <Text style={[styles.updatedTime, { color: Colors.textSecondary }]}>
              {new Date(data.updated_at).toLocaleTimeString(undefined, {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </View>
        </View>

        {/* KPI Cards */}
        <View style={styles.kpiGrid}>
          <KPICard
            label="SCHEDULE"
            value={data.schedule.days_remaining}
            unit="days"
            status={data.schedule.status}
            colors={Colors}
          />
          <KPICard
            label="BUDGET"
            value={(data.financial.budget_remaining / 100000).toFixed(1)}
            unit="L"
            status={data.financial.budget_remaining > 0 ? 'green' : 'red'}
            colors={Colors}
          />
          <KPICard
            label="AT RISK"
            value={data.schedule.tasks_at_risk}
            unit="tasks"
            status={data.schedule.tasks_at_risk > 0 ? 'yellow' : 'green'}
            colors={Colors}
          />
        </View>

        {/* Mini Charts */}
        <Text style={[styles.sectionTitle, { color: Colors.textSecondary }]}>
          TRENDS
        </Text>
        <MiniChart
          data={data.timeline.budget_spent_trend}
          label="Budget Spend"
          metric="budget"
          value={data.financial.burn_rate_daily}
          unit="/day"
        />
        <MiniChart
          data={data.timeline.daily_completion}
          label="Task Completion"
          metric="completion"
          value={data.timeline.daily_completion[data.timeline.daily_completion.length - 1]?.value || 0}
          unit="tasks"
        />
        <MiniChart
          data={data.timeline.utilization_trend}
          label="Resource Utilization"
          metric="utilization"
          value={
            Object.values(data.resources.by_resource || {}).reduce((sum, r) => sum + r.allocation_percent, 0) /
            Object.keys(data.resources.by_resource || {}).length
          }
          unit="%"
        />

        {/* Expandable Details */}
        <Text style={[styles.sectionTitle, { color: Colors.textSecondary }]}>
          DETAILS
        </Text>
        <MetricsDetail
          type="schedule"
          schedule={data.schedule}
        />
        <MetricsDetail
          type="resources"
          resources={data.resources}
        />
        <MetricsDetail
          type="financial"
          financial={data.financial}
        />
      </ScrollView>
    </SafeAreaView>
  );
}

interface KPICardProps {
  label: string;
  value: number | string;
  unit: string;
  status: 'green' | 'yellow' | 'red';
  colors: any;
}

function KPICard({ label, value, unit, status, colors }: KPICardProps) {
  const statusColors = {
    green: '#10b981',
    yellow: '#eab308',
    red: '#ef4444',
  };

  return (
    <Card padding="md" style={styles.kpiCard}>
      <View style={styles.kpiHeader}>
        <Text style={[styles.kpiLabel, { color: colors.textSecondary }]}>
          {label}
        </Text>
        <View
          style={[
            styles.statusIcon,
            { backgroundColor: `${statusColors[status]}20` },
          ]}
        >
          <View
            style={[
              styles.statusDot,
              { backgroundColor: statusColors[status] },
            ]}
          />
        </View>
      </View>
      <Text style={[styles.kpiValue, { color: colors.text }]}>
        {value}{unit}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 20,
  },
  projectName: {
    fontSize: 9,
    fontWeight: '800',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  projectTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  lastUpdated: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  updatedTime: {
    fontSize: 9,
    fontWeight: '600',
  },
  kpiGrid: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 24,
  },
  kpiCard: {
    flex: 1,
  },
  kpiHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  kpiLabel: {
    fontSize: 9,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  statusIcon: {
    width: 24,
    height: 24,
    borderRadius: 4,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  kpiValue: {
    fontSize: 16,
    fontWeight: '800',
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 16,
    marginBottom: 10,
    opacity: 0.6,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  emptySubtitle: {
    fontSize: 13,
    fontWeight: '500',
    textAlign: 'center',
  },
  loadingState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 13,
    fontWeight: '600',
  },
  errorState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 20,
  },
  errorTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  errorMessage: {
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 6,
    marginTop: 12,
  },
  retryText: {
    color: 'white',
    fontWeight: '700',
    fontSize: 12,
    textAlign: 'center',
  },
});
