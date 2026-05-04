// ADMIN DPR INDEX - LIST VIEW
// Shows DPRs for selected project with premium luxury design

import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
  TextInput,
  GestureResponderEvent,
  StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useFocusEffect } from 'expo-router';
import { useProject } from '../../../contexts/ProjectContext';
import { Card } from '../../../components/ui';
import { useTheme, ThemeContextType } from '../../../contexts/ThemeContext';
import { dprApi } from '../../../services/apiClient';
import { DPR, Project } from '../../../types/api';

export default function AdminDPRListScreen() {
  const router = useRouter();
  const { selectedProject } = useProject();
  const { colors: Colors, spacing: Spacing, fontSizes: FontSizes, borderRadius: BorderRadius, typography: Typography, isDark } = useTheme();
  const styles = React.useMemo(() => getStyles(Colors, Spacing, FontSizes, BorderRadius), [Colors, Spacing, FontSizes, BorderRadius]);

  const [dprs, setDprs] = useState<DPR[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [approvingId, setApprovingId] = useState<string | null>(null);

  // Redirect if no project selected
  useEffect(() => {
    if (!selectedProject) {
      requestAnimationFrame(() => {
        router.replace({
          pathname: '/(admin)/select-project',
          params: { redirect: '/(admin)/dpr' }
        });
      });
    }
  }, [selectedProject, router]);

  const project = selectedProject as Project | null;
  const projectId = project?.project_id || project?._id || '';

  const loadDPRs = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await dprApi.getAll(projectId, {
        search: searchQuery || undefined,
      });
      setDprs(data);
    } catch (error) {
      console.error('Error loading DPRs:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectId, searchQuery]);

  useEffect(() => {
    if (projectId) loadDPRs();
  }, [loadDPRs, projectId]);

  useFocusEffect(
    React.useCallback(() => {
      if (projectId) loadDPRs();
    }, [projectId, loadDPRs])
  );

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'approved': return Colors.success;
      case 'submitted': return Colors.primary; // Gold for submitted
      case 'draft': return Colors.warning;
      case 'rejected': return Colors.error;
      default: return Colors.textMuted;
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const approveDPR = async (dprId: string) => {
    try {
      setApprovingId(dprId);
      await dprApi.approve(dprId);
      setDprs(prev => prev.map(dpr =>
        (dpr.dpr_id === dprId || (dpr as any).id === dprId) ? { ...dpr, status: 'Approved' } : dpr
      ));
    } catch (error: unknown) {
      console.error('Error approving DPR:', error);
      const msg = error instanceof Error ? error.message : 'Failed to approve DPR';
      Alert.alert('Error', msg);
    } finally {
      setApprovingId(null);
    }
  };

  const renderDPR = ({ item }: { item: DPR }) => {
    const dprId = item.dpr_id || (item as any).id || (item as any)._id;
    const isApproved = item.status?.toLowerCase() === 'approved';

    return (
      <TouchableOpacity 
        activeOpacity={0.8}
        onPress={() => dprId && router.push(`/(admin)/dpr/${dprId}`)}
      >
        <Card variant="elevated" style={[styles.dprCard, isApproved && { opacity: 0.9 }]}>
          <View style={styles.dprHeader}>
            <View style={styles.dateBlock}>
                <Text style={[styles.dprDate, { color: Colors.text, ...Typography.subtitle }]}>{formatDate(item.dpr_date)}</Text>
                <Text style={[styles.dprYear, { color: Colors.textMuted, fontSize: 10 }]}>{new Date(item.dpr_date).getFullYear()}</Text>
            </View>
            
            <View style={styles.statusSection}>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) + '15' }]}>
                    <View style={[styles.statusDot, { backgroundColor: getStatusColor(item.status) }]} />
                    <Text style={[styles.statusText, { color: getStatusColor(item.status), ...Typography.overline }]}>
                    {item.status}
                    </Text>
                </View>
                
                {item.status?.toLowerCase() === 'submitted' && (
                    <TouchableOpacity
                    style={[styles.quickApproveBtn, { backgroundColor: Colors.success + '15' }]}
                    onPress={(e: GestureResponderEvent) => {
                        e.stopPropagation();
                        if (dprId) approveDPR(dprId);
                    }}
                    disabled={approvingId === dprId}
                    >
                    {approvingId === dprId ? (
                        <ActivityIndicator size="small" color={Colors.success} />
                    ) : (
                        <Ionicons name="checkmark" size={18} color={Colors.success} />
                    )}
                    </TouchableOpacity>
                )}
            </View>
          </View>

          <View style={styles.contentDivider} />

          {item.progress_notes && (
            <Text style={[styles.dprNotes, { color: Colors.textSecondary, ...Typography.body }]} numberOfLines={2}>
                {item.progress_notes}
            </Text>
          )}

          <View style={styles.dprFooter}>
            <View style={styles.creatorInfo}>
                <View style={[styles.avatar, { backgroundColor: Colors.primary + '20' }]}>
                    <Text style={{ color: Colors.primary, fontSize: 10, fontWeight: '700' }}>
                        {(item.created_by_name || 'U').charAt(0).toUpperCase()}
                    </Text>
                </View>
                <Text style={[styles.dprCreator, { color: Colors.textMuted, ...Typography.caption }]}>
                    {item.created_by_name || 'Supervisor'}
                </Text>
            </View>

            <View style={styles.metaBadge}>
              <Ionicons name="images-outline" size={12} color={Colors.primary} />
              <Text style={[styles.metaText, { color: Colors.primary, fontWeight: '700', fontSize: 10 }]}>
                {item.images_count || 0}
              </Text>
            </View>
          </View>
        </Card>
      </TouchableOpacity>
    );
  };

  if (!selectedProject) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]} edges={['top']}>
      <StatusBar barStyle={isDark ? "light-content" : "dark-content"} />
      
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={[styles.headerTitle, { color: Colors.text, ...Typography.heading2 }]}>Daily Reports</Text>
          <Text style={[styles.headerSubtitle, { color: Colors.textMuted, ...Typography.overline }]}>{selectedProject.project_name}</Text>
        </View>
        <TouchableOpacity style={[styles.headerIcon, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
            <Ionicons name="options-outline" size={20} color={Colors.text} />
        </TouchableOpacity>
      </View>

      {/* Action Row */}
      <View style={styles.actionRow}>
        <TouchableOpacity
          style={[styles.actionButton, { backgroundColor: Colors.primary }]}
          onPress={() => router.push('/(admin)/dpr/create')}
        >
          <Ionicons name="add" size={22} color={Colors.textInverse} />
          <Text style={[styles.actionButtonText, { color: Colors.textInverse }]}>New DPR</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.actionButton, { backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border }]}
          onPress={() => router.push('/(admin)/worker-log')}
        >
          <Ionicons name="people-outline" size={20} color={Colors.text} />
          <Text style={[styles.actionButtonText, { color: Colors.text }]}>Worker Log</Text>
        </TouchableOpacity>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <View style={[styles.searchBox, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
          <Ionicons name="search" size={18} color={Colors.textMuted} />
          <TextInput
            style={[styles.searchInput, { color: Colors.text }]}
            placeholder="Search reports..."
            placeholderTextColor={Colors.textMuted}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
        </View>
      </View>

      {/* DPR List */}
      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={[styles.loadingText, { color: Colors.textSecondary }]}>Retrieving records...</Text>
        </View>
      ) : (
        <FlatList
          data={dprs}
          renderItem={renderDPR}
          keyExtractor={(item) => item.dpr_id || (item as any).id || (item as any)._id}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => { setRefreshing(true); loadDPRs(); }}
              tintColor={Colors.primary}
            />
          }
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <View style={[styles.emptyIconCircle, { backgroundColor: Colors.surface }]}>
                <Ionicons name="document-text-outline" size={40} color={Colors.textMuted} />
              </View>
              <Text style={[styles.emptyTitle, { color: Colors.text }]}>No Reports Found</Text>
              <Text style={[styles.emptyText, { color: Colors.textMuted }]}>
                Try adjusting your filters or create a new report.
              </Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const getStyles = (
  Colors: ThemeContextType['colors'],
  Spacing: ThemeContextType['spacing'],
  FontSizes: ThemeContextType['fontSizes'],
  BorderRadius: ThemeContextType['borderRadius']
) => StyleSheet.create({
  container: {
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: Spacing.md,
  },
  loadingText: {
    fontFamily: 'Inter_500Medium',
    marginTop: 8,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  headerTitle: {
    fontWeight: '800',
  },
  headerSubtitle: {
    marginTop: 2,
    letterSpacing: 0.5,
  },
  headerIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
  },
  actionRow: {
    flexDirection: 'row',
    gap: Spacing.md,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    height: 50,
    borderRadius: 14,
    gap: 8,
  },
  actionButtonText: {
    fontSize: 14,
    fontWeight: '700',
  },
  searchContainer: {
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.md,
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 12,
    paddingHorizontal: Spacing.md,
    borderWidth: 1,
    height: 46,
  },
  searchInput: {
    flex: 1,
    height: '100%',
    marginLeft: 10,
    fontSize: 14,
  },
  listContent: {
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.sm,
    paddingBottom: 120,
  },
  dprCard: {
    marginBottom: Spacing.md,
    borderRadius: 18,
    padding: Spacing.md,
  },
  dprHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  dateBlock: {
  },
  dprDate: {
    fontWeight: '700',
  },
  dprYear: {
    marginTop: 2,
  },
  statusSection: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 8,
    gap: 6,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontWeight: '700',
    fontSize: 10,
    textTransform: 'uppercase',
  },
  quickApproveBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  contentDivider: {
    height: 1,
    backgroundColor: 'transparent',
    marginVertical: Spacing.md,
  },
  dprNotes: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: Spacing.md,
  },
  dprFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: Spacing.md,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: 'rgba(0,0,0,0.05)',
  },
  creatorInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  avatar: {
    width: 22,
    height: 22,
    borderRadius: 11,
    justifyContent: 'center',
    alignItems: 'center',
  },
  dprCreator: {
    fontWeight: '500',
  },
  metaBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  metaText: {
    marginLeft: 2,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 100,
  },
  emptyIconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.lg,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 8,
  },
  emptyText: {
    fontSize: 14,
    textAlign: 'center',
    paddingHorizontal: 40,
    lineHeight: 20,
  },
});
