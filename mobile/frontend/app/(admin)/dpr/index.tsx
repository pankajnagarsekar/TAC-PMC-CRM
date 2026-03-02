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
  Alert,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useProject } from '../../../contexts/ProjectContext';
import { Card } from '../../../components/ui';
import { useTheme } from '../../../contexts/ThemeContext';

const BASE_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

const getToken = async () => {
  if (Platform.OS === 'web') return localStorage.getItem('access_token');
  // eslint-disable-next-line @typescript-eslint/no-require-imports
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
  const { colors: Colors, spacing: Spacing, fontSizes: FontSizes, borderRadius: BorderRadius } = useTheme();
  const styles = React.useMemo(() => getStyles(Colors, Spacing, FontSizes, BorderRadius), [Colors, Spacing, FontSizes, BorderRadius]);

  const [dprs, setDprs] = useState<DPRItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFilter, setDateFilter] = useState('');
  const [approvingId, setApprovingId] = useState<string | null>(null);

  // Redirect if no project selected
  useEffect(() => {
    if (!selectedProject) {
      requestAnimationFrame(() => {
        router.replace('/(admin)/select-project');
      });
    }
  }, [selectedProject, router]);

  const projectId = (selectedProject as any)?.project_id || (selectedProject as any)?._id || '';

  const loadDPRs = useCallback(async () => {
    if (!projectId) return;
    try {
      const token = await getToken();
      let url = `${BASE_URL}/api/v2/dpr?project_id=${projectId}`;
      if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
      if (dateFilter) url += `&date=${encodeURIComponent(dateFilter)}`;
      
      const response = await fetch(url, {
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
  }, [projectId, searchQuery, dateFilter]);

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
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' });
  };

  const approveDPR = async (dprId: string) => {
    try {
      setApprovingId(dprId);
      const token = await getToken();
      const response = await fetch(`${BASE_URL}/api/v2/dpr/${dprId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ status: 'Approved' }),
      });

      if (response.ok) {
        // Immediate UI update
        setDprs(prev => prev.map(dpr => 
          dpr.dpr_id === dprId ? { ...dpr, status: 'Approved' } : dpr
        ));
      } else {
        const err = await response.json();
        Alert.alert('Error', err.detail || 'Failed to approve DPR');
      }
    } catch (error) {
      console.error('Error approving DPR:', error);
      Alert.alert('Error', 'An unexpected error occurred');
    } finally {
      setApprovingId(null);
    }
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
          <View style={styles.statusContainer}>
            <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '15' }]}>
              <Text style={[styles.statusText, { color: getStatusColor(item.status) }]}>
                {item.status}
              </Text>
            </View>
            {item.status?.toLowerCase() === 'submitted' && (
              <TouchableOpacity 
                style={styles.quickApproveBtn}
                onPress={(e) => {
                  e.stopPropagation();
                  approveDPR(item.dpr_id);
                }}
                disabled={approvingId === item.dpr_id}
              >
                {approvingId === item.dpr_id ? (
                  <ActivityIndicator size="small" color={Colors.success} />
                ) : (
                  <Ionicons name="checkmark-circle" size={24} color={Colors.success} />
                )}
              </TouchableOpacity>
            )}
          </View>
        </View>
        {item.progress_notes && (
          <Text style={styles.dprNotes} numberOfLines={2}>{item.progress_notes}</Text>
        )}
        <View style={styles.dprMeta}>
          <View style={styles.metaItem}>
            <Ionicons name="camera" size={16} color={Colors.textMuted} />
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

      {/* Filters */}
      <View style={styles.filterContainer}>
        <View style={styles.searchBox}>
          <Ionicons name="search" size={18} color={Colors.textMuted} />
          <TextInput
            style={styles.searchInput}
            placeholder="Search by notes..."
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>
        <View style={styles.dateBox}>
          <Ionicons name="calendar" size={18} color={Colors.textMuted} />
          <TextInput
            style={styles.dateInput}
            placeholder="YYYY-MM-DD"
            value={dateFilter}
            onChangeText={setDateFilter}
            maxLength={10}
          />
        </View>
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

const getStyles = (Colors: any, Spacing: any, FontSizes: any, BorderRadius: any) => StyleSheet.create({
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
    fontFamily: 'Inter_500Medium',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: Spacing.md,
    backgroundColor: Colors.cardBg,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.text,
    fontFamily: 'Inter_700Bold',
  },
  headerSubtitle: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: 4,
    fontFamily: 'Inter_400Regular',
  },
  actionRow: {
    flexDirection: 'row',
    gap: Spacing.md,
    padding: Spacing.md,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: Spacing.md,
    borderRadius: BorderRadius.md,
    gap: Spacing.sm,
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
    fontFamily: 'Inter_600SemiBold',
  },
  listContent: {
    padding: Spacing.md,
    paddingTop: 0,
    paddingBottom: 100,
  },
  dprCard: {
    marginBottom: Spacing.md,
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
    fontFamily: 'Inter_600SemiBold',
  },
  dprCreator: {
    fontSize: FontSizes.xs,
    color: Colors.textMuted,
    marginTop: 4,
    fontFamily: 'Inter_400Regular',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  quickApproveBtn: {
    padding: 4,
  },
  statusBadge: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 4,
    borderRadius: BorderRadius.full,
  },
  statusText: {
    fontSize: FontSizes.xs,
    fontWeight: '600',
    textTransform: 'capitalize',
    fontFamily: 'Inter_600SemiBold',
  },
  dprNotes: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    marginTop: Spacing.md,
    lineHeight: 22,
    fontFamily: 'Inter_400Regular',
  },
  dprMeta: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: Spacing.md,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.divider,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaText: {
    fontSize: FontSizes.xs,
    color: Colors.textMuted,
    fontFamily: 'Inter_400Regular',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingHorizontal: Spacing.xl,
    paddingVertical: 80,
  },
  emptyTitle: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.md,
    fontFamily: 'Inter_600SemiBold',
  },
  emptyText: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    textAlign: 'center',
    marginTop: Spacing.sm,
    lineHeight: 24,
    fontFamily: 'Inter_400Regular',
  },
  filterContainer: {
    flexDirection: 'row',
    padding: Spacing.md,
    paddingTop: 0,
    gap: Spacing.md,
  },
  searchBox: {
    flex: 2,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  dateBox: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  searchInput: {
    flex: 1,
    height: 44,
    marginLeft: Spacing.sm,
    fontSize: FontSizes.sm,
    color: Colors.text,
    fontFamily: 'Inter_400Regular',
  },
  dateInput: {
    flex: 1,
    height: 44,
    marginLeft: Spacing.sm,
    fontSize: FontSizes.sm,
    color: Colors.text,
    fontFamily: 'Inter_400Regular',
  },
});
