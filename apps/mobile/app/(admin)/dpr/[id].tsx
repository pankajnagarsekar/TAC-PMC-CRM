// DPR DETAIL/EDIT SCREEN (ADMIN)
// View, edit, and approve Daily Progress Reports
// Admin can edit ALL fields regardless of status and approve DPRs
// Shows editable worker log grid instead of weather/manpower/issues
// UI-3: Version selector for viewing historical snapshots
// M10: Admin can view images and edit captions

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TextInput,
  ScrollView,
  Pressable,
  Alert,
  ActivityIndicator,
  Platform,
  Image,
  RefreshControl,
  TouchableOpacity,
  Linking,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { baseApiClient, authApi, dprApi, workerLogsApi } from '../../../services/apiClient';
import { useTheme } from '../../../contexts/ThemeContext';
import VersionSelector from '../../../components/VersionSelector';
import { DPR, WorkerLog, WorkerLogEntry } from '../../../types/api';

export default function DPRDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors: Colors, spacing: Spacing, typography: Typography, borderRadius: BorderRadius, isDark } = useTheme();
  
  const styles = useMemo(() => getStyles(Colors, Spacing, BorderRadius), [Colors, Spacing, BorderRadius]);

  const [dpr, setDpr] = useState<DPR | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [generatingPdf, setGeneratingPdf] = useState(false);
  const [isViewingHistorical, setIsViewingHistorical] = useState(false);

  // Editable fields
  const [progressNotes, setProgressNotes] = useState('');

  // Worker log state
  const [workerLogs, setWorkerLogs] = useState<WorkerLog[]>([]);
  const [editableEntries, setEditableEntries] = useState<Record<string, WorkerLogEntry[]>>({});
  const [workerLogLoading, setWorkerLogLoading] = useState(false);
  const [savingWorkerLog, setSavingWorkerLog] = useState(false);

  // M10: Image caption editing
  const [imageCaptions, setImageCaptions] = useState<Record<string, string>>({});
  const [expandedImageId, setExpandedImageId] = useState<string | null>(null);

  const showAlert = (title: string, message: string, onDismiss?: () => void) => {
    if (Platform.OS === 'web') {
      alert(`${title}\n\n${message}`);
      onDismiss?.();
    } else {
      Alert.alert(title, message, [{ text: 'OK', onPress: onDismiss }]);
    }
  };

  const fetchWorkerLogs = useCallback(async (projectId: string, dprDate: string) => {
    setWorkerLogLoading(true);
    try {
      const dateStr = dprDate.substring(0, 10);
      const logs = await workerLogsApi.getAll(projectId, { date: dateStr });
      setWorkerLogs(logs);

      const editable: Record<string, WorkerLogEntry[]> = {};
      logs.forEach((log: WorkerLog) => {
        const logId = log.log_id;
        if (!logId) return;

        editable[logId] = (log.entries || []).map((e: WorkerLogEntry) => ({
          vendor_name: e.vendor_name || '',
          workers_count: e.workers_count || 0,
          skill_type: e.skill_type || '',
          rate_per_worker: e.rate_per_worker || 0,
          remarks: e.remarks || '',
        }));
      });
      setEditableEntries(editable);
    } catch (error) {
      console.error('Error fetching worker logs:', error);
    } finally {
      setWorkerLogLoading(false);
    }
  }, []);

  const fetchDPR = useCallback(async () => {
    if (!id) return;

    try {
      const response = await dprApi.getById(id);
      setDpr(response as DPR);
      setProgressNotes(response.progress_notes || '');

      // M10: Initialize image captions
      const captions: Record<string, string> = {};
      response.images?.forEach(img => {
        captions[img.image_id] = img.caption || '';
      });
      setImageCaptions(captions);

      // Fetch worker logs for this project + date
      if (response.project_id && response.dpr_date) {
        fetchWorkerLogs(response.project_id, response.dpr_date);
      }
    } catch (error: unknown) {
      console.error('Error fetching DPR:', error);
      const msg = error instanceof Error ? error.message : 'Failed to load DPR';
      showAlert('Error', msg);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id, fetchWorkerLogs]);

  useEffect(() => {
    fetchDPR();
  }, [fetchDPR]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchDPR();
  };

  const handleSave = async () => {
    if (!dpr) return;

    setSaving(true);
    try {
      await dprApi.update(id!, {
        progress_notes: progressNotes || undefined,
      });
      showAlert('Success', 'DPR updated successfully');
      setEditing(false);
      fetchDPR();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to update DPR';
      showAlert('Error', msg);
    } finally {
      setSaving(false);
    }
  };

  // Save worker log entries
  const handleSaveWorkerLog = async (logId: string) => {
    setSavingWorkerLog(true);
    try {
      const entries = editableEntries[logId] || [];
      await baseApiClient.put(`/api/v1/worker-logs/${logId}`, {
        entries: entries.map(e => ({
          vendor_name: e.vendor_name,
          workers_count: e.workers_count,
          skill_type: e.skill_type,
          rate_per_worker: e.rate_per_worker,
          remarks: e.remarks,
        })),
      });
      showAlert('Success', 'Worker log updated successfully');
      if (dpr) fetchWorkerLogs(dpr.project_id, dpr.dpr_date);
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to save worker log';
      showAlert('Error', msg);
    } finally {
      setSavingWorkerLog(false);
    }
  };

  // Update a single worker log entry
  const updateWorkerEntry = (logId: string, index: number, field: keyof WorkerLogEntry, value: string | number) => {
    setEditableEntries(prev => {
      const entries = [...(prev[logId] || [])];
      entries[index] = { ...entries[index], [field]: value } as WorkerLogEntry;
      return { ...prev, [logId]: entries };
    });
  };

  // Add a new worker entry to a log
  const addWorkerEntry = (logId: string) => {
    setEditableEntries(prev => {
      const entries = [...(prev[logId] || [])];
      entries.push({ vendor_name: '', workers_count: 0, skill_type: '', rate_per_worker: 0, remarks: '' });
      return { ...prev, [logId]: entries };
    });
  };

  // Remove a worker entry from a log
  const removeWorkerEntry = (logId: string, index: number) => {
    setEditableEntries(prev => {
      const entries = [...(prev[logId] || [])];
      entries.splice(index, 1);
      return { ...prev, [logId]: entries };
    });
  };

  // M10: Save image caption
  const saveImageCaption = async (imageId: string) => {
    if (!dpr) return;

    setSaving(true);
    try {
      await baseApiClient.put(`/api/v1/dprs/${id}/images/${imageId}`, {
        caption: imageCaptions[imageId] || '',
      });
      showAlert('Success', 'Caption updated successfully');
      setExpandedImageId(null);
      fetchDPR();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to update caption';
      showAlert('Error', msg);
    } finally {
      setSaving(false);
    }
  };


  // Admin: Approve DPR
  const handleApprove = async () => {
    if (!dpr) return;
    setSaving(true);
    try {
      await dprApi.update(id!, {
        status: 'approved',
      });
      showAlert('Success', 'DPR approved successfully');
      fetchDPR();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to approve DPR';
      showAlert('Error', msg);
    } finally {
      setSaving(false);
    }
  };

  const addPhoto = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        quality: 0.7,
        base64: true,
      });

      if (!result.canceled && result.assets[0]) {
        setSaving(true);
        await dprApi.uploadImage(id!, {
          dpr_id: id,
          image_data: result.assets[0].base64,
          caption: '',
        });
        showAlert('Success', 'Photo added!');
        fetchDPR();
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to add photo';
      showAlert('Error', msg);
    } finally {
      setSaving(false);
    }
  };

  const generatePDF = async () => {
    if (!dpr) return;

    setGeneratingPdf(true);
    try {
      const token = await authApi.getToken();
      const baseUrl = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      const url = `${baseUrl}/api/v1/dprs/${id}/generate-pdf?token=${token}`;

      // Use Linking to open the PDF URL which triggers the download
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        // Force opening in browser to ensure download headers are respected
        await Linking.openURL(url);
      } else {
        showAlert('Error', 'Could not open the download URL in your browser.');
      }
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : 'Failed to trigger PDF download';
      showAlert('Error', msg);
    } finally {
      setGeneratingPdf(false);
    }
  };

  // UI-3: Handle version selection
  const handleVersionSelect = (version: number, snapshotData: unknown | null) => {
    if (snapshotData) {
      // Backend returns the data object directly now
      // Check if it's a string (old format) or object (new format)
      let historicalDpr: DPR;

      const data = snapshotData as any;
      if (typeof data === 'string') {
        try {
          historicalDpr = JSON.parse(data);
        } catch (e) {
          console.error('Failed to parse historical DPR string', e);
          return;
        }
      } else if (data.data_json) {
        // Handle case where it's wrapped (original expectation)
        historicalDpr = typeof data.data_json === 'string'
          ? JSON.parse(data.data_json)
          : data.data_json;
      } else {
        historicalDpr = data as DPR;
      }

      setDpr(historicalDpr);
      setProgressNotes(historicalDpr.progress_notes || '');
      setIsViewingHistorical(true);
      setEditing(false);
    } else {
      setIsViewingHistorical(false);
      fetchDPR();
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'approved': return Colors.success;
      case 'submitted': return Colors.primary; // Use Primary (Gold) for Submitted
      case 'draft': return Colors.warning;
      case 'rejected': return Colors.error;
      default: return Colors.textMuted;
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={[styles.loadingText, { color: Colors.textSecondary }]}>Retrieving DPR...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!dpr) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle" size={48} color={Colors.error} />
          <Text style={[styles.errorText, { color: Colors.error }]}>DPR not found</Text>
          <Pressable style={[styles.backButton, { backgroundColor: Colors.primary }]} onPress={() => router.back()}>
            <Text style={{ color: Colors.textInverse, fontWeight: '700' }}>Go Back</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const totalWorkerCount = workerLogs.reduce((sum, log) => sum + (log.total_workers || 0), 0);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]} edges={['left', 'right']}>
      <StatusBar barStyle={isDark ? "light-content" : "dark-content"} />
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
      >
        {/* UI-3: Version Selector */}
        <VersionSelector
          entityType="dpr"
          entityId={id || ''}
          currentVersion={dpr.version || 1}
          onVersionSelect={handleVersionSelect}
        />

        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Text style={[styles.title, { color: Colors.text, ...Typography.heading2 }]}>Daily Report</Text>
            <Text style={[styles.date, { color: Colors.textMuted, ...Typography.overline }]}>
                {new Date(dpr.dpr_date).toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
            </Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: getStatusColor(dpr.status) + '20' }]}>
            <Text style={[styles.statusText, { color: getStatusColor(dpr.status), ...Typography.overline }]}>
              {dpr.status}
            </Text>
          </View>
        </View>

        {/* Project Info Card */}
        <View style={[styles.infoCard, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
          <Text style={[styles.projectName, { color: Colors.text, ...Typography.subtitle }]}>{dpr.project_name || 'Unknown Project'}</Text>
          
          <View style={[styles.infoRow, { borderTopColor: Colors.border }]}>
            <View style={styles.infoItem}>
              <Text style={[styles.cardTitle, { color: Colors.textMuted, ...Typography.caption }]}>Created By</Text>
              <Text style={[styles.infoValue, { color: Colors.textSecondary }]}>{dpr.created_by_name || 'Supervisor'}</Text>
            </View>
            <View style={styles.infoItem}>
              <Text style={[styles.cardTitle, { color: Colors.textMuted, ...Typography.caption }]}>Weather</Text>
              <Text style={[styles.infoValue, { color: Colors.textSecondary }]}>{dpr.weather_conditions || 'Clear Skies'}</Text>
            </View>
          </View>
        </View>

        {/* Progress Notes Section */}
        <View style={[styles.section, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.subtitle }]}>Progress Notes</Text>
            {!isViewingHistorical && (
              <Pressable onPress={() => setEditing(!editing)}>
                <Ionicons
                  name={editing ? "checkmark-circle" : "create-outline"}
                  size={24}
                  color={Colors.primary}
                />
              </Pressable>
            )}
          </View>

          {editing && !isViewingHistorical ? (
            <>
              <TextInput
                style={[styles.input, styles.textArea, { backgroundColor: Colors.background, borderColor: Colors.border, color: Colors.text }]}
                value={progressNotes}
                onChangeText={setProgressNotes}
                placeholder="Describe today's work progress..."
                multiline
                placeholderTextColor={Colors.textMuted}
              />
              <TouchableOpacity
                style={[styles.saveButton, { backgroundColor: Colors.primary }, saving && styles.buttonDisabled]}
                onPress={handleSave}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator color={Colors.textInverse} />
                ) : (
                  <Text style={[styles.saveButtonText, { color: Colors.textInverse }]}>Update Notes</Text>
                )}
              </TouchableOpacity>
            </>
          ) : (
            <Text style={[dpr.progress_notes ? styles.detailValue : styles.emptyText, { color: Colors.text }]}>
              {dpr.progress_notes || 'No detailed notes provided for this report.'}
            </Text>
          )}
        </View>

        {/* Worker Log Grid Section */}
        <View style={[styles.section, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.subtitle }]}>Workforce Log</Text>
            {totalWorkerCount > 0 && (
              <View style={[styles.workerCountBadge, { backgroundColor: Colors.primary }]}>
                <Ionicons name="people" size={12} color={Colors.textInverse} />
                <Text style={[styles.workerCountText, { color: Colors.textInverse }]}>{totalWorkerCount}</Text>
              </View>
            )}
          </View>

          {workerLogLoading ? (
            <View style={styles.workerLogLoading}>
              <ActivityIndicator size="small" color={Colors.primary} />
            </View>
          ) : workerLogs.length === 0 ? (
            <View style={styles.emptyWorkerLog}>
              <Ionicons name="people-outline" size={32} color={Colors.textMuted} />
              <Text style={[styles.emptyText, { color: Colors.textMuted }]}>No workforce logs for this date</Text>
            </View>
          ) : (
            workerLogs.map((log: WorkerLog) => {
              const logId = log.log_id;
              if (!logId) return null;
              const entries = editableEntries[logId] || [];
              return (
                <View key={logId} style={[styles.workerLogCard, { backgroundColor: Colors.background, borderColor: Colors.border }]}>
                  <View style={[styles.workerLogHeader, { borderBottomColor: Colors.border }]}>
                    <View style={styles.workerLogHeaderInfo}>
                      <Text style={[styles.workerLogSupervisor, { color: Colors.text }]}>
                        <Ionicons name="person-outline" size={14} color={Colors.primary} /> {log.supervisor_name || 'Supervisor'}
                      </Text>
                      <Text style={[styles.workerLogMeta, { color: Colors.textMuted }]}>
                        {entries.length} segments • {
                          entries.reduce((s, e) => s + (e.workers_count || 0), 0)
                        } total workers
                      </Text>
                    </View>
                  </View>

                  {/* Grid Header */}
                  <View style={[styles.gridHeader, { borderBottomColor: Colors.border }]}>
                    <Text style={[styles.gridHeaderText, { flex: 2, color: Colors.textSecondary }]}>Vendor</Text>
                    <Text style={[styles.gridHeaderText, { flex: 1, color: Colors.textSecondary, textAlign: 'center' }]}>Qty</Text>
                    <Text style={[styles.gridHeaderText, { flex: 2, color: Colors.textSecondary }]}>Remarks</Text>
                    {!isViewingHistorical && <Text style={{ width: 30 }}></Text>}
                  </View>

                  {/* Grid Rows */}
                  {entries.map((entry, idx) => (
                    <View key={`${logId}-entry-${idx}`} style={[styles.gridRow, { borderBottomColor: Colors.border + '30' }]}>
                      <TextInput
                        style={[styles.gridCell, { flex: 2, backgroundColor: Colors.surface, borderColor: Colors.border, color: Colors.text }]}
                        value={entry.vendor_name}
                        onChangeText={(v) => updateWorkerEntry(logId, idx, 'vendor_name', v)}
                        placeholder="Name"
                        placeholderTextColor={Colors.textMuted}
                        editable={!isViewingHistorical}
                      />
                      <TextInput
                        style={[styles.gridCell, { flex: 1, textAlign: 'center', backgroundColor: Colors.surface, borderColor: Colors.border, color: Colors.text }]}
                        value={entry.workers_count?.toString() || ''}
                        onChangeText={(v) => updateWorkerEntry(logId, idx, 'workers_count', parseInt(v) || 0)}
                        keyboardType="number-pad"
                        placeholder="0"
                        placeholderTextColor={Colors.textMuted}
                        editable={!isViewingHistorical}
                      />
                      <TextInput
                        style={[styles.gridCell, { flex: 2, backgroundColor: Colors.surface, borderColor: Colors.border, color: Colors.text }]}
                        value={entry.remarks}
                        onChangeText={(v) => updateWorkerEntry(logId, idx, 'remarks', v)}
                        placeholder="..."
                        placeholderTextColor={Colors.textMuted}
                        editable={!isViewingHistorical}
                      />
                      {!isViewingHistorical && (
                        <TouchableOpacity
                          style={styles.removeEntryBtn}
                          onPress={() => removeWorkerEntry(logId, idx)}
                        >
                          <Ionicons name="close-circle" size={20} color={Colors.error} />
                        </TouchableOpacity>
                      )}
                    </View>
                  ))}

                  {/* Add Entry + Save Row */}
                  {!isViewingHistorical && (
                    <View style={styles.workerLogActions}>
                      <TouchableOpacity
                        style={styles.addEntryBtn}
                        onPress={() => addWorkerEntry(logId)}
                      >
                        <Ionicons name="add-circle-outline" size={18} color={Colors.primary} />
                        <Text style={[styles.addEntryText, { color: Colors.primary }]}>Add Row</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.saveWorkerLogBtn, { backgroundColor: Colors.success }, savingWorkerLog && styles.buttonDisabled]}
                        onPress={() => handleSaveWorkerLog(logId)}
                        disabled={savingWorkerLog}
                      >
                        {savingWorkerLog ? (
                          <ActivityIndicator size="small" color={Colors.textInverse} />
                        ) : (
                          <>
                            <Ionicons name="save-outline" size={16} color={Colors.textInverse} />
                            <Text style={[styles.saveWorkerLogText, { color: Colors.textInverse }]}>Save</Text>
                          </>
                        )}
                      </TouchableOpacity>
                    </View>
                  )}
                </View>
              );
            })
          )}
        </View>

        {/* Photos Section */}
        <View style={[styles.section, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
          <View style={styles.sectionHeader}>
            <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.subtitle }]}>Site Photos ({dpr.images.length})</Text>
            {!isViewingHistorical && (
              <TouchableOpacity style={[styles.addPhotoBtn, { backgroundColor: Colors.primary + '15' }]} onPress={addPhoto}>
                <Ionicons name="camera-outline" size={18} color={Colors.primary} />
                <Text style={{ color: Colors.primary, fontWeight: '700', marginLeft: 4 }}>Add</Text>
              </TouchableOpacity>
            )}
          </View>

          {dpr.images.length === 0 ? (
            <View style={styles.emptyPhotos}>
              <Ionicons name="images-outline" size={40} color={Colors.textMuted} />
              <Text style={[styles.emptyText, { color: Colors.textMuted }]}>No images captured yet</Text>
            </View>
          ) : (
            <View style={styles.photoGrid}>
              {dpr.images.map((img, idx) => {
                const isExpanded = expandedImageId === img.image_id;
                const photoKey = img.image_id || `photo-${idx}`;
                return (
                  <View key={photoKey} style={[styles.photoCard, { borderColor: Colors.border }]}>
                    <TouchableOpacity
                      style={styles.photoHeader}
                      onPress={() => setExpandedImageId(isExpanded ? null : img.image_id)}
                    >
                      <View style={styles.photoHeaderLeft}>
                        <Ionicons name="image-outline" size={20} color={Colors.primary} />
                        <Text style={[styles.photoNumber, { color: Colors.text, fontWeight: '700' }]}>#{idx + 1}</Text>
                        {!isExpanded && imageCaptions[img.image_id] && (
                          <Text style={[styles.photoPreview, { color: Colors.textMuted }]} numberOfLines={1}>
                            - {imageCaptions[img.image_id]}
                          </Text>
                        )}
                      </View>
                      <Ionicons
                        name={isExpanded ? "chevron-up" : "chevron-down"}
                        size={20}
                        color={Colors.textMuted}
                      />
                    </TouchableOpacity>

                    {isExpanded && (
                      <View style={styles.photoContent}>
                        <Image
                          source={{ uri: img.image_url || (img.image_data?.startsWith('data:') ? img.image_data : `data:image/jpeg;base64,${img.image_data}`) || 'https://via.placeholder.com/300' }}
                          style={[styles.photo, { borderRadius: 12 }]}
                          resizeMode="cover"
                        />

                        <Text style={[styles.captionLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Caption</Text>
                        <TextInput
                          style={[styles.captionInput, { backgroundColor: Colors.background, borderColor: Colors.border, color: Colors.text }]}
                          value={imageCaptions[img.image_id] || ''}
                          onChangeText={(text) => setImageCaptions(prev => ({
                            ...prev,
                            [img.image_id]: text
                          }))}
                          placeholder="What is happening in this photo?"
                          multiline
                          numberOfLines={2}
                          placeholderTextColor={Colors.textMuted}
                        />

                        <TouchableOpacity
                          style={[styles.saveCaptionBtn, { backgroundColor: Colors.primary }, saving && styles.buttonDisabled]}
                          onPress={() => saveImageCaption(img.image_id)}
                          disabled={saving}
                        >
                          {saving ? (
                            <ActivityIndicator color={Colors.textInverse} size="small" />
                          ) : (
                            <Text style={{ color: Colors.textInverse, fontWeight: '700' }}>Update Caption</Text>
                          )}
                        </TouchableOpacity>
                      </View>
                    )}
                  </View>
                );
              })}
            </View>
          )}

          {dpr.images.length > 0 && dpr.images.length < 4 && (
            <View style={[styles.warningBox, { backgroundColor: Colors.error + '10' }]}>
                <Ionicons name="alert-circle" size={16} color={Colors.error} />
                <Text style={{ color: Colors.error, fontSize: 11, fontWeight: '600', marginLeft: 6 }}>
                    Requires {4 - dpr.images.length} more photo(s) for submission.
                </Text>
            </View>
          )}
        </View>

        {/* Action Buttons */}
        <View style={styles.actions}>
          {!isViewingHistorical && (
            <TouchableOpacity
              style={[styles.approveButton, { backgroundColor: Colors.success }, saving && styles.buttonDisabled]}
              onPress={handleApprove}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color={Colors.textInverse} />
              ) : (
                <>
                  <Ionicons name="checkmark-done" size={20} color={Colors.textInverse} />
                  <Text style={[styles.approveButtonText, { color: Colors.textInverse }]}>
                    {dpr.status === 'approved' ? 'RE-APPROVE' : 'APPROVE REPORT'}
                  </Text>
                </>
              )}
            </TouchableOpacity>
          )}

          <TouchableOpacity
            style={[styles.pdfButton, { borderColor: Colors.primary }, generatingPdf && styles.buttonDisabled]}
            onPress={generatePDF}
            disabled={generatingPdf || dpr.images.length === 0}
          >
            {generatingPdf ? (
              <ActivityIndicator color={Colors.primary} />
            ) : (
              <>
                <Ionicons name="document-text-outline" size={20} color={Colors.primary} />
                <Text style={[styles.pdfButtonText, { color: Colors.primary }]}>DOWNLOAD PDF</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const getStyles = (Colors: any, Spacing: any, BorderRadius: any) => StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: Spacing.md, fontWeight: '600' },
  errorContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: Spacing.xl },
  errorText: { fontWeight: '700', fontSize: 18, marginTop: Spacing.md },
  backButton: { marginTop: Spacing.lg, paddingHorizontal: 24, paddingVertical: 12, borderRadius: 12 },
  content: { padding: Spacing.md, paddingBottom: 60 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: Spacing.lg, paddingHorizontal: 4 },
  headerLeft: { flex: 1 },
  title: { fontWeight: '800' },
  date: { marginTop: 4, letterSpacing: 0.5 },
  statusBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10 },
  statusText: { fontWeight: '800' },
  infoCard: { padding: Spacing.lg, borderRadius: 20, marginBottom: Spacing.md, borderWidth: 1 },
  cardTitle: { marginBottom: 2, letterSpacing: 0.5 },
  projectName: { fontWeight: '700', marginBottom: Spacing.md },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', borderTopWidth: 1, paddingTop: Spacing.md },
  infoItem: { flex: 1 },
  infoValue: { fontWeight: '700', fontSize: 13 },
  section: { padding: Spacing.lg, borderRadius: 20, marginBottom: Spacing.md, borderWidth: 1 },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: Spacing.lg },
  sectionTitle: { fontWeight: '700', letterSpacing: 0.5 },
  input: { borderRadius: 12, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, fontSize: 14, borderWidth: 1 },
  textArea: { minHeight: 100, textAlignVertical: 'top' },
  saveButton: { paddingVertical: 14, borderRadius: 12, alignItems: 'center', marginTop: Spacing.md },
  saveButtonText: { fontWeight: '700' },
  buttonDisabled: { opacity: 0.6 },
  detailValue: { fontSize: 15, lineHeight: 22 },
  emptyText: { fontStyle: 'italic', opacity: 0.6, textAlign: 'center', paddingVertical: 10 },

  workerCountBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  workerCountText: { fontSize: 11, fontWeight: '800' },
  workerLogLoading: { padding: Spacing.lg },
  emptyWorkerLog: { alignItems: 'center', paddingVertical: Spacing.lg, gap: 8 },
  workerLogCard: { borderRadius: 16, padding: Spacing.md, marginBottom: Spacing.md, borderWidth: 1 },
  workerLogHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingBottom: Spacing.sm, marginBottom: Spacing.md, borderBottomWidth: 1 },
  workerLogHeaderInfo: { flex: 1 },
  workerLogSupervisor: { fontWeight: '700' },
  workerLogMeta: { fontSize: 11, marginTop: 2 },
  gridHeader: { flexDirection: 'row', alignItems: 'center', paddingBottom: 8, borderBottomWidth: 1 },
  gridHeaderText: { fontSize: 10, fontWeight: '800', textTransform: 'uppercase' },
  gridRow: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 6, borderBottomWidth: 1 },
  gridCell: { fontSize: 12, borderWidth: 1, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 8 },
  removeEntryBtn: { width: 30, alignItems: 'center' },
  workerLogActions: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: Spacing.md },
  addEntryBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  addEntryText: { fontWeight: '700', fontSize: 13 },
  saveWorkerLogBtn: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8, gap: 6 },
  saveWorkerLogText: { fontWeight: '700', fontSize: 13 },

  addPhotoBtn: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10 },
  emptyPhotos: { alignItems: 'center', paddingVertical: 40, gap: 12 },
  photoGrid: { gap: Spacing.md },
  photoCard: { borderRadius: 16, borderWidth: 1, overflow: 'hidden' },
  photoHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: Spacing.md },
  photoHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: 8, flex: 1 },
  photoNumber: { fontSize: 14 },
  photoPreview: { fontSize: 12, marginLeft: 4 },
  photoContent: { padding: Spacing.md, paddingTop: 0 },
  photo: { width: '100%', height: 200, marginBottom: Spacing.md },
  captionLabel: { marginBottom: 6, letterSpacing: 1 },
  captionInput: { borderRadius: 10, padding: 10, borderWidth: 1, fontSize: 13, marginBottom: Spacing.md },
  saveCaptionBtn: { paddingVertical: 10, borderRadius: 10, alignItems: 'center' },
  warningBox: { flexDirection: 'row', alignItems: 'center', padding: 10, borderRadius: 8, marginTop: Spacing.md },
  
  actions: { gap: Spacing.md, marginTop: Spacing.xl },
  approveButton: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingVertical: 16, borderRadius: 16, gap: 8 },
  approveButtonText: { fontWeight: '800', letterSpacing: 1 },
  pdfButton: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingVertical: 16, borderRadius: 16, borderWidth: 1, gap: 8 },
  pdfButtonText: { fontWeight: '800', letterSpacing: 1 },
});
