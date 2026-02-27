// DPR DETAIL/EDIT SCREEN (ADMIN)
// View, edit, and approve Daily Progress Reports
// Admin can edit ALL fields regardless of status and approve DPRs
// Shows editable worker log grid instead of weather/manpower/issues
// UI-3: Version selector for viewing historical snapshots
// M10: Admin can view images and edit captions

import React, { useState, useEffect, useCallback } from 'react';
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
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import * as Print from 'expo-print';
import * as Sharing from 'expo-sharing';
import { apiClient } from '../../../services/apiClient';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../../constants/theme';
import VersionSelector from '../../../components/VersionSelector';

interface DPRImage {
  image_id: string;
  image_url?: string;
  image_data?: string;
  caption?: string;
  uploaded_at?: string;
}

interface DPRDetail {
  dpr_id: string;
  project_id: string;
  project_name?: string;
  project_code?: string;
  dpr_date: string;
  status: string;
  progress_notes?: string;
  images: DPRImage[];
  created_at: string;
  updated_at?: string;
  version?: number;
  locked_flag?: boolean;
}

interface WorkerLogEntry {
  vendor_name: string;
  workers_count: number;
  skill_type: string;
  rate_per_worker: number;
  remarks: string;
}

interface WorkerLog {
  log_id: string;
  project_id: string;
  date: string;
  supervisor_name: string;
  entries: WorkerLogEntry[];
  total_workers: number;
}

