import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    Pressable,
    RefreshControl,
    Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons, Feather } from '@expo/vector-icons';
import { useProject } from '../../contexts/ProjectContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import api, { cashApi } from '../../services/apiClient';
import { Button, Card, BlueprintGrid, LoadingScreen } from '../../components/ui';
import { DerivedFinancialState, AdminDashboardData, Image as ProjectImage, Task } from '../../types/api';
import type { CashCategory } from '../../services/apiClient';

// --------------------------------------------------------
// HELPERS
// --------------------------------------------------------

const formatCurrency = (amount: number): string => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
    return `₹${amount.toFixed(0)}`;
};

const formatPercent = (value: number): string => `${Math.round(value)}%`;

// --------------------------------------------------------
// SUB-COMPONENTS
// --------------------------------------------------------

interface KPICardProps {
    label: string;
    value: string;
    icon: string;
    iconColor: string;
    trend?: { value: string; isPositive: boolean };
    colors: Record<string, string>;
}

const KPICard = React.memo(({ label, value, icon, iconColor, trend, colors }: KPICardProps) => {
    const { typography: Typography } = useTheme();
    return (
        <Card variant="elevated" style={styles.kpiCard} padding="sm">
            <View style={[styles.kpiIconBox, { backgroundColor: iconColor + '18' }]}>
                <Ionicons name={icon as any} size={16} color={iconColor} />
            </View>
            <Text style={[styles.kpiLabel, { color: colors.textSecondary, ...Typography.overline }]}>{label}</Text>
            <Text style={[styles.kpiValue, { color: colors.text, ...Typography.heading1 }]}>
                {value}
            </Text>
            {trend && (
                <View style={styles.kpiTrend}>
                    <Ionicons
                        name={trend.isPositive ? 'trending-up' : 'trending-down'}
                        size={10}
                        color={trend.isPositive ? '#10b981' : '#ef4444'}
                    />
                    <Text style={[styles.kpiTrendText, { color: trend.isPositive ? '#10b981' : '#ef4444', ...Typography.caption }]}>
                        {trend.value}
                    </Text>
                </View>
            )}
        </Card>
    );
});

interface ProgressRowProps {
    label: string;
    value: number;
    total: number;
    color: string;
    colors: Record<string, string>;
}

const ProgressRow = React.memo(({ label, value, total, color, colors }: ProgressRowProps) => {
    const { typography: Typography } = useTheme();
    const pct = total > 0 ? Math.min(100, Math.round((value / total) * 100)) : 0;
    return (
        <View style={styles.progressItem}>
            <View style={styles.progressHeader}>
                <Text style={[styles.progressLabel, { color: colors.text, ...Typography.subtitle }]} numberOfLines={1}>{label}</Text>
                <Text style={[styles.progressPct, { color: colors.textSecondary, ...Typography.caption }]}>{pct}%</Text>
            </View>
            <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
                <View style={[styles.progressFill, { width: `${Math.max(2, pct)}%`, backgroundColor: color }]} />
            </View>
        </View>
    );
});

interface QuickActionProps {
    label: string;
    icon: string;
    route: string;
    colors: Record<string, string>;
    onPress: (route: string) => void;
}

const QuickAction = React.memo(({ label, icon, route, colors, onPress }: QuickActionProps) => {
    const { typography: Typography } = useTheme();
    return (
        <Pressable
            style={({ pressed }) => [
                styles.actionBox,
                {
                    backgroundColor: pressed ? colors.surface : colors.cardBg,
                    borderColor: colors.border,
                    opacity: pressed ? 0.8 : 1,
                    transform: [{ scale: pressed ? 0.96 : 1 }]
                }
            ]}
            onPress={() => onPress(route)}
        >
            <Feather name={icon as any} size={20} color={colors.primary} />
            <Text style={[styles.actionLabel, { color: colors.text, ...Typography.overline }]}>{label}</Text>
        </Pressable>
    );
});

// --------------------------------------------------------
// MAIN COMPONENT
// --------------------------------------------------------

