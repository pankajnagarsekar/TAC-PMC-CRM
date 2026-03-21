// ADMIN DASHBOARD — PROJECT-SPECIFIC FINANCIAL INTELLIGENCE
// Replicates the Web Dashboard logic on Mobile
// Shows financial KPIs and Budget Utilization for the selected project

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    Pressable,
    ActivityIndicator,
    RefreshControl,
    Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useProject } from '../../contexts/ProjectContext';
import api from '../../services/apiClient';
import { Card, Button } from '../../components/ui';
import { useTheme } from '../../contexts/ThemeContext';
import { DerivedFinancialState } from '../../types/api';

const { width } = Dimensions.get('window');

const formatCurrency = (amount: number): string => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount.toLocaleString('en-IN')}`;
};

const formatPercent = (val: number) => `${val.toFixed(1)}%`;

export default function ProjectDashboard() {
    const router = useRouter();
    const { selectedProject } = useProject();
    const { colors: Colors, spacing: Spacing } = useTheme();

    const [financials, setFinancials] = useState<DerivedFinancialState[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    const fetchFinancials = useCallback(async () => {
        if (!selectedProject?.project_id) {
            setLoading(false);
            setRefreshing(false);
            return;
        }

        try {
            const data = await api.financial.getProjectFinancials(selectedProject.project_id);
            setFinancials(data || []);
        } catch (err: any) {
            console.error('Error fetching financials:', err);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [selectedProject?.project_id]);

    useEffect(() => {
        fetchFinancials();
    }, [fetchFinancials]);

    const onRefresh = () => {
        setRefreshing(true);
        fetchFinancials();
    };

    const aggregateMetrics = useMemo(() => {
        const totalBudget = financials.reduce((sum, f) => sum + (f.original_budget || 0), 0);
        const totalCommitted = financials.reduce((sum, f) => sum + (f.committed_value || 0), 0);
        const totalCertified = financials.reduce((sum, f) => sum + (f.certified_value || 0), 0);
        const totalRemaining = financials.reduce((sum, f) => sum + (f.balance_budget_remaining || 0), 0);
        const commitPct = totalBudget > 0 ? (totalCommitted / totalBudget) * 100 : 0;

        return { totalBudget, totalCommitted, totalCertified, totalRemaining, commitPct };
    }, [financials]);

    const topCategories = useMemo(() => {
        return [...financials]
            .sort((a, b) => (b.original_budget || 0) - (a.original_budget || 0))
            .slice(0, 5);
    }, [financials]);

    if (!selectedProject) {
        return (
            <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }}>
                <View style={styles.emptyContainer}>
                    <View style={styles.emptyIconCircle}>
                        <Ionicons name="grid-outline" size={48} color={Colors.primary} />
                    </View>
                    <Text style={[styles.emptyTitle, { color: Colors.text }]}>No Project Selected</Text>
                    <Text style={[styles.emptySubtitle, { color: Colors.textMuted }]}>
                        Select an active operational project to initialize financial intelligence.
                    </Text>
                    <Button
                        title="Browse Projects"
                        onPress={() => router.push('/(admin)/projects')}
                        style={{ marginTop: Spacing.xl, paddingHorizontal: Spacing.xl }}
                    />
                </View>
            </SafeAreaView>
        );
    }

    if (loading && !refreshing) {
        return (
            <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color={Colors.primary} />
                    <Text style={[styles.loadingText, { color: Colors.textSecondary }]}>Crunching financial data...</Text>
                </View>
            </SafeAreaView>
        );
    }

    return (
        <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }} edges={['top']}>
            <View style={styles.header}>
                <View>
                    <Text style={[styles.headerTitle, { color: Colors.text }]}>Intelligence Dashboard</Text>
                    <Text style={[styles.headerSubtitle, { color: Colors.textSecondary }]}>{selectedProject.project_name}</Text>
                </View>
                <Pressable
                    style={[styles.switchBtn, { backgroundColor: Colors.surface }]}
                    onPress={() => router.push('/(admin)/projects')}
                >
                    <Ionicons name="swap-horizontal" size={16} color={Colors.primary} />
                    <Text style={[styles.switchBtnText, { color: Colors.primary }]}>Switch</Text>
                </Pressable>
            </View>

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            >
                <View style={styles.kpiGrid}>
                    <Card style={styles.kpiCard}>
                        <Text style={styles.kpiLabel}>Total Budget</Text>
                        <Text style={[styles.kpiValue, { color: Colors.text }]}>{formatCurrency(aggregateMetrics.totalBudget)}</Text>
                        <View style={styles.kpiFooter}>
                            <View style={[styles.pill, { backgroundColor: Colors.surface }]}>
                                <Text style={styles.pillText}>Baseline</Text>
                            </View>
                        </View>
                    </Card>

                    <Card style={styles.kpiCard}>
                        <Text style={styles.kpiLabel}>Committed Value</Text>
                        <Text style={[styles.kpiValue, { color: Colors.text }]}>{formatCurrency(aggregateMetrics.totalCommitted)}</Text>
                        <View style={styles.kpiFooter}>
                            <View style={styles.progressContainer}>
                                <View style={[styles.progressBar, { backgroundColor: Colors.divider }]}>
                                    <View style={[styles.progressFill, { width: `${Math.min(100, aggregateMetrics.commitPct)}%`, backgroundColor: '#6366f1' }]} />
                                </View>
                                <Text style={styles.pctText}>{formatPercent(aggregateMetrics.commitPct)}</Text>
                            </View>
                        </View>
                    </Card>

                    <Card style={styles.kpiCard}>
                        <Text style={styles.kpiLabel}>Certified (Billed)</Text>
                        <Text style={[styles.kpiValue, { color: Colors.text }]}>{formatCurrency(aggregateMetrics.totalCertified)}</Text>
                        <View style={styles.kpiFooter}>
                            <View style={[styles.pill, { backgroundColor: Colors.success + '15' }]}>
                                <Ionicons name="trending-up" size={10} color={Colors.success} />
                                <Text style={[styles.pillText, { color: Colors.success }]}>On Track</Text>
                            </View>
                        </View>
                    </Card>

                    <Card style={styles.kpiCard}>
                        <Text style={styles.kpiLabel}>Allocated Balance</Text>
                        <Text style={[styles.kpiValue, { color: aggregateMetrics.totalRemaining < 0 ? Colors.error : Colors.success }]}>
                            {formatCurrency(aggregateMetrics.totalRemaining)}
                        </Text>
                        <View style={styles.kpiFooter}>
                            <View style={[styles.pill, { backgroundColor: (aggregateMetrics.totalRemaining < 0 ? Colors.error : Colors.success) + '15' }]}>
                                <Text style={[styles.pillText, { color: aggregateMetrics.totalRemaining < 0 ? Colors.error : Colors.success }]}>
                                    {aggregateMetrics.totalRemaining < 0 ? 'Over-Budget' : 'Healthy'}
                                </Text>
                            </View>
                        </View>
                    </Card>
                </View>

                <View style={styles.shortcutGrid}>
                    <Pressable style={styles.shortcutItem} onPress={() => router.push('/(admin)/petty-cash')}>
                        <View style={[styles.shortcutIcon, { backgroundColor: Colors.success }]}>
                            <Ionicons name="wallet" size={20} color={Colors.white} />
                        </View>
                        <Text style={[styles.shortcutLabel, { color: Colors.text }]}>Site Funds</Text>
                    </Pressable>
                    <Pressable style={styles.shortcutItem} onPress={() => router.push('/(admin)/dpr')}>
                        <View style={[styles.shortcutIcon, { backgroundColor: Colors.primary }]}>
                            <Ionicons name="document-text" size={20} color={Colors.white} />
                        </View>
                        <Text style={[styles.shortcutLabel, { color: Colors.text }]}>View DPRs</Text>
                    </Pressable>
                    <Pressable style={styles.shortcutItem} onPress={() => router.push('/(admin)/worker-log')}>
                        <View style={[styles.shortcutIcon, { backgroundColor: Colors.accent }]}>
                            <Ionicons name="people" size={20} color={Colors.white} />
                        </View>
                        <Text style={[styles.shortcutLabel, { color: Colors.text }]}>Worker Log</Text>
                    </Pressable>
                    <Pressable style={styles.shortcutItem} onPress={() => router.push('/(admin)/settings')}>
                        <View style={[styles.shortcutIcon, { backgroundColor: Colors.textMuted }]}>
                            <Ionicons name="settings" size={20} color={Colors.white} />
                        </View>
                        <Text style={[styles.shortcutLabel, { color: Colors.text }]}>Settings</Text>
                    </Pressable>
                </View>

                <Card style={styles.chartCard}>
                    <Text style={[styles.sectionTitle, { color: Colors.text }]}>Budget vs Commitment</Text>
                    <View style={styles.chartLegend}>
                        <View style={styles.legendItem}>
                            <View style={[styles.legendDot, { backgroundColor: '#6366f1' }]} />
                            <Text style={styles.legendText}>Budget</Text>
                        </View>
                        <View style={styles.legendItem}>
                            <View style={[styles.legendDot, { backgroundColor: Colors.accent }]} />
                            <Text style={styles.legendText}>Used</Text>
                        </View>
                    </View>

                    <View style={styles.barList}>
                        {topCategories.map((cat) => {
                            const maxVal = Math.max(...topCategories.map(c => c.original_budget || 1));
                            const budgetWidth = ((cat.original_budget || 0) / maxVal) * 100;
                            const usedWidth = ((cat.committed_value || 0) / (cat.original_budget || 1)) * 100;

                            return (
                                <View key={cat.category_id} style={styles.barRow}>
                                    <Text style={[styles.barLabel, { color: Colors.textSecondary }]} numberOfLines={1}>
                                        {cat.category_id}
                                    </Text>
                                    <View style={styles.barContainer}>
                                        <View style={[styles.budgetBar, { width: `${budgetWidth}%`, backgroundColor: '#6366f120' }]}>
                                            <View style={[styles.usedBar, { width: `${Math.min(100, usedWidth)}%`, backgroundColor: usedWidth > 100 ? Colors.error : Colors.accent }]} />
                                        </View>
                                    </View>
                                </View>
                            );
                        })}
                    </View>
                </Card>

                <Card style={styles.ledgerCard} padding="none">
                    <View style={styles.ledgerHeader}>
                        <View style={[styles.ledgerIcon, { backgroundColor: Colors.text }]}>
                            <Ionicons name="list" size={14} color={Colors.background} />
                        </View>
                        <Text style={[styles.ledgerTitle, { color: Colors.text }]}>Budget Utilization Ledger</Text>
                    </View>

                    <View style={[styles.tableHeader, { backgroundColor: Colors.surface }]}>
                        <Text style={[styles.columnHeader, { flex: 2 }]}>CATEGORY</Text>
                        <Text style={[styles.columnHeader, { flex: 1.5, textAlign: 'right' }]}>BUDGET</Text>
                        <Text style={[styles.columnHeader, { flex: 1.5, textAlign: 'right' }]}>BALANCE</Text>
                    </View>

                    {financials.map((f) => {
                        const utilPct = f.original_budget > 0 ? (f.committed_value / f.original_budget) * 100 : 0;
                        return (
                            <View key={f.category_id} style={styles.tableRow}>
                                <View style={{ flex: 2 }}>
                                    <Text style={[styles.rowTitle, { color: Colors.text }]} numberOfLines={1}>{f.category_id}</Text>
                                    <View style={styles.rowUtilization}>
                                        <View style={[styles.miniProgressBar, { backgroundColor: Colors.divider }]}>
                                            <View style={[styles.miniProgressFill, { width: `${Math.min(100, utilPct)}%`, backgroundColor: f.over_commit_flag ? Colors.error : Colors.primary }]} />
                                        </View>
                                        <Text style={styles.miniPct}>{formatPercent(utilPct)}</Text>
                                    </View>
                                </View>
                                <Text style={[styles.rowValue, { flex: 1.5, color: Colors.textSecondary }]}>{formatCurrency(f.original_budget)}</Text>
                                <Text style={[styles.rowValue, { flex: 1.5, color: f.balance_budget_remaining < 0 ? Colors.error : Colors.text, fontWeight: '700' }]}>
                                    {formatCurrency(f.balance_budget_remaining)}
                                </Text>
                            </View>
                        );
                    })}
                </Card>
            </ScrollView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
    loadingText: { marginTop: 16, fontSize: 14, fontWeight: '500' },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 20,
        paddingVertical: 16
    },
    headerTitle: { fontSize: 20, fontWeight: '800', letterSpacing: -0.5 },
    headerSubtitle: { fontSize: 13, marginTop: 2 },
    switchBtn: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 8
    },
    switchBtnText: { fontSize: 12, fontWeight: '700' },

    scrollContent: { padding: 16, paddingBottom: 100 },

    // Empty State
    emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
    emptyIconCircle: { width: 80, height: 80, borderRadius: 40, backgroundColor: '#f3f4f6', alignItems: 'center', justifyContent: 'center', marginBottom: 20 },
    emptyTitle: { fontSize: 18, fontWeight: '700', marginBottom: 8 },
    emptySubtitle: { fontSize: 14, textAlign: 'center', lineHeight: 20 },

    // KPI Grid
    kpiGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginBottom: 24 },
    kpiCard: { width: (width - 44) / 2, padding: 16 },
    kpiLabel: { fontSize: 10, fontWeight: '700', color: '#6b7280', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
    kpiValue: { fontSize: 18, fontWeight: '900' },
    kpiFooter: { marginTop: 12 },
    pill: { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4, flexDirection: 'row', alignItems: 'center', gap: 4 },
    pillText: { fontSize: 10, fontWeight: '800', color: '#6b7280' },

    progressContainer: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    progressBar: { flex: 1, height: 4, borderRadius: 2, overflow: 'hidden' },
    progressFill: { height: '100%', borderRadius: 2 },
    pctText: { fontSize: 10, fontWeight: '700', color: '#9ca3af', width: 35 },

    // Shortcuts
    shortcutGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
    shortcutItem: { alignItems: 'center', gap: 8 },
    shortcutIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
    shortcutLabel: { fontSize: 11, fontWeight: '700' },

    // Chart
    chartCard: { marginBottom: 24, padding: 20 },
    sectionTitle: { fontSize: 14, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 16 },
    chartLegend: { flexDirection: 'row', gap: 16, marginBottom: 20 },
    legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
    legendDot: { width: 8, height: 8, borderRadius: 4 },
    legendText: { fontSize: 10, fontWeight: '600', color: '#6b7280' },
    barList: { gap: 12 },
    barRow: { gap: 6 },
    barLabel: { fontSize: 11, fontWeight: '600' },
    barContainer: { height: 8, backgroundColor: '#f3f4f6', borderRadius: 4, overflow: 'hidden' },
    budgetBar: { height: '100%', borderRadius: 4 },
    usedBar: { height: '100%', borderRadius: 4 },

    // Ledger
    ledgerCard: { marginBottom: 24 },
    ledgerHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 16, borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
    ledgerIcon: { width: 24, height: 24, borderRadius: 6, alignItems: 'center', justifyContent: 'center' },
    ledgerTitle: { fontSize: 13, fontWeight: '800', textTransform: 'uppercase' },
    tableHeader: { flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 10 },
    columnHeader: { fontSize: 10, fontWeight: '700', color: '#9ca3af' },
    tableRow: { flexDirection: 'row', paddingHorizontal: 16, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: '#f3f4f6', alignItems: 'center' },
    rowTitle: { fontSize: 13, fontWeight: '600', marginBottom: 4 },
    rowValue: { fontSize: 13, textAlign: 'right' },
    rowUtilization: { flexDirection: 'row', alignItems: 'center', gap: 8 },
    miniProgressBar: { width: 60, height: 4, borderRadius: 2, overflow: 'hidden' },
    miniProgressFill: { height: '100%' },
    miniPct: { fontSize: 10, fontWeight: '600', color: '#9ca3af' },
});