export default function DPRDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams<{ id: string }>();
  
  const [dpr, setDpr] = useState<DPRDetail | null>(null);
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

  const fetchDPR = useCallback(async () => {
    if (!id) return;
    
    try {
      const response = await apiClient.get<DPRDetail>(`/api/v2/dpr/${id}`);
      setDpr(response);
      setProgressNotes(response.progress_notes || '');
      
      // M10: Initialize image captions
      const captions: Record<string, string> = {};
      response.images.forEach(img => {
        captions[img.image_id] = img.caption || '';
      });
      setImageCaptions(captions);
      
      // Fetch worker logs for this project + date
      if (response.project_id && response.dpr_date) {
        fetchWorkerLogs(response.project_id, response.dpr_date);
      }
    } catch (error: any) {
      console.error('Error fetching DPR:', error);
      showAlert('Error', error.message || 'Failed to load DPR');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  const fetchWorkerLogs = async (projectId: string, dprDate: string) => {
    setWorkerLogLoading(true);
    try {
      // Extract date as YYYY-MM-DD directly from dpr_date string
      // Avoid new Date().toISOString() which shifts timezone and can give wrong date
      const dateStr = dprDate.substring(0, 10);
      const data = await apiClient.get<any>(`/api/worker-logs?project_id=${projectId}&date=${dateStr}`);
      const logs = Array.isArray(data) ? data : (data.logs || []);
      setWorkerLogs(logs);
      
      // Initialize editable entries
      const editable: Record<string, WorkerLogEntry[]> = {};
      logs.forEach((log: WorkerLog) => {
        editable[log.log_id] = (log.entries || []).map((e: any) => ({
          vendor_name: e.vendor_name || '',
          workers_count: e.workers_count || 0,
          skill_type: e.skill_type || '',
          rate_per_worker: e.rate_per_worker || 0,
          remarks: e.remarks || e.purpose || '',
        }));
      });
      setEditableEntries(editable);
    } catch (error) {
      console.error('Error fetching worker logs:', error);
    } finally {
      setWorkerLogLoading(false);
    }
  };

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
      await apiClient.put(`/api/v2/dpr/${id}`, {
        progress_notes: progressNotes || undefined,
      });
      showAlert('Success', 'DPR updated successfully');
      setEditing(false);
      fetchDPR();
    } catch (error: any) {
      showAlert('Error', error.message || 'Failed to update DPR');
    } finally {
      setSaving(false);
    }
  };

  // Save worker log entries
  const handleSaveWorkerLog = async (logId: string) => {
    setSavingWorkerLog(true);
    try {
      const entries = editableEntries[logId] || [];
      await apiClient.put(`/api/worker-logs/${logId}`, {
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
    } catch (error: any) {
      showAlert('Error', error.message || 'Failed to save worker log');
    } finally {
      setSavingWorkerLog(false);
    }
  };

  // Update a single worker log entry
  const updateWorkerEntry = (logId: string, index: number, field: keyof WorkerLogEntry, value: any) => {
    setEditableEntries(prev => {
      const entries = [...(prev[logId] || [])];
      entries[index] = { ...entries[index], [field]: value };
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
      await apiClient.put(`/api/v2/dpr/${id}/images/${imageId}`, {
        caption: imageCaptions[imageId] || '',
      });
      showAlert('Success', 'Caption updated successfully');
      setExpandedImageId(null);
      fetchDPR();
    } catch (error: any) {
      showAlert('Error', error.message || 'Failed to update caption');
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    if (!dpr) return;
    
    if (dpr.images.length < 4) {
      showAlert('Cannot Submit', 'A minimum of 4 photos is required to submit a DPR.');
      return;
    }
    
    setSaving(true);
    try {
      await apiClient.post(`/api/v2/dpr/${id}/submit`);
      showAlert('Success', 'DPR submitted successfully');
      fetchDPR();
    } catch (error: any) {
      showAlert('Error', error.message || 'Failed to submit DPR');
    } finally {
      setSaving(false);
    }
  };

  // Admin: Approve DPR
  const handleApprove = async () => {
    if (!dpr) return;
    setSaving(true);
    try {
      await apiClient.put(`/api/v2/dpr/${id}`, {
        status: 'approved',
      });
      showAlert('Success', 'DPR approved successfully');
      fetchDPR();
    } catch (error: any) {
      showAlert('Error', error.message || 'Failed to approve DPR');
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
        await apiClient.post(`/api/v2/dpr/${id}/images`, {
          dpr_id: id,
          image_data: result.assets[0].base64,
          caption: '',
        });
        showAlert('Success', 'Photo added!');
        fetchDPR();
      }
    } catch (error: any) {
      showAlert('Error', error.message || 'Failed to add photo');
    } finally {
      setSaving(false);
    }
  };

  const generatePDF = async () => {
    if (!dpr) return;
    
    setGeneratingPdf(true);
    try {
      const dateObj = new Date(dpr.dpr_date);
      const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'];
      const formattedDate = `${monthNames[dateObj.getMonth()]}, ${String(dateObj.getDate()).padStart(2, '0')}, ${dateObj.getFullYear()}`;
      
      const photoPages = dpr.images.map((img, idx) => `
        <div style="page-break-after: always; height: 100vh; display: flex; flex-direction: column; padding: 30px; box-sizing: border-box;">
          <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #007AFF; margin: 0; font-size: 16px;">Photo ${idx + 1} of ${dpr.images.length}</h2>
            <p style="color: #666; margin: 5px 0 0; font-size: 12px;">${formattedDate}</p>
          </div>
          <div style="flex: 1; display: flex; align-items: center; justify-content: center; overflow: hidden;">
            <img src="${img.image_url || ''}" style="max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 8px;" />
          </div>
          <div style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #007AFF;">
            <p style="margin: 0; font-size: 14px; color: #333;">${img.caption || 'No caption'}</p>
          </div>
        </div>
      `).join('');
      
      const htmlContent = `
        <!DOCTYPE html>
        <html>
          <head><meta charset="utf-8"><title>DPR - ${formattedDate}</title>
            <style>
              @page { margin: 0; size: A4 portrait; }
              body { font-family: -apple-system, sans-serif; margin: 0; padding: 0; }
              .cover-page { height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 40px; box-sizing: border-box; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); page-break-after: always; }
              .cover-title { font-size: 32px; font-weight: bold; color: #1a1a1a; margin: 0 0 10px; text-align: center; }
              .cover-subtitle { font-size: 18px; color: #666; margin: 0 0 40px; }
              .cover-info { background: white; padding: 30px 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
              .cover-info-row { display: flex; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid #eee; }
              .cover-info-row:last-child { margin-bottom: 0; padding-bottom: 0; border-bottom: none; }
              .cover-info-label { font-weight: 600; color: #333; width: 100px; }
              .cover-info-value { color: #666; flex: 1; }
            </style>
          </head>
          <body>
            <div class="cover-page">
              <h1 class="cover-title">Daily Progress Report</h1>
              <p class="cover-subtitle">${formattedDate}</p>
              <div class="cover-info">
                <div class="cover-info-row">
                  <span class="cover-info-label">Project</span>
                  <span class="cover-info-value">${dpr.project_name || 'N/A'}</span>
                </div>
                <div class="cover-info-row">
                  <span class="cover-info-label">Date</span>
                  <span class="cover-info-value">${formattedDate}</span>
                </div>
                <div class="cover-info-row">
                  <span class="cover-info-label">Photos</span>
                  <span class="cover-info-value">${dpr.images.length} progress photos</span>
                </div>
              </div>
              ${dpr.progress_notes ? `
              <div style="margin-top: 30px; max-width: 400px; text-align: left;">
                <h3 style="font-size: 14px; color: #333; margin: 0 0 10px;">Progress Notes</h3>
                <p style="font-size: 12px; color: #666; margin: 0; line-height: 1.5;">${dpr.progress_notes}</p>
              </div>` : ''}
            </div>
            ${photoPages}
          </body>
        </html>
      `;
      
      const { uri } = await Print.printToFileAsync({ html: htmlContent, base64: false });
      
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(uri, {
          mimeType: 'application/pdf',
          dialogTitle: `DPR - ${formattedDate}`,
          UTI: 'com.adobe.pdf',
        });
      } else {
        showAlert('PDF Generated', `PDF saved at: ${uri}`);
      }
    } catch (error: any) {
      showAlert('Error', error.message || 'Failed to generate PDF');
    } finally {
      setGeneratingPdf(false);
    }
  };

  // UI-3: Handle version selection
  const handleVersionSelect = (version: number, snapshotData: any | null) => {
    if (snapshotData && snapshotData.data_json) {
      const historicalDpr = JSON.parse(snapshotData.data_json);
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
      case 'submitted': return Colors.info;
      case 'draft': return Colors.warning;
      case 'rejected': return Colors.error;
      default: return Colors.textMuted;
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading DPR...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!dpr) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Ionicons name="alert-circle" size={48} color={Colors.error} />
          <Text style={styles.errorText}>DPR not found</Text>
          <Pressable style={styles.backButton} onPress={() => router.back()}>
            <Text style={styles.backButtonText}>Go Back</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  const totalWorkerCount = workerLogs.reduce((sum, log) => sum + (log.total_workers || 0), 0);

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
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
            <Text style={styles.title}>Daily Progress Report</Text>
            <Text style={styles.date}>{new Date(dpr.dpr_date).toLocaleDateString()}</Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: getStatusColor(dpr.status) + '20' }]}>
            <Text style={[styles.statusText, { color: getStatusColor(dpr.status) }]}>
              {dpr.status}
            </Text>
          </View>
        </View>

        {/* Project Info */}
        <View style={styles.infoCard}>
          <Text style={styles.cardTitle}>Project</Text>
          <Text style={styles.projectName}>{dpr.project_name || 'Unknown Project'}</Text>
        </View>

        {/* Progress Notes Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Progress Notes</Text>
            {!isViewingHistorical && (
              <Pressable onPress={() => setEditing(!editing)}>
                <Ionicons 
                  name={editing ? "checkmark-circle" : "create"} 
                  size={24} 
                  color={Colors.primary} 
                />
              </Pressable>
            )}
          </View>

          {editing && !isViewingHistorical ? (
            <>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={progressNotes}
                onChangeText={setProgressNotes}
                placeholder="Describe today's progress..."
                multiline
                placeholderTextColor={Colors.textMuted}
              />
              <Pressable
                style={[styles.saveButton, saving && styles.buttonDisabled]}
                onPress={handleSave}
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator color={Colors.white} />
                ) : (
                  <Text style={styles.saveButtonText}>Save Notes</Text>
                )}
              </Pressable>
            </>
          ) : (
            <Text style={dpr.progress_notes ? styles.detailValue : styles.emptyText}>
              {dpr.progress_notes || 'No progress notes added yet'}
            </Text>
          )}
        </View>

        {/* Worker Log Grid Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Worker Logs</Text>
            {totalWorkerCount > 0 && (
              <View style={styles.workerCountBadge}>
                <Ionicons name="people" size={14} color={Colors.white} />
                <Text style={styles.workerCountText}>{totalWorkerCount}</Text>
              </View>
            )}
          </View>

          {workerLogLoading ? (
            <View style={styles.workerLogLoading}>
              <ActivityIndicator size="small" color={Colors.accent} />
              <Text style={styles.loadingText}>Loading worker logs...</Text>
            </View>
          ) : workerLogs.length === 0 ? (
            <View style={styles.emptyWorkerLog}>
              <Ionicons name="people-outline" size={40} color={Colors.textMuted} />
              <Text style={styles.emptyText}>No worker logs submitted for this date</Text>
            </View>
          ) : (
            workerLogs.map((log) => (
              <View key={log.log_id} style={styles.workerLogCard}>
                <View style={styles.workerLogHeader}>
                  <View>
                    <Text style={styles.workerLogSupervisor}>
                      <Ionicons name="person" size={14} color={Colors.accent} /> {log.supervisor_name || 'Supervisor'}
                    </Text>
                    <Text style={styles.workerLogMeta}>
                      {(editableEntries[log.log_id] || []).length} entries • {
                        (editableEntries[log.log_id] || []).reduce((s, e) => s + (e.workers_count || 0), 0)
                      } workers
                    </Text>
                  </View>
                </View>

                {/* Grid Header */}
                <View style={styles.gridHeader}>
                  <Text style={[styles.gridHeaderText, { flex: 2 }]}>Vendor</Text>
                  <Text style={[styles.gridHeaderText, { flex: 1 }]}>Workers</Text>
                  <Text style={[styles.gridHeaderText, { flex: 2 }]}>Purpose</Text>
                  {!isViewingHistorical && <Text style={[styles.gridHeaderText, { width: 36 }]}></Text>}
                </View>

                {/* Grid Rows */}
                {(editableEntries[log.log_id] || []).map((entry, idx) => (
                  <View key={idx} style={styles.gridRow}>
                    <TextInput
                      style={[styles.gridCell, { flex: 2 }]}
                      value={entry.vendor_name}
                      onChangeText={(v) => updateWorkerEntry(log.log_id, idx, 'vendor_name', v)}
                      placeholder="Vendor"
                      placeholderTextColor={Colors.textMuted}
                      editable={!isViewingHistorical}
                    />
                    <TextInput
                      style={[styles.gridCell, { flex: 1, textAlign: 'center' }]}
                      value={entry.workers_count?.toString() || ''}
                      onChangeText={(v) => updateWorkerEntry(log.log_id, idx, 'workers_count', parseInt(v) || 0)}
                      keyboardType="number-pad"
                      placeholder="0"
                      placeholderTextColor={Colors.textMuted}
                      editable={!isViewingHistorical}
                    />
                    <TextInput
                      style={[styles.gridCell, { flex: 2 }]}
                      value={entry.remarks}
                      onChangeText={(v) => updateWorkerEntry(log.log_id, idx, 'remarks', v)}
                      placeholder="Purpose"
                      placeholderTextColor={Colors.textMuted}
                      editable={!isViewingHistorical}
                    />
                    {!isViewingHistorical && (
                      <TouchableOpacity
                        style={styles.removeEntryBtn}
                        onPress={() => removeWorkerEntry(log.log_id, idx)}
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
                      onPress={() => addWorkerEntry(log.log_id)}
                    >
                      <Ionicons name="add-circle-outline" size={18} color={Colors.accent} />
                      <Text style={styles.addEntryText}>Add Entry</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={[styles.saveWorkerLogBtn, savingWorkerLog && styles.buttonDisabled]}
                      onPress={() => handleSaveWorkerLog(log.log_id)}
                      disabled={savingWorkerLog}
                    >
                      {savingWorkerLog ? (
                        <ActivityIndicator size="small" color={Colors.white} />
                      ) : (
                        <>
                          <Ionicons name="checkmark" size={16} color={Colors.white} />
                          <Text style={styles.saveWorkerLogText}>Save</Text>
                        </>
                      )}
                    </TouchableOpacity>
                  </View>
                )}
              </View>
            ))
          )}
        </View>

        {/* Photos Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Photos ({dpr.images.length})</Text>
            {!isViewingHistorical && (
              <Pressable style={styles.addPhotoBtn} onPress={addPhoto}>
                <Ionicons name="camera" size={18} color={Colors.primary} />
                <Text style={styles.addPhotoBtnText}>Add</Text>
              </Pressable>
            )}
          </View>

          {dpr.images.length === 0 ? (
            <View style={styles.emptyPhotos}>
              <Ionicons name="images-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyText}>No photos yet</Text>
              {!isViewingHistorical && (
                <Pressable style={styles.addFirstPhotoBtn} onPress={addPhoto}>
                  <Text style={styles.addFirstPhotoBtnText}>Add First Photo</Text>
                </Pressable>
              )}
            </View>
          ) : (
            <View style={styles.photoGrid}>
              {dpr.images.map((img, idx) => {
                const isExpanded = expandedImageId === img.image_id;
                return (
                  <View key={img.image_id || idx} style={styles.photoCard}>
                    <TouchableOpacity 
                      style={styles.photoHeader}
                      onPress={() => setExpandedImageId(isExpanded ? null : img.image_id)}
                    >
                      <View style={styles.photoHeaderLeft}>
                        <Ionicons name="image" size={20} color={Colors.accent} />
                        <Text style={styles.photoNumber}>Photo {idx + 1}</Text>
                        {!isExpanded && imageCaptions[img.image_id] && (
                          <Text style={styles.photoPreview} numberOfLines={1}>
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
                          style={styles.photo} 
                          resizeMode="cover"
                        />
                        
                        <Text style={styles.captionLabel}>Caption</Text>
                        <TextInput
                          style={styles.captionInput}
                          value={imageCaptions[img.image_id] || ''}
                          onChangeText={(text) => setImageCaptions(prev => ({
                            ...prev,
                            [img.image_id]: text
                          }))}
                          placeholder="Add a caption for this photo..."
                          multiline
                          numberOfLines={2}
                          placeholderTextColor={Colors.textMuted}
                        />
                        
                        <TouchableOpacity
                          style={[styles.saveCaptionBtn, saving && styles.buttonDisabled]}
                          onPress={() => saveImageCaption(img.image_id)}
                          disabled={saving}
                        >
                          {saving ? (
                            <ActivityIndicator color={Colors.white} size="small" />
                          ) : (
                            <>
                              <Ionicons name="checkmark" size={16} color={Colors.white} />
                              <Text style={styles.saveCaptionText}>Save Caption</Text>
                            </>
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
            <Text style={styles.warningText}>
              Minimum 4 photos required to submit. Add {4 - dpr.images.length} more.
            </Text>
          )}
        </View>

        {/* Action Buttons */}
        <View style={styles.actions}>
          {/* Approve Button */}
          {!isViewingHistorical && (
            <Pressable
              style={[styles.approveButton, saving && styles.buttonDisabled]}
              onPress={handleApprove}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color={Colors.white} />
              ) : (
                <>
                  <Ionicons name="checkmark-circle" size={20} color={Colors.white} />
                  <Text style={styles.approveButtonText}>
                    {dpr.status === 'approved' ? 'Re-Approve DPR' : 'Approve DPR'}
                  </Text>
                </>
              )}
            </Pressable>
          )}

          {dpr.status === 'draft' && dpr.images.length >= 4 && !isViewingHistorical && (
            <Pressable
              style={[styles.submitButton, saving && styles.buttonDisabled]}
              onPress={handleSubmit}
              disabled={saving}
            >
              {saving ? (
                <ActivityIndicator color={Colors.white} />
              ) : (
                <>
                  <Ionicons name="send" size={20} color={Colors.white} />
                  <Text style={styles.submitButtonText}>Submit DPR</Text>
                </>
              )}
            </Pressable>
          )}

          <Pressable
            style={[styles.pdfButton, generatingPdf && styles.buttonDisabled]}
            onPress={generatePDF}
            disabled={generatingPdf || dpr.images.length === 0}
          >
            {generatingPdf ? (
              <ActivityIndicator color={Colors.primary} />
            ) : (
              <>
                <Ionicons name="document" size={20} color={Colors.primary} />
                <Text style={styles.pdfButtonText}>Generate PDF</Text>
              </>
            )}
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: Spacing.md, fontSize: FontSizes.md, color: Colors.textSecondary },
  errorContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: Spacing.xl },
  errorText: { fontSize: FontSizes.lg, color: Colors.error, marginTop: Spacing.md },
  backButton: { marginTop: Spacing.lg, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.md, backgroundColor: Colors.primary, borderRadius: BorderRadius.md },
  backButtonText: { color: Colors.white, fontWeight: '600' },
  content: { padding: Spacing.md },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: Spacing.lg },
  headerLeft: { flex: 1 },
  title: { fontSize: FontSizes.xl, fontWeight: 'bold', color: Colors.text },
  date: { fontSize: FontSizes.md, color: Colors.textSecondary, marginTop: 4 },
  statusBadge: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs, borderRadius: BorderRadius.full },
  statusText: { fontSize: FontSizes.sm, fontWeight: '600', textTransform: 'capitalize' },
  infoCard: { backgroundColor: Colors.white, padding: Spacing.md, borderRadius: BorderRadius.md, marginBottom: Spacing.md, borderLeftWidth: 4, borderLeftColor: Colors.primary },
  cardTitle: { fontSize: FontSizes.sm, color: Colors.textMuted, marginBottom: 4 },
  projectName: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  section: { backgroundColor: Colors.white, padding: Spacing.md, borderRadius: BorderRadius.md, marginBottom: Spacing.md },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: Spacing.md },
  sectionTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text },
  input: { backgroundColor: Colors.background, borderWidth: 1, borderColor: Colors.border, borderRadius: BorderRadius.md, paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, fontSize: FontSizes.md, color: Colors.text },
  textArea: { minHeight: 80, textAlignVertical: 'top' },
  saveButton: { backgroundColor: Colors.primary, paddingVertical: Spacing.md, borderRadius: BorderRadius.md, alignItems: 'center', marginTop: Spacing.sm },
  saveButtonText: { color: Colors.white, fontWeight: '600', fontSize: FontSizes.md },
  buttonDisabled: { opacity: 0.6 },
  detailValue: { fontSize: FontSizes.md, color: Colors.text, lineHeight: 22 },
  emptyText: { fontSize: FontSizes.md, color: Colors.textMuted, textAlign: 'center', paddingVertical: Spacing.md },
  
  // Worker Log Grid Styles
  workerCountBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: Colors.accent, paddingHorizontal: Spacing.sm, paddingVertical: 3, borderRadius: BorderRadius.full },
  workerCountText: { fontSize: FontSizes.xs, fontWeight: '700', color: Colors.white },
  workerLogLoading: { alignItems: 'center', padding: Spacing.lg, gap: Spacing.sm },
  emptyWorkerLog: { alignItems: 'center', paddingVertical: Spacing.lg, gap: Spacing.sm },
  workerLogCard: { backgroundColor: Colors.background, borderRadius: BorderRadius.md, padding: Spacing.sm, marginBottom: Spacing.md, borderWidth: 1, borderColor: Colors.border },
  workerLogHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingBottom: Spacing.sm, marginBottom: Spacing.sm, borderBottomWidth: 1, borderBottomColor: Colors.border },
  workerLogSupervisor: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  workerLogMeta: { fontSize: FontSizes.xs, color: Colors.textMuted, marginTop: 2 },
  gridHeader: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 4, paddingBottom: Spacing.xs, borderBottomWidth: 1, borderBottomColor: Colors.border },
  gridHeaderText: { fontSize: FontSizes.xs, fontWeight: '700', color: Colors.textSecondary, textTransform: 'uppercase' },
  gridRow: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: Colors.border + '50' },
  gridCell: { fontSize: FontSizes.sm, color: Colors.text, backgroundColor: Colors.white, borderWidth: 1, borderColor: Colors.border, borderRadius: BorderRadius.sm, paddingHorizontal: Spacing.xs, paddingVertical: 6 },
  removeEntryBtn: { width: 36, alignItems: 'center', justifyContent: 'center' },
  workerLogActions: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: Spacing.sm },
  addEntryBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  addEntryText: { fontSize: FontSizes.sm, color: Colors.accent, fontWeight: '500' },
  saveWorkerLogBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: Colors.success, paddingHorizontal: Spacing.md, paddingVertical: Spacing.xs, borderRadius: BorderRadius.sm },
  saveWorkerLogText: { fontSize: FontSizes.sm, color: Colors.white, fontWeight: '600' },

  // Photo styles
  addPhotoBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: Spacing.sm, paddingVertical: Spacing.xs, borderWidth: 1, borderColor: Colors.primary, borderRadius: BorderRadius.sm },
  addPhotoBtnText: { fontSize: FontSizes.sm, color: Colors.primary },
  emptyPhotos: { alignItems: 'center', paddingVertical: Spacing.xl },
  addFirstPhotoBtn: { marginTop: Spacing.md, paddingHorizontal: Spacing.lg, paddingVertical: Spacing.sm, backgroundColor: Colors.primary, borderRadius: BorderRadius.md },
  addFirstPhotoBtnText: { color: Colors.white, fontWeight: '600' },
  photoGrid: { gap: Spacing.md },
  photoCard: { backgroundColor: Colors.background, borderRadius: BorderRadius.md, overflow: 'hidden', marginBottom: Spacing.sm, borderWidth: 1, borderColor: Colors.border },
  photoHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: Spacing.md, backgroundColor: Colors.white },
  photoHeaderLeft: { flexDirection: 'row', alignItems: 'center', flex: 1, gap: Spacing.xs },
  photoNumber: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  photoPreview: { fontSize: FontSizes.sm, color: Colors.textMuted, marginLeft: Spacing.xs, flex: 1 },
  photoContent: { padding: Spacing.md, paddingTop: 0 },
  photo: { width: '100%', aspectRatio: 16/9, borderRadius: BorderRadius.sm, marginBottom: Spacing.md },
  captionLabel: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.textSecondary, marginBottom: Spacing.xs },
  captionInput: { backgroundColor: Colors.white, borderWidth: 1, borderColor: Colors.border, borderRadius: BorderRadius.md, padding: Spacing.md, fontSize: FontSizes.md, color: Colors.text, minHeight: 60, textAlignVertical: 'top' },
  saveCaptionBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.success, padding: Spacing.sm, borderRadius: BorderRadius.md, marginTop: Spacing.sm, gap: Spacing.xs },
  saveCaptionText: { color: Colors.white, fontWeight: '600', fontSize: FontSizes.sm },
  warningText: { textAlign: 'center', color: Colors.warning, fontSize: FontSizes.sm, marginTop: Spacing.md },
  
  // Action button styles
  actions: { gap: Spacing.md, marginTop: Spacing.md },
  approveButton: { backgroundColor: Colors.success, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, paddingVertical: Spacing.md, borderRadius: BorderRadius.md },
  approveButtonText: { color: Colors.white, fontWeight: '600', fontSize: FontSizes.md },
  submitButton: { backgroundColor: Colors.info, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, paddingVertical: Spacing.md, borderRadius: BorderRadius.md },
  submitButtonText: { color: Colors.white, fontWeight: '600', fontSize: FontSizes.md },
  pdfButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.sm, paddingVertical: Spacing.md, borderRadius: BorderRadius.md, borderWidth: 1, borderColor: Colors.primary },
  pdfButtonText: { color: Colors.primary, fontWeight: '600', fontSize: FontSizes.md },
});
