// CLIENT REPORTS SCREEN (PHASE 7 PARITY)
// Mobile selector for project reports with download/share capability
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { reportingApi, projectsApi } from '../../services/apiClient';
import { Colors, Spacing, FontSizes, BorderRadius, Shadows } from '../../constants/theme';
import ScreenHeader from '../../components/ScreenHeader';
import { useAuth } from '../../contexts/AuthContext';

const REPORTS = [
  { id: 'weekly_progress', name: 'Weekly Progress', icon: 'calendar-outline', color: Colors.info },
  { id: '15_days_progress', name: '15-Day Progress', icon: 'calendar', color: Colors.info },
  { id: 'monthly_progress', name: 'Monthly Summary', icon: 'calendar-number', color: Colors.info },
  { id: 'project_summary', name: 'Project Overview', icon: 'analytics-outline', color: Colors.primary },
  { id: 'work_order_tracker', name: 'Work Orders Tracker', icon: 'document-attach-outline', color: Colors.accent },
  { id: 'payment_certificate_tracker', name: 'Payment Certificates', icon: 'checkbox-outline', color: Colors.success },
  { id: 'petty_cash_tracker', name: 'Petty Cash Log', icon: 'wallet-outline', color: Colors.warning },
  { id: 'csa_report', name: 'CSA Verification', icon: 'shield-checkmark-outline', color: '#8B5CF6' },
];

export default function ClientReportsScreen() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<any[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await projectsApi.getAll();
      setProjects(data || []);
      if (data && data.length > 0) {
        setSelectedProjectId(data[0].project_id);
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (reportType: string) => {
    if (!selectedProjectId) {
      Alert.alert('Selection Required', 'Please select a project first.');
      return;
    }

    setExporting(reportType);
    try {
      const url = reportingApi.getExportUrl(selectedProjectId, reportType, 'pdf');
      
      // Since it's a secured endpoint, we need to pass the token if possible
      // standard downloadResumable might not support custom headers easily for the final redirect if not careful
      // But repo-provided request() usually handles this.
      // For simplicity in mobile parity, we assume the backend supports a session or we use a fetch-blob approach
      
      // In Expo, we can use downloadAsync for simple GETs
      const filename = `${reportType}_${new Date().toISOString().split('T')[0]}.pdf`;
      const fileUri = (FileSystem as any).documentDirectory + filename;

      // We need the token for the request
      // (Re-using logic from apiClient to get token)
      const SecureStore = require('expo-secure-store');
      const token = await SecureStore.getItemAsync('access_token');

      const downloadResult = await FileSystem.downloadAsync(url, fileUri, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (downloadResult.status === 200) {
        if (await Sharing.isAvailableAsync()) {
          await Sharing.shareAsync(downloadResult.uri, {
            mimeType: 'application/pdf',
            dialogTitle: `Share ${reportType}`,
            UTI: 'com.adobe.pdf',
          });
        } else {
          Alert.alert('Download Complete', `File saved to ${downloadResult.uri}`);
        }
      } else {
        throw new Error(`Server returned ${downloadResult.status}`);
      }
    } catch (error: any) {
      console.error('Export error:', error);
      Alert.alert('Export Failed', error.message || 'Could not generate report.');
    } finally {
      setExporting(null);
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ScreenHeader title="Project Reports" showBack />
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScreenHeader title="Project Reports" showBack />
      
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.projectSelection}>
          <Text style={styles.label}>Selected Project</Text>
          <View style={styles.projectChips}>
            {projects.map(p => (
              <Pressable 
                key={p.project_id} 
                style={[styles.chip, selectedProjectId === p.project_id && styles.chipActive]}
                onPress={() => setSelectedProjectId(p.project_id)}
              >
                <Text style={[styles.chipText, selectedProjectId === p.project_id && styles.chipTextActive]}>
                  {p.project_name}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        <View style={styles.reportList}>
          {REPORTS.map(report => (
            <Pressable 
              key={report.id} 
              style={styles.reportCard}
              onPress={() => handleExport(report.id)}
              disabled={!!exporting}
            >
              <View style={[styles.reportIcon, { backgroundColor: report.color + '15' }]}>
                <Ionicons name={report.icon as any} size={24} color={report.color} />
              </View>
              <View style={styles.reportInfo}>
                <Text style={styles.reportName}>{report.name}</Text>
                <Text style={styles.reportMeta}>PDF Format • Auto-generated</Text>
              </View>
              {exporting === report.id ? (
                <ActivityIndicator size="small" color={Colors.primary} />
              ) : (
                <Ionicons name="share-outline" size={20} color={Colors.textMuted} />
              )}
            </Pressable>
          ))}
        </View>

        <View style={styles.notice}>
          <Ionicons name="mail-outline" size={20} color={Colors.textSecondary} />
          <Text style={styles.noticeText}>
            Reports shared from here can be emailed or sent via messaging apps using the native share menu.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scrollContent: { padding: Spacing.lg },
  
  projectSelection: { marginBottom: Spacing.xl },
  label: { fontSize: FontSizes.sm, fontWeight: '700', color: Colors.textSecondary, marginBottom: Spacing.sm, textTransform: 'uppercase' },
  projectChips: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.sm },
  chip: { paddingHorizontal: Spacing.md, paddingVertical: Spacing.sm, borderRadius: BorderRadius.full, backgroundColor: Colors.white, borderWidth: 1, borderColor: Colors.border },
  chipActive: { backgroundColor: Colors.primary, borderColor: Colors.primary },
  chipText: { fontSize: FontSizes.sm, color: Colors.textSecondary },
  chipTextActive: { color: Colors.white, fontWeight: '600' },

  reportList: { gap: Spacing.md },
  reportCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.white, padding: Spacing.md, borderRadius: BorderRadius.lg, ...Shadows.sm },
  reportIcon: { width: 48, height: 48, borderRadius: BorderRadius.md, justifyContent: 'center', alignItems: 'center', marginRight: Spacing.md },
  reportInfo: { flex: 1 },
  reportName: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  reportMeta: { fontSize: FontSizes.xs, color: Colors.textMuted, marginTop: 2 },

  notice: { marginTop: Spacing.xxl, flexDirection: 'row', alignItems: 'center', gap: Spacing.sm, padding: Spacing.md, backgroundColor: Colors.inputBg, borderRadius: BorderRadius.md },
  noticeText: { fontSize: FontSizes.xs, color: Colors.textSecondary, flex: 1, lineHeight: 18 },
});
