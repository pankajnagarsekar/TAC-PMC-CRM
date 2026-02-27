// ADMIN DASHBOARD — PROJECTS OVERVIEW (BIRDS-EYE VIEW)
// Shows all active projects as cards with budget stats, DPR counts, completion %
// Admin can tap a card to enter project-scoped mode

import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useProject } from '../../contexts/ProjectContext';
import { apiClient } from '../../services/apiClient';
import { Colors as StaticColors, Spacing as StaticSpacing, FontSizes as StaticFontSizes, BorderRadius as StaticBorderRadius } from '../../constants/theme';
import { useTheme } from '../../contexts/ThemeContext';

interface BudgetCategory {
  code_id: string;
  code_name: string;
  approved_budget: number;
  committed: number;
  certified: number;
  remaining: number;
}

interface ProjectOverview {
  project_id: string;
  project_name: string;
  project_code?: string;
  status: string;
  completion_pct: number;
  budget: {
    total_master: number;
    total_committed: number;
    total_certified: number;
    total_remaining: number;
    categories: BudgetCategory[];
  };
  petty_cash_total: number;
  dprs: {
    total: number;
    today: number;
    pending_approvals: number;
  };
  workers: {
    recent_total: number;
  };
}

const formatCurrency = (amount: number): string => {
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
  return `₹${amount.toFixed(0)}`;
};

