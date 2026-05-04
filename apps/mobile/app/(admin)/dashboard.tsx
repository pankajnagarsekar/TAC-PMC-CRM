import React, { useState, useEffect, useCallback } from 'react';
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
import api from '../../services/apiClient';
import { Button, Card, BlueprintGrid, LoadingScreen } from '../../components/ui';
import { DerivedFinancialState, AdminDashboardData, Image as ProjectImage } from '../../types/api';

// Removed width Dimensions get

const formatCurrency = (amount: number): string => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}K`;
    return `₹${amount.toFixed(0)}`;
};

export default function ProjectDashboard() {
    const router = useRouter();
    const { selectedProject } = useProject();
    const { colors: Colors, spacing: Spacing, isDark, toggleTheme } = useTheme();
    const { user } = useAuth();

    const [financials, setFinancials] = useState<DerivedFinancialState[]>([]);
    const [stats, setStats] = useState<AdminDashboardData | null>(null);
    const [latestImage, setLatestImage] = useState<ProjectImage | null>(null);
    const [refreshing, setRefreshing] = useState(false);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        if (!selectedProject?.project_id) {
            setRefreshing(false);
            setLoading(false);
            return;
        }

        try {
            const [finData, statsData, imageData] = await Promise.all([
                api.financial.getProjectFinancials(selectedProject.project_id),
                api.dashboard.getProjectDashboard(selectedProject.project_id),
                api.images.getAll(selectedProject.project_id)
            ]);
            
            setFinancials(finData || []);
            setStats(statsData || null);
            if (imageData && imageData.length > 0) {
                setLatestImage(imageData[0]);
            }
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
                    <Text style={[styles.emptyTitle, { color: Colors.text }]}>No Project Selected</Text>
                    <Text style={[styles.emptySubtitle, { color: Colors.textMuted }]}>
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
                    {/* Floating Header */}
                    <Card variant="elevated" style={styles.header} padding="md">
                        <View style={styles.headerRow}>
                            <View style={styles.profileBox}>
                                <View style={[styles.avatar, { backgroundColor: Colors.primary }]}>
                                    <Text style={styles.avatarText}>{user?.name?.[0]?.toUpperCase() || 'A'}</Text>
                                </View>
                                <View>
                                    <Text style={[styles.welcomeText, { color: Colors.textSecondary }]}>TAC PMC CRM</Text>
                                    <Text style={[styles.userName, { color: Colors.text, fontFamily: 'Inter_900Black' }]}>{user?.name || 'Administrator'}</Text>
                                </View>
                            </View>
                            <Pressable onPress={toggleTheme} style={[styles.themeToggle, { borderColor: Colors.border }]}>
                                <Feather name={isDark ? "sun" : "moon"} size={20} color={Colors.text} />
                            </Pressable>
                        </View>

                        <View style={[styles.projectSelectorBox, { borderTopColor: Colors.border }]}>
                            <View style={{ flex: 1 }}>
                                <Text style={[styles.projectLabel, { color: Colors.textSecondary }]}>ACTIVE SITE</Text>
                                <Text style={[styles.projectNameDisplay, { color: Colors.text }]} numberOfLines={1}>{selectedProject.project_name}</Text>
                            </View>
                            <Pressable
                                style={[styles.switchChip, { backgroundColor: Colors.primary }]}
                                onPress={() => router.push('/(admin)/projects')}
                            >
                                <Text style={[styles.switchText, { color: Colors.textInverse }]}>SWITCH SITE</Text>
                            </Pressable>
                        </View>
                    </Card>

                    {/* KPI Overview */}
                    <View style={styles.summaryRow}>
                        <Card variant="elevated" style={styles.summaryCard} padding="md">
                            <Text style={[styles.cardLabel, { color: Colors.textSecondary }]}>PORTFOLIO VALUE</Text>
                            <Text style={[styles.cardValue, { color: Colors.text, fontFamily: 'Inter_900Black' }]}>
                                {formatCurrency(stats?.financials?.total_budget || 0)}
                            </Text>
                            <View style={styles.cardTrend}>
                                <Ionicons 
                                    name={Number(stats?.indicators?.spi || 0) >= 1 ? "trending-up" : "trending-down"} 
                                    size={14} 
                                    color={Number(stats?.indicators?.spi || 0) >= 1 ? "#10b981" : "#ef4444"} 
                                />
                                <Text style={[styles.trendText, { color: Number(stats?.indicators?.spi || 0) >= 1 ? "#10b981" : "#ef4444" }]}>
                                    SPI: {stats?.indicators?.spi?.toFixed(2) || '1.00'}
                                </Text>
                            </View>
                        </Card>
                        <Card variant="elevated" style={styles.summaryCard} padding="md">
                            <Text style={[styles.cardLabel, { color: Colors.textSecondary }]}>ACTIVE TASKS</Text>
                            <Text style={[styles.cardValue, { color: Colors.text, fontFamily: 'Inter_900Black' }]}>
                                {String(stats?.active_tasks || 0).padStart(2, '0')}
                            </Text>
                            <View style={[styles.statusChip, { backgroundColor: (stats?.overdue_tasks || 0) > 0 ? (isDark ? '#3d1a1a' : '#fee2e2') : (isDark ? '#1a2e26' : '#ecfdf5') }]}>
                                <Text style={[styles.statusText, { color: (stats?.overdue_tasks || 0) > 0 ? '#ef4444' : '#10b981' }]}>
                                    {(stats?.overdue_tasks || 0) > 0 ? `${stats?.overdue_tasks} OVERDUE` : 'HEALTHY'}
                                </Text>
                            </View>
                        </Card>
                    </View>

                    {/* Site Intelligence Feed */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text }]}>SITE INTELLIGENCE</Text>
                        <Pressable><Text style={{ color: Colors.primary, fontSize: 13, fontFamily: 'Inter_700Bold' }}>LIVE VIEW</Text></Pressable>
                    </View>

                    <Card variant="elevated" style={styles.cameraFrame} padding="none">
                        <Image
                            source={{ uri: latestImage ? `data:image/jpeg;base64,${latestImage.image_base64}` : 'https://images.unsplash.com/photo-1541888946425-d81bb19480c5?auto=format&fit=crop&q=80&w=1000' }}
                            style={styles.cameraImage}
                        />
                        <View style={styles.liveBadge}>
                            <View style={styles.redDot} />
                            <Text style={styles.liveText}>
                                {latestImage ? `SITE FEED: ${latestImage.code_id || 'GENERAL'}` : 'REC • NO LIVE FEED'}
                            </Text>
                        </View>
                        <View style={[styles.cameraOverlayBar, { backgroundColor: 'rgba(0,0,0,0.7)' }]}>
                            <Text style={styles.cameraCap}>
                                {latestImage ? `CAPTURED: ${new Date(latestImage.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` : 'OFFLINE'}
                            </Text>
                            <View style={styles.badgeRow}>
                                <Ionicons name="wifi" size={12} color={latestImage ? "#10b981" : "#94a3b8"} />
                                <Text style={styles.cameraCap}>{latestImage ? 'STABLE' : 'NO DATA'}</Text>
                            </View>
                        </View>
                    </Card>

                    {/* Construction Schedule */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text }]}>CONSTRUCTION PROGRESS</Text>
                    </View>
                    <Card variant="elevated" style={styles.scheduleCard} padding="md">
                        {financials.length > 0 ? financials.slice(0, 3).map((item, idx) => {
                            const progress = item.original_budget > 0 
                                ? Math.min(100, Math.round((Number(item.certified_value || 0) / Number(item.original_budget)) * 100))
                                : 0;
                            return (
                                <View key={idx} style={[styles.scheduleItem, idx > 0 && { marginTop: 16 }]}>
                                    <View style={styles.scheduleHeader}>
                                        <Text style={[styles.scheduleLabel, { color: Colors.text }]} numberOfLines={1}>
                                            {item.category_name || item.category_id}
                                        </Text>
                                        <Text style={[styles.scheduleValue, { color: Colors.textSecondary }]}>{progress}%</Text>
                                    </View>
                                    <View style={[styles.progressTrack, { backgroundColor: Colors.border }]}>
                                        <View style={[styles.progressFill, { width: `${Math.max(2, progress)}%`, backgroundColor: progress >= 100 ? '#10b981' : Colors.primary }]} />
                                    </View>
                                </View>
                            );
                        }) : (
                            <Text style={{ color: Colors.textSecondary, fontSize: 12, textAlign: 'center', fontStyle: 'italic' }}>
                                No financial absorption data available.
                            </Text>
                        )}
                    </Card>

                    {/* Shortcut Matrix */}
                    <View style={styles.shortcutGrid}>
                        {(
                            [
                                { label: 'FUNDS', icon: 'credit-card', route: '/(admin)/petty-cash' },
                                { label: 'DPR', icon: 'file-text', route: '/(admin)/dpr' },
                                { label: 'TASKS', icon: 'check-square', route: '/(admin)/tasks' },
                                { label: 'MORE', icon: 'grid', route: '/(admin)/settings' }
                            ] as const
                        ).map((item, idx) => (
                            <Pressable
                                key={idx}
                                style={[styles.shortcutBox, { backgroundColor: Colors.surface, borderColor: Colors.border }]}
                                onPress={() => router.push(item.route as any)}
                            >
                                <Feather name={item.icon} size={22} color={Colors.primary} />
                                <Text style={[styles.shortcutText, { color: Colors.text }]}>{item.label}</Text>
                            </Pressable>
                        ))}
                    </View>
                </ScrollView>
            </BlueprintGrid>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    scrollContent: { padding: 16, paddingBottom: 100 },
    header: { marginBottom: 20 },
    headerRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
    profileBox: { flexDirection: 'row', alignItems: 'center', gap: 12 },
    avatar: { width: 44, height: 44, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
    avatarText: { color: 'white', fontWeight: '900', fontSize: 18 },
    welcomeText: { fontSize: 10, fontWeight: '700', letterSpacing: 0.5, textTransform: 'uppercase', opacity: 0.8 },
    userName: { fontSize: 18 },
    themeToggle: { width: 40, height: 40, borderRadius: 8, justifyContent: 'center', alignItems: 'center', borderWidth: 1 },
    projectSelectorBox: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, paddingTop: 16, borderTopWidth: 1 },
    projectLabel: { fontSize: 9, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 1 },
    projectNameDisplay: { fontSize: 16, fontFamily: 'Inter_800ExtraBold', marginTop: 2 },
    switchChip: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 4 },
    switchText: { fontSize: 10, fontWeight: '900', letterSpacing: 0.5 },

    summaryRow: { flexDirection: 'row', gap: 10, marginBottom: 20 },
    summaryCard: { flex: 1, padding: 12 },
    cardLabel: { fontSize: 8, fontWeight: '800', letterSpacing: 0.5 },
    cardValue: { fontSize: 20, marginVertical: 4 },
    cardTrend: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    trendText: { fontSize: 11, fontWeight: '700' },
    statusChip: { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4, marginTop: 8 },
    statusText: { fontSize: 9, fontWeight: '900' },

    sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, marginTop: 4 },
    sectionTitle: { fontSize: 11, fontWeight: '900', letterSpacing: 1.5, opacity: 0.6 },

    cameraFrame: { height: 180, borderRadius: 12, overflow: 'hidden', marginBottom: 24 },
    cameraImage: { width: '100%', height: '100%' },
    liveBadge: { position: 'absolute', top: 12, left: 12, backgroundColor: 'rgba(239, 68, 68, 0.9)', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 4, flexDirection: 'row', alignItems: 'center', gap: 6 },
    redDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: 'white' },
    liveText: { color: 'white', fontSize: 10, fontWeight: '900', letterSpacing: 0.5 },
    cameraOverlayBar: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 32, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12 },
    cameraCap: { color: 'white', fontSize: 9, fontWeight: '700' },
    badgeRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },

    scheduleCard: { marginBottom: 24 },
    scheduleItem: { width: '100%' },
    scheduleHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
    scheduleLabel: { fontSize: 13, fontFamily: 'Inter_700Bold' },
    scheduleValue: { fontSize: 11, fontWeight: '700' },
    progressTrack: { height: 6, borderRadius: 3, overflow: 'hidden' },
    progressFill: { height: '100%' },

    shortcutGrid: { flexDirection: 'row', gap: 12, marginBottom: 40 },
    shortcutBox: { flex: 1, height: 80, borderRadius: 12, borderWidth: 1, justifyContent: 'center', alignItems: 'center', gap: 8 },
    shortcutText: { fontSize: 10, fontWeight: '900', letterSpacing: 0.5 },

    emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 40 },
    emptyIconCircle: { width: 80, height: 80, borderRadius: 40, alignItems: 'center', justifyContent: 'center', marginBottom: 24 },
    emptyTitle: { fontSize: 20, fontWeight: '900', marginBottom: 12 },
    emptySubtitle: { fontSize: 14, textAlign: 'center', lineHeight: 20, opacity: 0.7 },
});
