// ADMIN ATTENDANCE VIEWER
// View supervisor and worker attendance per project
// Two tabs: Supervisor Attendance (selfie + GPS check-in) and Worker Attendance (from worker logs)

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  RefreshControl,
  Platform,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useProject } from '../../contexts/ProjectContext';
import { useRouter } from 'expo-router';
import { apiClient } from '../../services/apiClient';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';

type TabType = 'supervisor' | 'worker';

interface AttendanceRecord {
  attendance_id: string;
  user_id: string;
  user_name: string;
  role: string;
  project_id: string;
  project_name?: string;
  check_in_time: string;
  location?: { latitude: number; longitude: number; address?: string };
  status: string;
}

interface WorkerLogSummary {
  log_id: string;
  date: string;
  supervisor_name: string;
  total_workers: number;
  entries: { vendor_name: string; workers_count: number }[];
}

export default function AttendanceViewScreen() {
  const router = useRouter();
  const { selectedProject, isProjectSelected } = useProject();
  
  const [activeTab, setActiveTab] = useState<TabType>('supervisor');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [dateFilter, setDateFilter] = useState(new Date().toISOString().split('T')[0]);
  
  // Supervisor attendance
  const [supervisorRecords, setSupervisorRecords] = useState<AttendanceRecord[]>([]);
  
  // Worker attendance (from worker logs)
  const [workerLogs, setWorkerLogs] = useState<WorkerLogSummary[]>([]);

  const projectId = selectedProject
    ? (selectedProject as any).project_id || (selectedProject as any)._id
    : null;

  const fetchData = useCallback(async () => {
    if (!projectId) {
      setLoading(false);
      return;
    }

    try {
      // Fetch supervisor attendance
      const attendanceData = await apiClient.get<any>(
        `/api/v2/attendance/admin/all?project_id=${projectId}&date=${dateFilter}`
      );
      setSupervisorRecords(attendanceData.attendance || []);

      // Fetch worker logs for the same date
      const workerData = await apiClient.get<any>(
        `/api/worker-logs?project_id=${projectId}&date=${dateFilter}`
      );
      const logs = Array.isArray(workerData) ? workerData : (workerData.logs || []);
      setWorkerLogs(logs);
    } catch (err: any) {
      console.error('Error fetching attendance:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId, dateFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const changeDate = (days: number) => {
    const d = new Date(dateFilter);
    d.setDate(d.getDate() + days);
    setDateFilter(d.toISOString().split('T')[0]);
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoString;
    }
  };

  const formatDateLabel = (dateStr: string) => {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      const today = new Date().toISOString().split('T')[0];
      const yesterday = new Date(Date.now() - 86400000).toISOString().split('T')[0];
      if (dateStr === today) return 'Today';
      if (dateStr === yesterday) return 'Yesterday';
      return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  // No project selected
  if (!isProjectSelected) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContent}>
          <Ionicons name="business-outline" size={48} color={Colors.textMuted} />
          <Text style={styles.emptyTitle}>No Project Selected</Text>
          <Pressable style={styles.selectBtn} onPress={() => router.push('/(admin)/select-project' as any)}>
            <Text style={styles.selectBtnText}>Select Project</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const totalSupervisors = supervisorRecords.length;
  const totalWorkers = workerLogs.reduce((s, l) => s + (l.total_workers || 0), 0);

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.pageTitle}>Attendance</Text>
          <Text style={styles.projectLabel}>
            {(selectedProject as any)?.project_name || 'Project'}
          </Text>
        </View>

        {/* Date Navigator */}
        <View style={styles.dateNav}>
          <Pressable style={styles.dateArrow} onPress={() => changeDate(-1)}>
            <Ionicons name="chevron-back" size={22} color={Colors.primary} />
          </Pressable>
          <View style={styles.dateCenter}>
            <Text style={styles.dateLabel}>{formatDateLabel(dateFilter)}</Text>
            <Text style={styles.dateValue}>{dateFilter}</Text>
          </View>
          <Pressable style={styles.dateArrow} onPress={() => changeDate(1)}>
            <Ionicons name="chevron-forward" size={22} color={Colors.primary} />
          </Pressable>
        </View>

        {/* Summary Cards */}
        <View style={styles.summaryRow}>
          <View style={[styles.summaryCard, { borderLeftColor: Colors.primary }]}>
            <Text style={styles.summaryNum}>{totalSupervisors}</Text>
            <Text style={styles.summaryLabel}>Supervisors</Text>
          </View>
          <View style={[styles.summaryCard, { borderLeftColor: Colors.accent }]}>
            <Text style={styles.summaryNum}>{totalWorkers}</Text>
            <Text style={styles.summaryLabel}>Workers</Text>
          </View>
        </View>

        {/* Tabs */}
        <View style={styles.tabBar}>
          <Pressable
            style={[styles.tab, activeTab === 'supervisor' && styles.activeTab]}
            onPress={() => setActiveTab('supervisor')}
          >
            <Ionicons name="person" size={16} color={activeTab === 'supervisor' ? Colors.primary : Colors.textMuted} />
            <Text style={[styles.tabText, activeTab === 'supervisor' && styles.activeTabText]}>
              Supervisors ({totalSupervisors})
            </Text>
          </Pressable>
          <Pressable
            style={[styles.tab, activeTab === 'worker' && styles.activeTab]}
            onPress={() => setActiveTab('worker')}
          >
            <Ionicons name="people" size={16} color={activeTab === 'worker' ? Colors.accent : Colors.textMuted} />
            <Text style={[styles.tabText, activeTab === 'worker' && styles.activeTabText]}>
              Workers ({totalWorkers})
            </Text>
          </Pressable>
        </View>

        {loading ? (
          <View style={styles.centerContent}>
            <ActivityIndicator size="large" color={Colors.primary} />
          </View>
        ) : activeTab === 'supervisor' ? (
          /* Supervisor Attendance Tab */
          supervisorRecords.length === 0 ? (
            <View style={styles.emptySection}>
              <Ionicons name="person-outline" size={40} color={Colors.textMuted} />
              <Text style={styles.emptyText}>No supervisor attendance for this date</Text>
            </View>
          ) : (
            supervisorRecords.map((record) => (
              <View key={record.attendance_id} style={styles.recordCard}>
                <View style={styles.recordHeader}>
                  <View style={styles.avatarCircle}>
                    <Text style={styles.avatarText}>
                      {record.user_name?.charAt(0)?.toUpperCase() || '?'}
                    </Text>
                  </View>
                  <View style={styles.recordInfo}>
                    <Text style={styles.recordName}>{record.user_name}</Text>
                    <Text style={styles.recordRole}>{record.role}</Text>
                  </View>
                  <View style={[styles.statusBadge, { backgroundColor: '#dcfce7' }]}>
                    <Ionicons name="checkmark-circle" size={14} color="#16a34a" />
                    <Text style={[styles.statusText, { color: '#16a34a' }]}>Present</Text>
                  </View>
                </View>
                <View style={styles.recordDetails}>
                  <View style={styles.recordDetailItem}>
                    <Ionicons name="time" size={14} color={Colors.textMuted} />
                    <Text style={styles.recordDetailText}>
                      Check-in: {formatTime(record.check_in_time)}
                    </Text>
                  </View>
                  {record.location?.address && (
                    <View style={styles.recordDetailItem}>
                      <Ionicons name="location" size={14} color={Colors.textMuted} />
                      <Text style={styles.recordDetailText} numberOfLines={1}>
                        {record.location.address}
                      </Text>
                    </View>
                  )}
                  {record.location?.latitude && !record.location?.address && (
                    <View style={styles.recordDetailItem}>
                      <Ionicons name="location" size={14} color={Colors.textMuted} />
                      <Text style={styles.recordDetailText}>
                        GPS: {record.location.latitude.toFixed(4)}, {record.location.longitude.toFixed(4)}
                      </Text>
                    </View>
                  )}
                </View>
              </View>
            ))
          )
        ) : (
          /* Worker Attendance Tab */
          workerLogs.length === 0 ? (
            <View style={styles.emptySection}>
              <Ionicons name="people-outline" size={40} color={Colors.textMuted} />
              <Text style={styles.emptyText}>No worker logs for this date</Text>
            </View>
          ) : (
            workerLogs.map((log) => (
              <View key={log.log_id} style={styles.recordCard}>
                <View style={styles.recordHeader}>
                  <View style={[styles.avatarCircle, { backgroundColor: Colors.accent + '20' }]}>
                    <Ionicons name="people" size={18} color={Colors.accent} />
                  </View>
                  <View style={styles.recordInfo}>
                    <Text style={styles.recordName}>{log.supervisor_name || 'Supervisor'}</Text>
                    <Text style={styles.recordRole}>{log.total_workers} workers total</Text>
                  </View>
                </View>

                {/* Worker entries grid */}
                {(log.entries || []).length > 0 && (
                  <View style={styles.workerGrid}>
                    <View style={styles.workerGridHeader}>
                      <Text style={[styles.workerGridHeaderText, { flex: 2 }]}>Vendor</Text>
                      <Text style={[styles.workerGridHeaderText, { flex: 1, textAlign: 'center' }]}>Count</Text>
                    </View>
                    {(log.entries || []).map((entry, idx) => (
                      <View key={idx} style={styles.workerGridRow}>
                        <Text style={[styles.workerGridCell, { flex: 2 }]}>{entry.vendor_name || '—'}</Text>
                        <Text style={[styles.workerGridCell, { flex: 1, textAlign: 'center', fontWeight: '600' }]}>
                          {entry.workers_count}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}
              </View>
            ))
          )
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f2f5' },
  scrollContent: { padding: Spacing.md, paddingBottom: 100 },
  centerContent: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 60 },
  
  header: { marginBottom: Spacing.md },
  pageTitle: { fontSize: 24, fontWeight: '700', color: Colors.text },
  projectLabel: { fontSize: FontSizes.sm, color: Colors.textSecondary, marginTop: 2 },
  
  // Date navigator
  dateNav: { 
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: Colors.white, borderRadius: BorderRadius.lg, padding: Spacing.sm,
    marginBottom: Spacing.md,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 3, elevation: 2,
  },
  dateArrow: { padding: Spacing.sm },
  dateCenter: { alignItems: 'center' },
  dateLabel: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  dateValue: { fontSize: FontSizes.xs, color: Colors.textMuted, marginTop: 1 },
  
  // Summary
  summaryRow: { flexDirection: 'row', gap: Spacing.sm, marginBottom: Spacing.md },
  summaryCard: { 
    flex: 1, backgroundColor: Colors.white, borderRadius: BorderRadius.md, padding: Spacing.md,
    borderLeftWidth: 4, alignItems: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 3, elevation: 1,
  },
  summaryNum: { fontSize: 28, fontWeight: '700', color: Colors.text },
  summaryLabel: { fontSize: FontSizes.xs, color: Colors.textMuted, textTransform: 'uppercase', marginTop: 2 },
  
  // Tabs
  tabBar: { 
    flexDirection: 'row', backgroundColor: Colors.white, borderRadius: BorderRadius.lg,
    padding: 4, marginBottom: Spacing.md,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 3, elevation: 1,
  },
  tab: { 
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xs,
    paddingVertical: Spacing.sm, borderRadius: BorderRadius.md,
  },
  activeTab: { backgroundColor: '#f0f4ff' },
  tabText: { fontSize: FontSizes.sm, color: Colors.textMuted, fontWeight: '500' },
  activeTabText: { color: Colors.primary, fontWeight: '600' },
  
  // Empty states
  emptySection: { alignItems: 'center', paddingVertical: 40, gap: Spacing.sm },
  emptyText: { fontSize: FontSizes.md, color: Colors.textMuted },
  emptyTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text, marginTop: Spacing.md },
  selectBtn: { marginTop: Spacing.md, backgroundColor: Colors.primary, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, borderRadius: BorderRadius.md },
  selectBtnText: { color: Colors.white, fontWeight: '600' },
  
  // Record card
  recordCard: { 
    backgroundColor: Colors.white, borderRadius: BorderRadius.md, padding: Spacing.md,
    marginBottom: Spacing.sm,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.04, shadowRadius: 3, elevation: 1,
  },
  recordHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  avatarCircle: { 
    width: 40, height: 40, borderRadius: 20, backgroundColor: Colors.primary + '15',
    alignItems: 'center', justifyContent: 'center',
  },
  avatarText: { fontSize: FontSizes.lg, fontWeight: '700', color: Colors.primary },
  recordInfo: { flex: 1 },
  recordName: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  recordRole: { fontSize: FontSizes.xs, color: Colors.textMuted },
  statusBadge: { flexDirection: 'row', alignItems: 'center', gap: 3, paddingHorizontal: Spacing.sm, paddingVertical: 3, borderRadius: BorderRadius.full },
  statusText: { fontSize: FontSizes.xs, fontWeight: '600' },
  
  recordDetails: { marginTop: Spacing.sm, gap: 4 },
  recordDetailItem: { flexDirection: 'row', alignItems: 'center', gap: Spacing.xs },
  recordDetailText: { fontSize: FontSizes.sm, color: Colors.textSecondary, flex: 1 },
  
  // Worker grid
  workerGrid: { marginTop: Spacing.sm, borderTopWidth: 1, borderTopColor: Colors.border, paddingTop: Spacing.sm },
  workerGridHeader: { flexDirection: 'row', paddingBottom: 4, borderBottomWidth: 1, borderBottomColor: Colors.border },
  workerGridHeaderText: { fontSize: 10, fontWeight: '700', color: Colors.textMuted, textTransform: 'uppercase' },
  workerGridRow: { flexDirection: 'row', paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: '#f9fafb' },
  workerGridCell: { fontSize: FontSizes.sm, color: Colors.text },
});