export default function AdminDashboard() {
  const router = useRouter();
  const { setSelectedProject } = useProject();
  const { colors: Colors, spacing: Spacing, fontSizes: FontSizes, borderRadius: BorderRadius } = useTheme();
  const styles = useMemo(() => getStyles(Colors, Spacing, FontSizes, BorderRadius), [Colors, Spacing, FontSizes, BorderRadius]);
  
  const [projects, setProjects] = useState<ProjectOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);

  const fetchOverview = useCallback(async () => {
    try {
      const data = await apiClient.get<any>('/api/v2/admin/projects-overview');
      setProjects(data.projects || []);
    } catch (err: any) {
      console.error('Error fetching projects overview:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchOverview();
  }, [fetchOverview]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchOverview();
  };

  const handleProjectTap = (project: ProjectOverview) => {
    setSelectedProject({
      project_id: project.project_id,
      project_name: project.project_name,
      project_code: project.project_code,
    } as any);
    router.push('/(admin)/dpr' as any);
  };

  const toggleExpand = (projectId: string) => {
    setExpandedProject(expandedProject === projectId ? null : projectId);
  };

  const getCompletionColor = (pct: number) => {
    if (pct >= 75) return '#22c55e';
    if (pct >= 50) return '#f59e0b';
    if (pct >= 25) return '#3b82f6';
    return Colors.textMuted;
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading projects...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        {/* Page Header */}
        <View style={styles.pageHeader}>
          <Text style={styles.pageTitle}>Projects Overview</Text>
          <Text style={styles.pageSubtitle}>{projects.length} active project{projects.length !== 1 ? 's' : ''}</Text>
        </View>

        {/* Summary Strip */}
        <View style={styles.summaryStrip}>
          <View style={styles.summaryItem}>
            <Ionicons name="business" size={18} color={Colors.primary} />
            <Text style={styles.summaryValue}>{projects.length}</Text>
            <Text style={styles.summaryLabel}>Projects</Text>
          </View>
          <View style={styles.summaryDivider} />
          <View style={styles.summaryItem}>
            <Ionicons name="document-text" size={18} color={Colors.info} />
            <Text style={styles.summaryValue}>{projects.reduce((s, p) => s + p.dprs.pending_approvals, 0)}</Text>
            <Text style={styles.summaryLabel}>Pending</Text>
          </View>
          <View style={styles.summaryDivider} />
          <View style={styles.summaryItem}>
            <Ionicons name="today" size={18} color={Colors.success} />
            <Text style={styles.summaryValue}>{projects.reduce((s, p) => s + p.dprs.today, 0)}</Text>
            <Text style={styles.summaryLabel}>DPRs Today</Text>
          </View>
          <View style={styles.summaryDivider} />
          <View style={styles.summaryItem}>
            <Ionicons name="people" size={18} color={Colors.warning} />
            <Text style={styles.summaryValue}>{projects.reduce((s, p) => s + p.workers.recent_total, 0)}</Text>
            <Text style={styles.summaryLabel}>Workers</Text>
          </View>
        </View>

        {/* Project Cards */}
        {projects.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="business-outline" size={64} color={Colors.textMuted} />
            <Text style={styles.emptyTitle}>No Active Projects</Text>
            <Text style={styles.emptySubtitle}>Create a project from the Settings tab</Text>
          </View>
        ) : (
          projects.map((project) => {
            const isExpanded = expandedProject === project.project_id;
            const completionColor = getCompletionColor(project.completion_pct);
            
            return (
              <View key={project.project_id} style={styles.projectCard}>
                {/* Card Header */}
                <Pressable style={styles.cardHeader} onPress={() => toggleExpand(project.project_id)}>
                  <View style={styles.cardHeaderLeft}>
                    <Text style={styles.projectName}>{project.project_name}</Text>
                    {project.project_code && (
                      <Text style={styles.projectCode}>{project.project_code}</Text>
                    )}
                  </View>
                  <View style={styles.cardHeaderRight}>
                    {/* Completion badge */}
                    <View style={[styles.completionBadge, { backgroundColor: completionColor + '15' }]}>
                      <Text style={[styles.completionText, { color: completionColor }]}>
                        {project.completion_pct}%
                      </Text>
                    </View>
                    <Ionicons 
                      name={isExpanded ? "chevron-up" : "chevron-down"} 
                      size={20} 
                      color={Colors.textMuted} 
                    />
                  </View>
                </Pressable>

                {/* Completion Progress Bar */}
                <View style={styles.progressBarContainer}>
                  <View style={styles.progressBarBg}>
                    <View 
                      style={[
                        styles.progressBarFill, 
                        { 
                          width: `${Math.min(project.completion_pct, 100)}%`,
                          backgroundColor: completionColor 
                        }
                      ]} 
                    />
                  </View>
                </View>

                {/* Quick Stats Row */}
                <View style={styles.quickStats}>
                  <View style={styles.quickStatItem}>
                    <Text style={styles.quickStatValue}>{formatCurrency(project.budget.total_master)}</Text>
                    <Text style={styles.quickStatLabel}>Budget</Text>
                  </View>
                  <View style={styles.quickStatItem}>
                    <Text style={[styles.quickStatValue, { color: Colors.success }]}>
                      {formatCurrency(project.budget.total_remaining)}
                    </Text>
                    <Text style={styles.quickStatLabel}>Remaining</Text>
                  </View>
                  <View style={styles.quickStatItem}>
                    <Text style={styles.quickStatValue}>{project.dprs.total}</Text>
                    <Text style={styles.quickStatLabel}>DPRs</Text>
                  </View>
                  <View style={styles.quickStatItem}>
                    <Text style={[
                      styles.quickStatValue,
                      project.dprs.pending_approvals > 0 && { color: Colors.warning }
                    ]}>
                      {project.dprs.pending_approvals}
                    </Text>
                    <Text style={styles.quickStatLabel}>Pending</Text>
                  </View>
                </View>

                {/* Expanded Detail Section */}
                {isExpanded && (
                  <View style={styles.expandedSection}>
                    <View style={styles.divider} />

                    {/* Budget Breakdown */}
                    <Text style={styles.sectionLabel}>Budget Breakdown</Text>
                    <View style={styles.budgetGrid}>
                      <View style={styles.budgetRow}>
                        <Text style={styles.budgetRowLabel}>Total Master</Text>
                        <Text style={styles.budgetRowValue}>{formatCurrency(project.budget.total_master)}</Text>
                      </View>
                      <View style={styles.budgetRow}>
                        <Text style={styles.budgetRowLabel}>Committed</Text>
                        <Text style={[styles.budgetRowValue, { color: Colors.info }]}>{formatCurrency(project.budget.total_committed)}</Text>
                      </View>
                      <View style={styles.budgetRow}>
                        <Text style={styles.budgetRowLabel}>Certified</Text>
                        <Text style={[styles.budgetRowValue, { color: Colors.success }]}>{formatCurrency(project.budget.total_certified)}</Text>
                      </View>
                      <View style={styles.budgetRow}>
                        <Text style={styles.budgetRowLabel}>Remaining</Text>
                        <Text style={[styles.budgetRowValue, { color: project.budget.total_remaining > 0 ? Colors.success : Colors.error }]}>
                          {formatCurrency(project.budget.total_remaining)}
                        </Text>
                      </View>
                      {project.petty_cash_total > 0 && (
                        <View style={styles.budgetRow}>
                          <Text style={styles.budgetRowLabel}>Petty Cash Used</Text>
                          <Text style={[styles.budgetRowValue, { color: Colors.warning }]}>{formatCurrency(project.petty_cash_total)}</Text>
                        </View>
                      )}
                    </View>

                    {/* Category Breakdown */}
                    {project.budget.categories.length > 0 && (
                      <>
                        <Text style={[styles.sectionLabel, { marginTop: Spacing.md }]}>Category Wise</Text>
                        {project.budget.categories.map((cat) => (
                          <View key={cat.code_id} style={styles.categoryRow}>
                            <View style={styles.categoryNameCol}>
                              <Text style={styles.categoryName} numberOfLines={1}>{cat.code_name}</Text>
                            </View>
                            <View style={styles.categoryValCol}>
                              <Text style={styles.categoryApproved}>{formatCurrency(cat.approved_budget)}</Text>
                              <Text style={styles.categoryRemaining}>Rem: {formatCurrency(cat.remaining)}</Text>
                            </View>
                          </View>
                        ))}
                      </>
                    )}

                    <View style={styles.divider} />

                    {/* Action Buttons */}
                    <View style={styles.actionRow}>
                      <Pressable
                        style={styles.actionBtn}
                        onPress={() => handleProjectTap(project)}
                      >
                        <Ionicons name="document-text" size={18} color={Colors.white} />
                        <Text style={styles.actionBtnText}>View DPRs</Text>
                      </Pressable>
                      <Pressable
                        style={[styles.actionBtn, { backgroundColor: Colors.accent }]}
                        onPress={() => {
                          setSelectedProject({
                            project_id: project.project_id,
                            project_name: project.project_name,
                            project_code: project.project_code,
                          } as any);
                          router.push('/(admin)/worker-log' as any);
                        }}
                      >
                        <Ionicons name="people" size={18} color={Colors.white} />
                        <Text style={styles.actionBtnText}>Worker Log</Text>
                      </Pressable>
                    </View>
                  </View>
                )}
              </View>
            );
          })
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const getStyles = (Colors: any, Spacing: any, FontSizes: any, BorderRadius: any) => StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f2f5' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: Spacing.md, color: Colors.textSecondary },
  scrollContent: { padding: Spacing.md, paddingBottom: 100 },

  // Page header
  pageHeader: { marginBottom: Spacing.md },
  pageTitle: { fontSize: 24, fontWeight: '700', color: Colors.text },
  pageSubtitle: { fontSize: FontSizes.sm, color: Colors.textSecondary, marginTop: 2 },

  // Summary strip
  summaryStrip: { 
    flexDirection: 'row', alignItems: 'center', 
    backgroundColor: Colors.white, borderRadius: BorderRadius.lg, 
    padding: Spacing.md, marginBottom: Spacing.lg, 
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 4, elevation: 2,
  },
  summaryItem: { flex: 1, alignItems: 'center', gap: 2 },
  summaryValue: { fontSize: FontSizes.lg, fontWeight: '700', color: Colors.text },
  summaryLabel: { fontSize: 10, color: Colors.textMuted, textTransform: 'uppercase', fontWeight: '500' },
  summaryDivider: { width: 1, height: 30, backgroundColor: Colors.border },

  // Empty state
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text, marginTop: Spacing.md },
  emptySubtitle: { fontSize: FontSizes.md, color: Colors.textMuted, marginTop: Spacing.xs },

  // Project card
  projectCard: { 
    backgroundColor: Colors.white, borderRadius: BorderRadius.lg, 
    marginBottom: Spacing.md, overflow: 'hidden',
    shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: Spacing.md, paddingBottom: Spacing.sm },
  cardHeaderLeft: { flex: 1 },
  cardHeaderRight: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  projectName: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text },
  projectCode: { fontSize: FontSizes.xs, color: Colors.textMuted, marginTop: 2 },

  // Completion
  completionBadge: { paddingHorizontal: Spacing.sm, paddingVertical: 3, borderRadius: BorderRadius.full },
  completionText: { fontSize: FontSizes.sm, fontWeight: '700' },
  progressBarContainer: { paddingHorizontal: Spacing.md, paddingBottom: Spacing.sm },
  progressBarBg: { height: 4, backgroundColor: '#e5e7eb', borderRadius: 2 },
  progressBarFill: { height: 4, borderRadius: 2, minWidth: 2 },

  // Quick stats
  quickStats: { flexDirection: 'row', paddingHorizontal: Spacing.md, paddingBottom: Spacing.md },
  quickStatItem: { flex: 1, alignItems: 'center' },
  quickStatValue: { fontSize: FontSizes.md, fontWeight: '700', color: Colors.text },
  quickStatLabel: { fontSize: 10, color: Colors.textMuted, marginTop: 1, textTransform: 'uppercase' },

  // Expanded section
  expandedSection: { paddingHorizontal: Spacing.md, paddingBottom: Spacing.md },
  divider: { height: 1, backgroundColor: Colors.border, marginVertical: Spacing.sm },
  sectionLabel: { fontSize: FontSizes.sm, fontWeight: '700', color: Colors.textSecondary, textTransform: 'uppercase', marginBottom: Spacing.sm },

  // Budget grid
  budgetGrid: { gap: Spacing.xs },
  budgetRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  budgetRowLabel: { fontSize: FontSizes.sm, color: Colors.textSecondary },
  budgetRowValue: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.text },

  // Category breakdown
  categoryRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 4, borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  categoryNameCol: { flex: 2 },
  categoryName: { fontSize: FontSizes.sm, color: Colors.text },
  categoryValCol: { flex: 1, alignItems: 'flex-end' },
  categoryApproved: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.text },
  categoryRemaining: { fontSize: 10, color: Colors.textMuted },

  // Action row
  actionRow: { flexDirection: 'row', gap: Spacing.sm, marginTop: Spacing.sm },
  actionBtn: { 
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: Spacing.xs,
    backgroundColor: Colors.primary, paddingVertical: Spacing.sm, borderRadius: BorderRadius.md,
  },
  actionBtnText: { color: Colors.white, fontWeight: '600', fontSize: FontSizes.sm },
});
