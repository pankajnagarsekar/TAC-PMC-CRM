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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useProject } from '../../contexts/ProjectContext';
import { useRouter } from 'expo-router';
import { apiClient, authApi } from '../../services/apiClient';
import { Card, Input, Button } from '../../components/ui';
import { useTheme } from '../../contexts/ThemeContext';
import * as Linking from 'expo-linking';
import DateTimePicker, { DateTimePickerEvent } from '@react-native-community/datetimepicker';

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

  const { colors: Colors, spacing: Spacing, fontSizes: FontSizes, borderRadius: BorderRadius } = useTheme();
  const styles = React.useMemo(() => getStyles(Colors, Spacing, FontSizes, BorderRadius), [Colors, Spacing, FontSizes, BorderRadius]);

  const [activeTab, setActiveTab] = useState<TabType>('supervisor');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pdfExporting, setPdfExporting] = useState(false);

  // Filters
  const [dateFilter, setDateFilter] = useState(() => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  });
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [supervisorSearch, setSupervisorSearch] = useState('');
  const [vendorFilter, setVendorFilter] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Date Picker visibility
  const [showStartPicker, setShowStartPicker] = useState(false);
  const [showEndPicker, setShowEndPicker] = useState(false);

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
      const start = startDate || dateFilter;
      const end = endDate || dateFilter;
      const isRange = !!(startDate || endDate);

      // Fetch supervisor attendance
      const attendanceUrl = isRange
        ? `/api/v1/attendance/admin/all?project_id=${projectId}&start_date=${start}&end_date=${end}&search=${supervisorSearch}`
        : `/api/v1/attendance/admin/all?project_id=${projectId}&date=${dateFilter}&search=${supervisorSearch}`;

      const attendanceData = await apiClient.get<any>(attendanceUrl);
      setSupervisorRecords(attendanceData.attendance || []);

      // Fetch worker logs
      const workerUrl = isRange
        ? `/api/worker-logs?project_id=${projectId}&start_date=${start}&end_date=${end}&vendor=${vendorFilter}`
        : `/api/worker-logs?project_id=${projectId}&date=${dateFilter}&vendor=${vendorFilter}`;

      const workerData = await apiClient.get<any>(workerUrl);
      const logs = Array.isArray(workerData) ? workerData : (workerData.logs || []);
      setWorkerLogs(logs);
    } catch (err: any) {
      console.error('Error fetching attendance:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId, dateFilter, startDate, endDate, supervisorSearch, vendorFilter]);

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
    // Reset range when using single day navigator
    setStartDate('');
    setEndDate('');
  };

  const handleExport = async () => {
    if (!projectId) return;
    setExporting(true);
    try {
      const start = startDate || dateFilter;
      const end = endDate || dateFilter;

      const token = await authApi.getToken();

      const url = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/v1/attendance/export?project_id=${projectId}&start_date=${start}&end_date=${end}&search=${supervisorSearch}&vendor=${vendorFilter}&token=${token}`;

      await Linking.openURL(url);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const handleExportPdf = async () => {
    if (!projectId) return;
    setPdfExporting(true);
    try {
      const start = startDate || dateFilter;
      const end = endDate || dateFilter;
      const token = await authApi.getToken();

      const url = `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/v1/attendance/export-pdf?project_id=${projectId}&start_date=${start}&end_date=${end}&search=${supervisorSearch}&vendor=${vendorFilter}&token=${token}`;

      await Linking.openURL(url);
    } catch (err) {
      console.error('PDF Export failed:', err);
      alert('PDF Export failed. Please try again.');
    } finally {
      setPdfExporting(false);
    }
  };

  const onStartDateChange = (event: DateTimePickerEvent, selectedDate?: Date) => {
    setShowStartPicker(Platform.OS === 'ios');
    if (selectedDate) {
      setStartDate(selectedDate.toISOString().split('T')[0]);
    }
  };

  const onEndDateChange = (event: DateTimePickerEvent, selectedDate?: Date) => {
    setShowEndPicker(Platform.OS === 'ios');
    if (selectedDate) {
      setEndDate(selectedDate.toISOString().split('T')[0]);
    }
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
          <View>
            <Text style={styles.pageTitle}>Attendance</Text>
            <Text style={styles.projectLabel}>
              {(selectedProject as any)?.project_name || 'Project'}
            </Text>
          </View>
          <View style={styles.headerBtns}>
            <Pressable
              style={[styles.iconBtn, showFilters && styles.activeIconBtn]}
              onPress={() => setShowFilters(!showFilters)}
            >
              <Ionicons name="filter" size={20} color={showFilters ? Colors.primary : Colors.text} />
            </Pressable>
            <Pressable style={styles.iconBtn} onPress={handleExport} disabled={exporting}>
              {exporting ? (
                <ActivityIndicator size="small" color={Colors.primary} />
              ) : (
                <Ionicons name="document-text-outline" size={20} color={Colors.text} />
              )}
            </Pressable>
            <Pressable style={styles.iconBtn} onPress={handleExportPdf} disabled={pdfExporting}>
              {pdfExporting ? (
                <ActivityIndicator size="small" color={Colors.primary} />
              ) : (
                <Ionicons name="document-text" size={20} color={Colors.error} />
              )}
            </Pressable>
          </View>
        </View>

        {/* Advanced Filters */}
        {showFilters && (
          <Card style={styles.filterSection}>
            <View style={styles.filterRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.filterLabel}>Start Date</Text>
                <Pressable onPress={() => setShowStartPicker(true)}>
                  <View pointerEvents="none">
                    <Input
                      placeholder="YYYY-MM-DD"
                      value={startDate}
                      editable={false}
                      style={styles.filterInput}
                      rightIcon="calendar-outline"
                    />
                  </View>
                </Pressable>
                {showStartPicker && (
                  <DateTimePicker
                    value={startDate ? new Date(startDate) : new Date()}
                    mode="date"
                    display="default"
                    onChange={onStartDateChange}
                  />
                )}
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.filterLabel}>End Date</Text>
                <Pressable onPress={() => setShowEndPicker(true)}>
                  <View pointerEvents="none">
                    <Input
                      placeholder="YYYY-MM-DD"
                      value={endDate}
                      editable={false}
                      style={styles.filterInput}
                      rightIcon="calendar-outline"
                    />
                  </View>
                </Pressable>
                {showEndPicker && (
                  <DateTimePicker
                    value={endDate ? new Date(endDate) : new Date()}
                    mode="date"
                    display="default"
                    onChange={onEndDateChange}
                  />
                )}
              </View>
            </View>

            <View style={styles.filterRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.filterLabel}>{activeTab === 'supervisor' ? 'Supervisor Name' : 'Vendor Name'}</Text>
                <Input
                  placeholder={activeTab === 'supervisor' ? "Search supervisor..." : "Search vendor..."}
                  value={activeTab === 'supervisor' ? supervisorSearch : vendorFilter}
                  onChangeText={activeTab === 'supervisor' ? setSupervisorSearch : setVendorFilter}
                  style={styles.filterInput}
                />
              </View>
            </View>

            <View style={styles.filterActions}>
              <Button
                title="Clear Filters"
                variant="outline"
                size="sm"
                onPress={() => {
                  setStartDate('');
                  setEndDate('');
                  setSupervisorSearch('');
                  setVendorFilter('');
                }}
              />
              <Button
                title="Apply"
                size="sm"
                onPress={() => fetchData()}
              />
            </View>
          </Card>
        )}

        {/* Date Navigator (only show if no range is selected) */}
        {!startDate && !endDate && (
          <Card style={styles.dateNav} padding="none">
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
          </Card>
        )}

        {/* Summary Cards */}
        <View style={styles.summaryRow}>
          <Card style={[styles.summaryCard, { borderLeftColor: Colors.primary }]} padding="none">
            <Text style={styles.summaryNum}>{totalSupervisors}</Text>
            <Text style={styles.summaryLabel}>Supervisors</Text>
          </Card>
          <Card style={[styles.summaryCard, { borderLeftColor: Colors.accent }]} padding="none">
            <Text style={styles.summaryNum}>{totalWorkers}</Text>
            <Text style={styles.summaryLabel}>Workers</Text>
          </Card>
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
              <Card key={record.attendance_id} style={styles.recordCard}>
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
              </Card>
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
              <Card key={log.log_id} style={styles.recordCard}>
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
              </Card>
            ))
          )
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const getStyles = (Colors: any, Spacing: any, FontSizes: any, BorderRadius: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scrollContent: { padding: Spacing.md, paddingBottom: 100 },
  centerContent: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 80 },

  header: { marginBottom: Spacing.xl, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  headerBtns: { flexDirection: 'row', gap: Spacing.sm },
  iconBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: Colors.cardBg,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.border
  },
  activeIconBtn: { backgroundColor: Colors.primary + '10', borderColor: Colors.primary },
  pageTitle: { fontSize: 24, fontWeight: '700', color: Colors.text, fontFamily: 'Inter_700Bold' },
  projectLabel: { fontSize: FontSizes.sm, color: Colors.textSecondary, marginTop: 4, fontFamily: 'Inter_400Regular' },

  // Advanced Filters
  filterSection: { marginBottom: Spacing.lg, gap: Spacing.md },
  filterRow: { flexDirection: 'row', gap: Spacing.md },
  filterLabel: { fontSize: 12, fontWeight: '600', color: Colors.textSecondary, marginBottom: 4, fontFamily: 'Inter_600SemiBold' },
  filterInput: { backgroundColor: Colors.background, height: 40 },
  filterActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: Spacing.md, marginTop: Spacing.sm },

  // Date navigator
  dateNav: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  dateArrow: { padding: Spacing.md },
  dateCenter: { alignItems: 'center' },
  dateLabel: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text, fontFamily: 'Inter_600SemiBold' },
  dateValue: { fontSize: FontSizes.xs, color: Colors.textMuted, marginTop: 2, fontFamily: 'Inter_400Regular' },

  // Summary
  summaryRow: { flexDirection: 'row', gap: Spacing.md, marginBottom: Spacing.xl },
  summaryCard: {
    flex: 1,
    borderLeftWidth: 4,
    alignItems: 'center',
    padding: Spacing.lg,
  },
  summaryNum: { fontSize: 32, fontWeight: '700', color: Colors.text, fontFamily: 'Inter_700Bold' },
  summaryLabel: { fontSize: 10, color: Colors.textMuted, textTransform: 'uppercase', marginTop: 4, fontWeight: '600', fontFamily: 'Inter_600SemiBold' },

  // Tabs
  tabBar: {
    flexDirection: 'row',
    backgroundColor: Colors.cardBg,
    borderRadius: BorderRadius.lg,
    padding: 6,
    marginBottom: Spacing.xl,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
  },
  activeTab: { backgroundColor: Colors.primary + '10' },
  tabText: { fontSize: FontSizes.sm, color: Colors.textMuted, fontWeight: '500', fontFamily: 'Inter_500Medium' },
  activeTabText: { color: Colors.primary, fontWeight: '600', fontFamily: 'Inter_600SemiBold' },

  // Empty states
  emptySection: { alignItems: 'center', paddingVertical: 60, gap: Spacing.md },
  emptyText: { fontSize: FontSizes.md, color: Colors.textMuted, fontFamily: 'Inter_400Regular' },
  emptyTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text, marginTop: Spacing.md, fontFamily: 'Inter_600SemiBold' },
  selectBtn: { marginTop: Spacing.lg, backgroundColor: Colors.primary, paddingHorizontal: Spacing.xl, paddingVertical: Spacing.md, borderRadius: BorderRadius.md },
  selectBtnText: { color: Colors.white, fontWeight: '600', fontSize: FontSizes.md, fontFamily: 'Inter_600SemiBold' },

  // Record card
  recordCard: {
    marginBottom: Spacing.md,
  },
  recordHeader: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  avatarCircle: {
    width: 44, height: 44, borderRadius: 22, backgroundColor: Colors.primary + '15',
    alignItems: 'center', justifyContent: 'center',
  },
  avatarText: { fontSize: FontSizes.lg, fontWeight: '700', color: Colors.primary, fontFamily: 'Inter_700Bold' },
  recordInfo: { flex: 1 },
  recordName: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text, fontFamily: 'Inter_600SemiBold' },
  recordRole: { fontSize: FontSizes.xs, color: Colors.textMuted, fontFamily: 'Inter_400Regular' },
  statusBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: Spacing.md, paddingVertical: 4, borderRadius: BorderRadius.full },
  statusText: { fontSize: FontSizes.xs, fontWeight: '600', fontFamily: 'Inter_600SemiBold' },

  recordDetails: { marginTop: Spacing.md, gap: 6 },
  recordDetailItem: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  recordDetailText: { fontSize: FontSizes.sm, color: Colors.textSecondary, flex: 1, fontFamily: 'Inter_400Regular' },

  // Worker grid
  workerGrid: { marginTop: Spacing.md, borderTopWidth: 1, borderTopColor: Colors.border, paddingTop: Spacing.md },
  workerGridHeader: { flexDirection: 'row', paddingBottom: 6, borderBottomWidth: 1, borderBottomColor: Colors.border },
  workerGridHeaderText: { fontSize: 10, fontWeight: '700', color: Colors.textMuted, textTransform: 'uppercase', fontFamily: 'Inter_700Bold' },
  workerGridRow: { flexDirection: 'row', paddingVertical: 6, borderBottomWidth: 1, borderBottomColor: Colors.divider },
  workerGridCell: { fontSize: FontSizes.sm, color: Colors.text, fontFamily: 'Inter_400Regular' },
});
