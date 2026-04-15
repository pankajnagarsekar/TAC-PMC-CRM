// VOICE LOG SCREEN (Supervisor)
// Record audio, convert to base64, submit to /api/v1/voice-logs
// Cross-platform: FileSystem.readAsStringAsync on native, FileReader on web

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Platform,
  FlatList,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import { Card } from '../../components/ui';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../constants/theme';
import { useProject } from '../../contexts/ProjectContext';
import { voiceLogsApi, codesApi } from '../../services/apiClient';
import type { VoiceLog, Code } from '../../types/api';

// ─── helpers ────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = (seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

async function uriToBase64(uri: string): Promise<string> {
  if (Platform.OS === 'web') {
    const response = await fetch(uri);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const result = reader.result as string;
        // Strip data URL prefix (data:audio/...;base64,)
        resolve(result.split(',')[1]);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
  // Native: expo-file-system
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const FileSystem = require('expo-file-system');
  return await FileSystem.readAsStringAsync(uri, { encoding: 'base64' });
}

// ─── component ──────────────────────────────────────────────────────────────

export default function VoiceLogScreen() {
  const { selectedProject } = useProject();

  // Recording state
  const recordingRef = useRef<Audio.Recording | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [duration, setDuration] = useState(0);

  // Data state
  const [codes, setCodes] = useState<Code[]>([]);
  const [selectedCode, setSelectedCode] = useState<Code | null>(null);
  const [logs, setLogs] = useState<VoiceLog[]>([]);
  const [isLoadingLogs, setIsLoadingLogs] = useState(false);
  const [showCodePicker, setShowCodePicker] = useState(false);

  const projectId = (selectedProject as any)?.project_id || (selectedProject as any)?.id || '';

  // Load codes + recent logs on mount
  useEffect(() => {
    if (!projectId) return;
    loadCodes();
    loadLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      recordingRef.current?.stopAndUnloadAsync().catch(() => null);
    };
  }, []);

  const loadCodes = async () => {
    try {
      const data = await codesApi.getAll(true);
      setCodes(data);
      if (data.length > 0) setSelectedCode(data[0]);
    } catch (e) {
      console.error('Failed to load codes:', e);
    }
  };

  const loadLogs = useCallback(async () => {
    if (!projectId) return;
    setIsLoadingLogs(true);
    try {
      const data = await voiceLogsApi.getAll(projectId);
      setLogs(data);
    } catch (e) {
      console.error('Failed to load voice logs:', e);
    } finally {
      setIsLoadingLogs(false);
    }
  }, [projectId]);

  const startRecording = async () => {
    try {
      if (!selectedCode) {
        Alert.alert('Select Code', 'Please select a cost code before recording.');
        return;
      }

      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        Alert.alert('Permission Required', 'Microphone permission is needed for voice recording.');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );

      recordingRef.current = recording;
      setDuration(0);
      setIsRecording(true);

      timerRef.current = setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    } catch (error) {
      console.error('Start recording failed:', error);
      Alert.alert('Error', 'Failed to start recording. Check microphone permissions.');
    }
  };

  const stopAndSubmit = async () => {
    if (!recordingRef.current) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    const recordedDuration = duration;
    setIsRecording(false);
    setIsSubmitting(true);

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      if (!uri) throw new Error('No audio recorded');
      if (recordedDuration < 1) throw new Error('Recording too short');

      const audio_base64 = await uriToBase64(uri);

      await voiceLogsApi.create({
        project_id: projectId,
        code_id: selectedCode!.code_id,
        audio_base64,
        duration_seconds: recordedDuration,
      });

      setDuration(0);
      Alert.alert('Success', 'Voice log saved and sent for transcription.');
      await loadLogs();
    } catch (error: unknown) {
      const err = error as { message?: string };
      console.error('Voice log submit failed:', error);
      Alert.alert('Error', err.message || 'Failed to save voice log. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRecordPress = () => {
    if (isRecording) {
      stopAndSubmit();
    } else {
      startRecording();
    }
  };

  if (!projectId) {
    return (
      <SafeAreaView style={styles.container} edges={['left', 'right']}>
        <View style={styles.centered}>
          <Ionicons name="business-outline" size={48} color={Colors.textMuted} />
          <Text style={styles.emptyTitle}>No Project Selected</Text>
          <Text style={styles.emptySubtitle}>Select a project to record voice logs</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>

        {/* Code Picker */}
        <Card style={styles.card}>
          <Text style={styles.label}>Cost Code</Text>
          <TouchableOpacity
            style={styles.codePicker}
            onPress={() => setShowCodePicker(!showCodePicker)}
          >
            <Text style={styles.codePickerText}>
              {selectedCode ? `${selectedCode.code_short} — ${selectedCode.code_name}` : 'Select a code'}
            </Text>
            <Ionicons
              name={showCodePicker ? 'chevron-up' : 'chevron-down'}
              size={16}
              color={Colors.textSecondary}
            />
          </TouchableOpacity>

          {showCodePicker && (
            <View style={styles.codeDropdown}>
              {codes.map(code => (
                <TouchableOpacity
                  key={code.code_id}
                  style={[styles.codeOption, selectedCode?.code_id === code.code_id && styles.codeOptionActive]}
                  onPress={() => {
                    setSelectedCode(code);
                    setShowCodePicker(false);
                  }}
                >
                  <Text style={[
                    styles.codeOptionText,
                    selectedCode?.code_id === code.code_id && styles.codeOptionTextActive,
                  ]}>
                    {code.code_short} — {code.code_name}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          )}
        </Card>

        {/* Record Button */}
        <Card style={styles.recordCard}>
          <TouchableOpacity
            style={[styles.recordCircle, isRecording && styles.recordCircleActive]}
            onPress={handleRecordPress}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <ActivityIndicator color={Colors.white} size="large" />
            ) : (
              <Ionicons
                name={isRecording ? 'stop' : 'mic'}
                size={36}
                color={Colors.white}
              />
            )}
          </TouchableOpacity>

          <Text style={styles.recordLabel}>
            {isSubmitting
              ? 'Saving...'
              : isRecording
              ? `Recording  ${formatDuration(duration)}`
              : 'Tap to record'}
          </Text>

          {isRecording && (
            <Text style={styles.recordHint}>Tap stop when done — auto-saves</Text>
          )}
          {!isRecording && !isSubmitting && (
            <Text style={styles.recordHint}>Audio sent for transcription after saving</Text>
          )}
        </Card>

        {/* Recent Logs */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Voice Logs</Text>

          {isLoadingLogs ? (
            <ActivityIndicator color={Colors.accent} style={styles.loader} />
          ) : logs.length === 0 ? (
            <View style={styles.emptyList}>
              <Text style={styles.emptyText}>No voice logs yet</Text>
            </View>
          ) : (
            <FlatList
              data={logs}
              keyExtractor={item => item.voice_log_id}
              scrollEnabled={false}
              renderItem={({ item }) => (
                <Card style={styles.logItem}>
                  <View style={styles.logRow}>
                    <Ionicons name="mic-outline" size={18} color={Colors.accent} />
                    <View style={styles.logContent}>
                      <Text style={styles.logDate}>
                        {new Date(item.created_at).toLocaleDateString('en-US', {
                          day: '2-digit', month: 'short', year: 'numeric',
                        })}
                      </Text>
                      {item.transcribed_text ? (
                        <Text style={styles.logText} numberOfLines={2}>
                          {item.transcribed_text}
                        </Text>
                      ) : item.transcription_failed ? (
                        <Text style={styles.logTextFailed}>Transcription failed</Text>
                      ) : (
                        <Text style={styles.logTextPending}>Transcribing...</Text>
                      )}
                    </View>
                  </View>
                </Card>
              )}
            />
          )}
        </View>

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  content: { padding: Spacing.md, paddingBottom: Spacing.xxl },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: Spacing.xl },
  emptyTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text, marginTop: Spacing.md },
  emptySubtitle: { fontSize: FontSizes.sm, color: Colors.textSecondary, marginTop: Spacing.xs, textAlign: 'center' },

  card: { padding: Spacing.md, marginBottom: Spacing.md },
  label: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.textSecondary, marginBottom: Spacing.xs },

  codePicker: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingVertical: Spacing.sm, paddingHorizontal: Spacing.sm,
    backgroundColor: Colors.inputBg, borderRadius: BorderRadius.md,
    borderWidth: 1, borderColor: Colors.inputBorder,
  },
  codePickerText: { fontSize: FontSizes.md, color: Colors.text, flex: 1 },
  codeDropdown: {
    marginTop: Spacing.xs, borderRadius: BorderRadius.md,
    borderWidth: 1, borderColor: Colors.inputBorder, overflow: 'hidden',
  },
  codeOption: { paddingVertical: Spacing.sm, paddingHorizontal: Spacing.sm, backgroundColor: Colors.surface },
  codeOptionActive: { backgroundColor: Colors.accentLight },
  codeOptionText: { fontSize: FontSizes.md, color: Colors.text },
  codeOptionTextActive: { color: Colors.white, fontWeight: '600' },

  recordCard: { alignItems: 'center', padding: Spacing.xl, marginBottom: Spacing.md },
  recordCircle: {
    width: 88, height: 88, borderRadius: 44,
    backgroundColor: Colors.accent,
    justifyContent: 'center', alignItems: 'center',
    shadowColor: Colors.accent, shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35, shadowRadius: 10, elevation: 6,
    marginBottom: Spacing.md,
  },
  recordCircleActive: {
    backgroundColor: Colors.error,
    shadowColor: Colors.error,
  },
  recordLabel: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  recordHint: { fontSize: FontSizes.sm, color: Colors.textMuted, marginTop: Spacing.xs, textAlign: 'center' },

  section: { marginBottom: Spacing.lg },
  sectionTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text, marginBottom: Spacing.sm },
  loader: { marginVertical: Spacing.lg },
  emptyList: { alignItems: 'center', paddingVertical: Spacing.xl },
  emptyText: { fontSize: FontSizes.md, color: Colors.textMuted },

  logItem: { padding: Spacing.md, marginBottom: Spacing.sm },
  logRow: { flexDirection: 'row', alignItems: 'flex-start', gap: Spacing.sm },
  logContent: { flex: 1 },
  logDate: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.textSecondary, marginBottom: 2 },
  logText: { fontSize: FontSizes.sm, color: Colors.text, lineHeight: 18 },
  logTextFailed: { fontSize: FontSizes.sm, color: Colors.error, fontStyle: 'italic' },
  logTextPending: { fontSize: FontSizes.sm, color: Colors.textMuted, fontStyle: 'italic' },
});