export default function ProjectDashboard() {
    const router = useRouter();
    const { selectedProject } = useProject();
    const { colors: Colors, spacing: Spacing, typography: Typography, isDark, toggleTheme } = useTheme();
    const { user } = useAuth();

    const [financials, setFinancials] = useState<DerivedFinancialState[]>([]);
    const [stats, setStats] = useState<AdminDashboardData | null>(null);
    const [latestImage, setLatestImage] = useState<ProjectImage | null>(null);
    const [fundCategories, setFundCategories] = useState<CashCategory[]>([]);
    const [recentTasks, setRecentTasks] = useState<Task[]>([]);
    const [refreshing, setRefreshing] = useState(false);
    const [loading, setLoading] = useState(true);

    // Redirect if no project selected
    useEffect(() => {
        if (!selectedProject) {
            requestAnimationFrame(() => {
                router.replace({
                  pathname: '/(admin)/select-project',
                  params: { redirect: '/(admin)/dashboard' }
                });
            });
        }
    }, [selectedProject, router]);

    const fetchData = useCallback(async () => {
        if (!selectedProject?.project_id) {
            setRefreshing(false);
            setLoading(false);
            return;
        }

        try {
            const [finData, statsData, imageData, cashData, tasksData] = await Promise.all([
                api.financial.getProjectFinancials(selectedProject.project_id),
                api.dashboard.getProjectDashboard(selectedProject.project_id),
                api.images.getAll(selectedProject.project_id),
                cashApi.getSummary(selectedProject.project_id).catch(() => null),
                api.tasks.getForProject(selectedProject.project_id).catch(() => []),
            ]);

            setFinancials(finData || []);
            setStats(statsData || null);
            if (imageData && imageData.length > 0) {
                setLatestImage(imageData[0]);
            }
            if (cashData?.categories) {
                setFundCategories(cashData.categories);
            }
            setRecentTasks(tasksData.slice(0, 3));
        } catch (err: unknown) {
            console.error('Error fetching dashboard data:', err);
        } finally {
            setRefreshing(false);
            setLoading(false);
        }
    }, [selectedProject?.project_id]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const onRefresh = () => {
        setRefreshing(true);
        fetchData();
    };

    // Derived values
    const budgetTotal = stats?.financials?.total_budget || 0;
    const budgetSpent = stats?.financials?.actual_cost || stats?.financials?.certified || 0;
    const budgetRemaining = stats?.financials?.remaining || (budgetTotal - budgetSpent);
    const budgetUtilPct = budgetTotal > 0 ? Math.round((budgetSpent / budgetTotal) * 100) : 0;

    const pettyCash = useMemo(() =>
        fundCategories.find(c => c.category_name.toLowerCase().includes('petty')),
        [fundCategories]
    );
    const siteOverhead = useMemo(() =>
        fundCategories.find(c => c.category_name.toLowerCase().includes('ovh') || c.category_name.toLowerCase().includes('overhead')),
        [fundCategories]
    );

    const handleNavigation = useCallback((route: string) => {
        router.push(route as any);
    }, [router]);

    if (loading && !refreshing) {
        return <LoadingScreen message="Initializing Intelligence..." />;
    }

    if (!selectedProject) {
        return (
            <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }}>
                <View style={styles.emptyContainer}>
                    <View style={[styles.emptyIconCircle, { backgroundColor: Colors.surface }]}>
                        <Ionicons name="grid-outline" size={48} color={Colors.primary} />
                    </View>
                    <Text style={[styles.emptyTitle, { color: Colors.text, ...Typography.heading1 }]}>No Project Selected</Text>
                    <Text style={[styles.emptySubtitle, { color: Colors.textMuted, ...Typography.body }]}>
                        Select an active operational project to initialize financial intelligence.
                    </Text>
                    <Button
                        title="Browse Projects"
                        onPress={() => router.push('/(admin)/projects')}
                        style={{ marginTop: Spacing.xl }}
                    />
                </View>
            </SafeAreaView>
        );
    }

    return (
        <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }} edges={['top']}>
            <BlueprintGrid>
                <ScrollView
                    showsVerticalScrollIndicator={false}
                    contentContainerStyle={styles.scrollContent}
                    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.primary} />}
                >
                    {/* ── Header ── */}
                    <Card variant="elevated" style={styles.header} padding="md">
                        <View style={styles.headerRow}>
                            <View style={styles.profileBox}>
                                <View style={[styles.avatar, { backgroundColor: Colors.primary }]}>
                                    <Text style={[styles.avatarText, { ...Typography.subtitle, color: 'white' }]}>{user?.name?.[0]?.toUpperCase() || 'A'}</Text>
                                </View>
                                <View>
                                    <Text style={[styles.welcomeText, { color: Colors.textSecondary, ...Typography.overline }]}>TAC PMC CRM</Text>
                                    <Text style={[styles.userName, { color: Colors.text, ...Typography.heading2 }]}>{user?.name || 'Administrator'}</Text>
                                </View>
                            </View>
                            <View style={styles.headerActions}>
                                <Pressable onPress={() => router.push('/(admin)/notifications')} style={[styles.iconBtn, { borderColor: Colors.border }]}>
                                    <Ionicons name="notifications-outline" size={18} color={Colors.text} />
                                </Pressable>
                                <Pressable onPress={toggleTheme} style={[styles.iconBtn, { borderColor: Colors.border }]}>
                                    <Feather name={isDark ? 'sun' : 'moon'} size={18} color={Colors.text} />
                                </Pressable>
                            </View>
                        </View>

                        <View style={[styles.projectBar, { borderTopColor: Colors.border }]}>
                            <View style={{ flex: 1 }}>
                                <Text style={[styles.projectLabel, { color: Colors.textSecondary, ...Typography.overline }]}>ACTIVE SITE</Text>
                                <Text style={[styles.projectName, { color: Colors.text, ...Typography.subtitle }]} numberOfLines={1}>{selectedProject.project_name}</Text>
                            </View>
                            <Pressable
                                style={[styles.switchChip, { backgroundColor: Colors.primary }]}
                                onPress={() => router.push('/(admin)/projects')}
                            >
                                <Text style={[styles.switchText, { color: Colors.textInverse, ...Typography.overline }]}>SWITCH</Text>
                            </Pressable>
                        </View>
                    </Card>

                    {/* ── KPI Strip (4 cards) ── */}
                    <View style={styles.kpiRow}>
                        <KPICard
                            label="PROJECT VALUE"
                            value={formatCurrency(budgetTotal)}
                            icon="wallet-outline"
                            iconColor="#3b82f6"
                            trend={{
                                value: `SPI ${stats?.indicators?.spi?.toFixed(2) || '1.00'}`,
                                isPositive: Number(stats?.indicators?.spi || 0) >= 1,
                            }}
                            colors={Colors}
                        />
                        <KPICard
                            label="ACTIVE TASKS"
                            value={String(stats?.active_tasks || 0).padStart(2, '0')}
                            icon="list-outline"
                            iconColor="#8b5cf6"
                            trend={
                                (stats?.overdue_tasks || 0) > 0
                                    ? { value: `${stats?.overdue_tasks} overdue`, isPositive: false }
                                    : { value: 'On track', isPositive: true }
                            }
                            colors={Colors}
                        />
                    </View>
                    <View style={styles.kpiRow}>
                        <KPICard
                            label="BUDGET USED"
                            value={formatPercent(budgetUtilPct)}
                            icon="pie-chart-outline"
                            iconColor={budgetUtilPct > 80 ? '#ef4444' : '#10b981'}
                            colors={Colors}
                        />
                        <KPICard
                            label="COMPLETION"
                            value={formatPercent(stats?.completion_percentage || 0)}
                            icon="checkmark-circle-outline"
                            iconColor="#f59e0b"
                            colors={Colors}
                        />
                    </View>

                    {/* ── Financial Summary ── */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.overline }]}>FINANCIAL OVERVIEW</Text>
                    </View>
                    <Card variant="elevated" padding="md" style={styles.finCard}>
                        <View style={styles.finRow}>
                            <View style={styles.finItem}>
                                <Text style={[styles.finLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Total Budget</Text>
                                <Text style={[styles.finValue, { color: Colors.text, ...Typography.subtitle }]}>{formatCurrency(budgetTotal)}</Text>
                            </View>
                            <View style={[styles.finDivider, { backgroundColor: Colors.border }]} />
                            <View style={styles.finItem}>
                                <Text style={[styles.finLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Spent</Text>
                                <Text style={[styles.finValue, { color: budgetUtilPct > 80 ? '#ef4444' : Colors.text, ...Typography.subtitle }]}>{formatCurrency(budgetSpent)}</Text>
                            </View>
                            <View style={[styles.finDivider, { backgroundColor: Colors.border }]} />
                            <View style={styles.finItem}>
                                <Text style={[styles.finLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Remaining</Text>
                                <Text style={[styles.finValue, { color: '#10b981', ...Typography.subtitle }]}>{formatCurrency(budgetRemaining)}</Text>
                            </View>
                        </View>
                        {/* Budget utilization bar */}
                        <View style={[styles.budgetBarTrack, { backgroundColor: Colors.border }]}>
                            <View
                                style={[
                                    styles.budgetBarFill,
                                    {
                                        width: `${Math.min(100, budgetUtilPct)}%`,
                                        backgroundColor: budgetUtilPct > 90 ? '#ef4444' : budgetUtilPct > 70 ? '#f59e0b' : '#10b981',
                                    },
                                ]}
                            />
                        </View>
                    </Card>

                    {/* ── Funds Summary (Petty Cash + Site Overheads) ── */}
                    {(pettyCash || siteOverhead) && (
                        <>
                            <View style={styles.sectionHeader}>
                                <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.overline }]}>SITE FUNDS</Text>
                                <Pressable onPress={() => router.push('/(admin)/petty-cash')}>
                                    <Text style={{ color: Colors.primary, ...Typography.caption }}>VIEW ALL</Text>
                                </Pressable>
                            </View>
                            <View style={styles.fundsRow}>
                                {pettyCash && (
                                    <Card variant="elevated" style={styles.fundCard} padding="sm" onPress={() => router.push('/(admin)/petty-cash')}>
                                        <Text style={[styles.fundLabel, { color: Colors.textSecondary, ...Typography.overline }]}>PETTY CASH</Text>
                                        <Text style={[styles.fundValue, { color: pettyCash.is_negative ? '#ef4444' : Colors.text, ...Typography.heading2 }]}>
                                            {formatCurrency(pettyCash.cash_in_hand)}
                                        </Text>
                                        <Text style={[styles.fundAlloc, { color: Colors.textMuted, ...Typography.caption }]}>
                                            of {formatCurrency(pettyCash.allocation_total)}
                                        </Text>
                                    </Card>
                                )}
                                {siteOverhead && (
                                    <Card variant="elevated" style={styles.fundCard} padding="sm" onPress={() => router.push('/(admin)/petty-cash')}>
                                        <Text style={[styles.fundLabel, { color: Colors.textSecondary, ...Typography.overline }]}>SITE OVERHEADS</Text>
                                        <Text style={[styles.fundValue, { color: siteOverhead.is_negative ? '#ef4444' : Colors.text, ...Typography.heading2 }]}>
                                            {formatCurrency(siteOverhead.cash_in_hand)}
                                        </Text>
                                        <Text style={[styles.fundAlloc, { color: Colors.textMuted, ...Typography.caption }]}>
                                            of {formatCurrency(siteOverhead.allocation_total)}
                                        </Text>
                                    </Card>
                                )}
                            </View>
                        </>
                    )}

                    {/* ── Construction Progress ── */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.overline }]}>CONSTRUCTION PROGRESS</Text>
                    </View>
                    <Card variant="elevated" style={styles.progressCard} padding="md">
                        {financials.length > 0 ? financials.slice(0, 4).map((item, idx) => (
                            <ProgressRow
                                key={idx}
                                label={item.category_name || item.category_id}
                                value={Number(item.certified_value || 0)}
                                total={Number(item.original_budget)}
                                color={
                                    Number(item.certified_value || 0) >= Number(item.original_budget)
                                        ? '#10b981'
                                        : Colors.primary
                                }
                                colors={Colors}
                            />
                        )) : (
                            <Text style={{ color: Colors.textSecondary, ...Typography.body, textAlign: 'center', fontStyle: 'italic' }}>
                                No financial absorption data available.
                            </Text>
                        )}
                    </Card>

                    {/* ── Recent Tasks ── */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.overline }]}>RECENT TASKS</Text>
                        <Pressable onPress={() => router.push('/(admin)/tasks')}>
                            <Text style={{ color: Colors.primary, ...Typography.caption }}>VIEW ALL</Text>
                        </Pressable>
                    </View>
                    <Card variant="elevated" style={styles.taskCard} padding="md">
                        {recentTasks.length > 0 ? recentTasks.map((task, idx) => (
                            <View key={task.id || idx} style={[styles.taskItem, idx < recentTasks.length - 1 && { borderBottomWidth: 1, borderBottomColor: Colors.border, paddingBottom: 10 }]}>
                                <View style={styles.taskHeader}>
                                    <Text style={[styles.taskDesc, { color: Colors.text, ...Typography.body }]} numberOfLines={1}>{task.task_description}</Text>
                                    <View style={[styles.statusBadge, { backgroundColor: task.status === 'Open' ? '#ef444420' : '#10b98120' }]}>
                                        <Text style={[styles.statusText, { color: task.status === 'Open' ? '#ef4444' : '#10b981', ...Typography.overline }]}>{task.status}</Text>
                                    </View>
                                </View>
                                <Text style={[styles.taskMeta, { color: Colors.textMuted, ...Typography.caption }]}>
                                    Assigned to: {task.assigned_to_name} • {task.deadline ? new Date(task.deadline).toLocaleDateString() : 'No deadline'}
                                </Text>
                            </View>
                        )) : (
                            <Text style={{ color: Colors.textSecondary, ...Typography.body, textAlign: 'center', fontStyle: 'italic' }}>
                                No active tasks found for this project.
                            </Text>
                        )}
                    </Card>

                    {/* ── Site Intelligence ── */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.overline }]}>SITE INTELLIGENCE</Text>
                        <Pressable><Text style={{ color: Colors.primary, ...Typography.caption }}>LIVE VIEW</Text></Pressable>
                    </View>
                    <Card variant="elevated" style={styles.cameraFrame} padding="none">
                        <Image
                            source={{ uri: latestImage ? `data:image/jpeg;base64,${latestImage.image_base64}` : 'https://images.unsplash.com/photo-1541888946425-d81bb19480c5?auto=format&fit=crop&q=80&w=1000' }}
                            style={styles.cameraImage}
                        />
                        <View style={styles.liveBadge}>
                            <View style={styles.redDot} />
                            <Text style={[styles.liveText, { ...Typography.overline, color: 'white' }]}>
                                {latestImage ? `SITE FEED: ${latestImage.code_id || 'GENERAL'}` : 'REC • NO LIVE FEED'}
                            </Text>
                        </View>
                        <View style={[styles.cameraOverlay, { backgroundColor: 'rgba(0,0,0,0.7)' }]}>
                            <Text style={[styles.cameraCap, { ...Typography.caption, color: 'white' }]}>
                                {latestImage ? `CAPTURED: ${new Date(latestImage.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'OFFLINE'}
                            </Text>
                            <View style={styles.badgeRow}>
                                <Ionicons name="wifi" size={12} color={latestImage ? '#10b981' : '#94a3b8'} />
                                <Text style={[styles.cameraCap, { ...Typography.caption, color: 'white' }]}>{latestImage ? 'STABLE' : 'NO DATA'}</Text>
                            </View>
                        </View>
                    </Card>

                    {/* ── Quick Actions (6 items) ── */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.overline }]}>QUICK ACTIONS</Text>
                    </View>
                    <View style={styles.actionGrid}>
                        {([
                            { label: 'Projects', icon: 'briefcase', route: '/(admin)/projects' },
                            { label: 'DPR', icon: 'file-text', route: '/(admin)/dpr' },
                            { label: 'Attendance', icon: 'users', route: '/(admin)/attendance-view' },
                            { label: 'Funds', icon: 'credit-card', route: '/(admin)/petty-cash' },
                            { label: 'Schedule', icon: 'calendar', route: '/(admin)/scheduler' },
                            { label: 'Settings', icon: 'settings', route: '/(admin)/settings' },
                        ] as const).map((item, idx) => (
                            <QuickAction
                                key={idx}
                                label={item.label}
                                icon={item.icon}
                                route={item.route}
                                colors={Colors}
                                onPress={handleNavigation}
                            />
                        ))}
                    </View>
                </ScrollView>
            </BlueprintGrid>
        </SafeAreaView>
    );
}

// --------------------------------------------------------
// STYLES
// --------------------------------------------------------

const styles = StyleSheet.create({
    scrollContent: { padding: 16, paddingBottom: 100 },

    // Header
    header: { marginBottom: 16 },
    headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
    profileBox: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    avatar: { width: 40, height: 40, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
    avatarText: { color: 'white', fontWeight: '900', fontSize: 17 },
    welcomeText: { fontSize: 9, fontWeight: '800', letterSpacing: 0.5, textTransform: 'uppercase', opacity: 0.8 },
    userName: { fontSize: 17 },
    headerActions: { flexDirection: 'row', gap: 8 },
    iconBtn: { width: 36, height: 36, borderRadius: 8, justifyContent: 'center', alignItems: 'center', borderWidth: 1 },
    projectBar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, paddingTop: 12, borderTopWidth: 1 },
    projectLabel: { fontSize: 9, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 1 },
    projectName: { fontSize: 15, fontFamily: 'Inter_800ExtraBold', marginTop: 2 },
    switchChip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 4 },
    switchText: { fontSize: 10, fontWeight: '900', letterSpacing: 0.5 },

    // KPI Cards
    kpiRow: { flexDirection: 'row', gap: 10, marginBottom: 10 },
    kpiCard: { flex: 1 },
    kpiIconBox: { width: 28, height: 28, borderRadius: 6, justifyContent: 'center', alignItems: 'center', marginBottom: 8 },
    kpiLabel: { fontSize: 8, fontWeight: '800', letterSpacing: 0.5, textTransform: 'uppercase' },
    kpiValue: { fontSize: 20, marginTop: 2, marginBottom: 4 },
    kpiTrend: { flexDirection: 'row', alignItems: 'center', gap: 3 },
    kpiTrendText: { fontSize: 9, fontWeight: '700' },

    // Section headers
    sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10, marginTop: 12 },
    sectionTitle: { fontSize: 10, fontWeight: '900', letterSpacing: 1.5, opacity: 0.6 },

    // Financial overview
    finCard: { marginBottom: 8 },
    finRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    finItem: { flex: 1, alignItems: 'center' },
    finLabel: { fontSize: 9, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 4 },
    finValue: { fontSize: 14, fontFamily: 'Inter_800ExtraBold' },
    finDivider: { width: 1, height: 32, marginHorizontal: 4 },
    budgetBarTrack: { height: 4, borderRadius: 2, overflow: 'hidden', marginTop: 12 },
    budgetBarFill: { height: '100%', borderRadius: 2 },

    // Funds
    fundsRow: { flexDirection: 'row', gap: 10, marginBottom: 8 },
    fundCard: { flex: 1 },
    fundLabel: { fontSize: 8, fontWeight: '800', letterSpacing: 0.5, textTransform: 'uppercase' },
    fundValue: { fontSize: 18, marginTop: 4, marginBottom: 2 },
    fundAlloc: { fontSize: 10, fontWeight: '600' },

    // Progress
    progressCard: { marginBottom: 12 },
    progressItem: { marginBottom: 12 },
    progressHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
    progressLabel: { fontSize: 13, fontFamily: 'Inter_700Bold', flex: 1, marginRight: 8 },
    progressPct: { fontSize: 11, fontWeight: '700' },
    progressTrack: { height: 5, borderRadius: 3, overflow: 'hidden' },
    progressFill: { height: '100%', borderRadius: 3 },

    // Tasks
    taskCard: { marginBottom: 16 },
    taskItem: { marginBottom: 10 },
    taskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
    taskDesc: { flex: 1, marginRight: 8 },
    statusBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4 },
    statusText: { fontSize: 8, fontWeight: '900' },
    taskMeta: { fontSize: 10 },

    // Camera / Site
    cameraFrame: { height: 160, borderRadius: 12, overflow: 'hidden', marginBottom: 16 },
    cameraImage: { width: '100%', height: '100%' },
    liveBadge: { position: 'absolute', top: 10, left: 10, backgroundColor: 'rgba(239, 68, 68, 0.9)', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4, flexDirection: 'row', alignItems: 'center', gap: 5 },
    redDot: { width: 6, height: 6, borderRadius: 3, backgroundColor: 'white' },
    liveText: { color: 'white', fontSize: 9, fontWeight: '900', letterSpacing: 0.5 },
    cameraOverlay: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 28, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 10 },
    cameraCap: { color: 'white', fontSize: 9, fontWeight: '700' },
    badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },

    // Quick Actions (3x2 grid)
    actionGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 40 },
    actionBox: { width: '31%', height: 72, borderRadius: 10, borderWidth: 1, justifyContent: 'center', alignItems: 'center', gap: 6 },
    actionLabel: { fontSize: 10, fontWeight: '800', letterSpacing: 0.3 },

    // Empty state
    emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
    emptyIconCircle: { width: 80, height: 80, borderRadius: 40, alignItems: 'center', justifyContent: 'center', marginBottom: 24 },
    emptyTitle: { fontSize: 20, fontWeight: '900', marginBottom: 12 },
    emptySubtitle: { fontSize: 14, textAlign: 'center', lineHeight: 20, opacity: 0.7 },
});
