// ADMIN DPR INDEX - LIST VIEW
// Shows DPRs for selected project with Create + Worker Log buttons
// Admin can view, edit, approve DPRs created by supervisors or themselves

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useProject } from '../../../contexts/ProjectContext';
import { Card } from '../../../components/ui';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../../constants/theme';

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

const getToken = async () => {
  if (Platform.OS === 'web') return localStorage.getItem('access_token');
  const SecureStore = require('expo-secure-store');
  return await SecureStore.getItemAsync('access_token');
};

interface DPRItem {
  dpr_id: string;
  dpr_date: string;
  status: string;
  progress_notes?: string;
  created_by_name?: string;
  created_by_role?: string;
  images_count?: number;
  created_at: string;
}

export default function AdminDPRListScreen() {
  const router = useRouter();
  const { selectedProject } = useProject();
  const [dprs, setDprs] = useState<DPRItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Redirect if no project selected
  useEffect(() => {
    if (!selectedProject) {
      requestAnimationFrame(() => {
        router.replace('/(admin)/select-project');
      });
    }
  }, [selectedProject]);

  const projectId = (selectedProject as any)?.project_id || (selectedProject as any)?._id || '';

  const loadDPRs = useCallback(async () => {
    if (!projectId) return;
    try {
      const token = await getToken();
      const response = await fetch(`${BASE_URL}/api/v2/dpr?project_id=${projectId}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
      });
      if (response.ok) {
        const data = await response.json();
        setDprs(data.dprs || data || []);
      }
    } catch (error) {
      console.error('Error loading DPRs:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadDPRs();
  }, [loadDPRs, projectId]);

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'approved': return Colors.success;
      case 'submitted': return Colors.info;
      case 'draft': return Colors.warning;
      case 'rejected': return Colors.error;
      default: return Colors.textMuted;
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const renderDPR = ({ item }: { item: DPRItem }) => (
    <TouchableOpacity onPress={() => router.push(`/(admin)/dpr/${item.dpr_id}`)}>
      <Card style={styles.dprCard}>
        <View style={styles.dprHeader}>
          <View>
            <Text style={styles.dprDate}>{formatDate(item.dpr_date)}</Text>
            <Text style={styles.dprCreator}>
              by {item.created_by_name || 'Unknown'} ({item.created_by_role || 'N/A'})
            </Text>
          </View>
          <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '20' }]}>
            <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
              {item.status}
            </Text>
          </View>
        </View>
        {item.progress_notes && (
          <Text style={styles.dprNotes} numberOfLines={2}>{item.progress_notes}</Text>
        )}
        <View style={styles.dprMeta}>
          <View style={styles.metaItem}>
            <Ionicons name="camera-outline" size={14} color={Colors.textMuted} />
            <Text style={styles.metaText}>{item.images_count || 0} photos</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
        </View>
      </Card>
    </TouchableOpacity>
  );

  if (!selectedProject) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.accent} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>Daily Progress Reports</Text>
          <Text style={styles.headerSubtitle}>{selectedProject.project_name}</Text>
        </View>
      </View>

      {/* Action Buttons */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[styles.actionButton, styles.createButton]}
          onPress={() => router.push('/(admin)/dpr/create')}
        >
          <Ionicons name="add-circle" size={20} color={Colors.white} />
          <Text style={styles.actionButtonText}>Create DPR</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.actionButton, styles.workerLogButton]}
          onPress={() => router.push('/(admin)/worker-log')}
        >
          <Ionicons name="people" size={20} color={Colors.white} />
          <Text style={styles.actionButtonText}>Worker Log</Text>
        </TouchableOpacity>
      </View>

      {/* DPR List */}
      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.accent} />
          <Text style={styles.loadingText}>Loading DPRs...</Text>
        </View>
      ) : (
        <FlatList
          data={dprs}
          renderItem={renderDPR}
          keyExtractor={(item) => item.dpr_id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); loadDPRs(); }}
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Ionicons name="document-text-outline" size={64} color={Colors.textMuted} />
              <Text style={styles.emptyTitle}>No DPRs Yet</Text>
              <Text style={styles.emptyText}>
                Create your first DPR or wait for supervisors to submit their reports.
              </Text>
            </View>
          }
        />
      )}
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
    gap: Spacing.md,
  },
  loadingText: {
    color: Colors.textSecondary,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: Spacing.md,
    backgroundColor: Colors.white,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
    color: Colors.text,
  },
  headerSubtitle: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 2,
  },
  actionRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
    padding: Spacing.md,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.sm,
    borderRadius: BorderRadius.md,
    gap: Spacing.xs,
  },
  createButton: {
    backgroundColor: Colors.accent,
  },
  workerLogButton: {
    backgroundColor: Colors.primary,
  },
  actionButtonText: {
    fontSize: FontSizes.sm,
    fontWeight: '600',
    color: Colors.white,
  },
  listContent: {
    padding: Spacing.md,
    paddingTop: 0,
  },
  dprCard: {
    padding: Spacing.md,
    marginBottom: Spacing.sm,
  },
  dprHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  dprDate: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  dprCreator: {
    fontSize: FontSizes.xs,
    color: Colors.textMuted,
    marginTop: 2,
  },
  statusBadge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: BorderRadius.sm,
  },
  statusText: {
    fontSize: FontSizes.xs,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  dprNotes: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: Spacing.sm,
    lineHeight: 20,
  },
  dprMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: Spacing.sm,
    paddingTop: Spacing.sm,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    fontSize: FontSizes.xs,
    color: Colors.textMuted,
  },
  emptyContainer: {
    alignItems: 'center',
    padding: Spacing.xxl,
    paddingTop: Spacing.xxl * 2,
  },
  emptyTitle: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.md,
  },
  emptyText: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginTop: Spacing.xs,
    lineHeight: 22,
  },
});
