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
    Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons, MaterialCommunityIcons, FontAwesome5, Feather } from '@expo/vector-icons';
import { useProject } from '../../contexts/ProjectContext';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import api from '../../services/apiClient';
import { Button, Card, BlueprintGrid } from '../../components/ui';
import { DerivedFinancialState } from '../../types/api';

const { width } = Dimensions.get('window');

const formatCurrency = (amount: number): string => {
    if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(2)}Cr`;
    if (amount >= 100000) return `₹${(amount / 100000).toFixed(2)}L`;
    if (amount >= 1000) return `₹${(amount / 1000).toFixed(1)}K`;
    return `₹${amount.toLocaleString('en-IN')}`;
};

export default function ProjectDashboard() {
    const router = useRouter();
    const { selectedProject } = useProject();
    const { colors: Colors, spacing: Spacing, isDark, toggleTheme } = useTheme();
    const { user } = useAuth();

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

    const totalBudget = useMemo(() => financials.reduce((sum, f) => sum + (f.original_budget || 0), 0), [financials]);

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
                        style={{ marginTop: Spacing.xl } as any}
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
                            <Text style={[styles.cardValue, { color: Colors.text, fontFamily: 'Inter_900Black' }]}>{formatCurrency(totalBudget)}</Text>
                            <View style={styles.cardTrend}>
                                <Ionicons name="trending-up" size={14} color="#10b981" />
                                <Text style={[styles.trendText, { color: '#10b981' }]}>+12% YoY</Text>
                            </View>
                        </Card>
                        <Card variant="elevated" style={styles.summaryCard} padding="md">
                            <Text style={[styles.cardLabel, { color: Colors.textSecondary }]}>ACTIVE PHASES</Text>
                            <Text style={[styles.cardValue, { color: Colors.text, fontFamily: 'Inter_900Black' }]}>04</Text>
                            <View style={[styles.statusChip, { backgroundColor: isDark ? '#1a2e26' : '#ecfdf5' }]}>
                                <Text style={[styles.statusText, { color: '#10b981' }]}>HEALTHY</Text>
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
                            source={{ uri: 'https://images.unsplash.com/photo-1541888946425-d81bb19480c5?auto=format&fit=crop&q=80&w=1000' }}
                            style={styles.cameraImage}
                        />
                        <View style={styles.liveBadge}>
                            <View style={styles.redDot} />
                            <Text style={styles.liveText}>REC • SITE ALPHA-9</Text>
                        </View>
                        <View style={[styles.cameraOverlayBar, { backgroundColor: 'rgba(0,0,0,0.7)' }]}>
                            <Text style={styles.cameraCap}>LAST SYNC: 10:42 AM</Text>
                            <View style={styles.badgeRow}>
                                <Ionicons name="wifi" size={12} color="#10b981" />
                                <Text style={styles.cameraCap}>STABLE</Text>
                            </View>
                        </View>
                    </Card>

                    {/* Construction Schedule */}
                    <View style={styles.sectionHeader}>
                        <Text style={[styles.sectionTitle, { color: Colors.text }]}>CONSTRUCTION PROGRESS</Text>
                    </View>
                    <Card variant="elevated" style={styles.scheduleCard} padding="md">
                        {[
                            { label: 'Foundations', progress: 100, color: '#10b981' },
                            { label: 'Structural Steel', progress: 64, color: Colors.text },
                            { label: 'Enclosure', progress: 12, color: Colors.primary },
                        ].map((item, idx) => (
                            <View key={idx} style={[styles.scheduleItem, idx > 0 && { marginTop: 16 }]}>
                                <View style={styles.scheduleHeader}>
                                    <Text style={[styles.scheduleLabel, { color: Colors.text }]}>{item.label}</Text>
                                    <Text style={[styles.scheduleValue, { color: Colors.textSecondary }]}>{item.progress}%</Text>
                                </View>
                                <View style={[styles.progressTrack, { backgroundColor: Colors.border }]}>
                                    <View style={[styles.progressFill, { width: `${item.progress}%`, backgroundColor: item.color }]} />
                                </View>
                            </View>
                        ))}
                    </Card>

                    {/* Shortcut Matrix */}
                    <View style={styles.shortcutGrid}>
                        {[
                            { label: 'FUNDS', icon: 'wallet', route: '/(admin)/petty-cash' },
                            { label: 'DPR', icon: 'file-text', route: '/(admin)/dpr' },
                            { label: 'WORKERS', icon: 'users', route: '/(admin)/worker-log' },
                            { label: 'MORE', icon: 'grid', route: '/(admin)/settings' }
                        ].map((item, idx) => (
                            <Pressable
                                key={idx}
                                style={[styles.shortcutBox, { backgroundColor: Colors.surface, borderColor: Colors.border }]}
                                onPress={() => router.push(item.route as any)}
                            >
                                <Feather name={item.icon as any} size={22} color={Colors.primary} />
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

    summaryRow: { flexDirection: 'row', gap: 12, marginBottom: 24 },
    summaryCard: { flex: 1 },
    cardLabel: { fontSize: 9, fontWeight: '800', letterSpacing: 1 },
    cardValue: { fontSize: 24, marginVertical: 4 },
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
