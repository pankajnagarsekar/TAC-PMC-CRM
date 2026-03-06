// CLIENT DASHBOARD (PHASE 7 PARITY)
// Shows project overview based on enabled client permissions
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../../contexts/AuthContext';
import { settingsApi, dashboardApi } from '../../services/apiClient';
import { Colors, Spacing, FontSizes, BorderRadius, Shadows } from '../../constants/theme';

export default function ClientDashboard() {
  const { user } = useAuth();
  const router = useRouter();
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadSettings = useCallback(async () => {
    try {
      const data = await settingsApi.getGlobalSettings();
      setSettings(data);
    } catch (error) {
      console.error('Error loading client settings:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const onRefresh = () => {
    setRefreshing(true);
    loadSettings();
  };

  const permissions = settings?.client_permissions || {
    budget: false,
    commitments: false,
    dpr: false,
    site_images: false,
    issues: false,
    reports: false,
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
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
        <View style={styles.header}>
          <View>
            <Text style={styles.welcome}>Welcome,</Text>
            <Text style={styles.name}>{user?.name}</Text>
          </View>
          <Pressable style={styles.profileBtn}>
            <Ionicons name="person-circle" size={40} color={Colors.white} />
          </Pressable>
        </View>

        {/* Dynamic Permissions Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Project Overview</Text>
          
          <View style={styles.grid}>
            {permissions.budget && (
              <DashboardCard 
                icon="pie-chart" 
                title="Budget" 
                subtitle="Financial overview"
                color={Colors.primary} 
              />
            )}
            {permissions.commitments && (
              <DashboardCard 
                icon="document-attach" 
                title="Commitments" 
                subtitle="Work Orders"
                color={Colors.info} 
              />
            )}
            {permissions.dpr && (
              <DashboardCard 
                icon="document-text" 
                title="DPR" 
                subtitle="Progress Reports"
                color={Colors.success} 
              />
            )}
            {permissions.site_images && (
              <DashboardCard 
                icon="images" 
                title="Photos" 
                subtitle="Site progress"
                color={Colors.accent} 
              />
            )}
            {permissions.issues && (
              <DashboardCard 
                icon="alert-circle" 
                title="Issues" 
                subtitle="Site observations"
                color={Colors.error} 
              />
            )}
            {permissions.reports && (
              <DashboardCard 
                icon="bar-chart" 
                title="Reports" 
                subtitle="Export analytics"
                color={Colors.secondary} 
                onPress={() => router.push('/(client)/reports' as any)}
              />
            )}
          </View>

          {!Object.values(permissions).some(v => v) && (
            <View style={styles.emptyState}>
              <Ionicons name="lock-closed-outline" size={48} color={Colors.textMuted} />
              <Text style={styles.emptyTitle}>Access Restricted</Text>
              <Text style={styles.emptyText}>
                The administrator has not granted any dashboard permissions to clients yet.
              </Text>
            </View>
          )}
        </View>

        <View style={styles.notice}>
          <Ionicons name="information-circle" size={20} color={Colors.warning} />
          <Text style={styles.noticeText}>
            The mobile client portal is currently optimized for quick overview. For full financial depth and PDF exports, please use the Web Portal.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function DashboardCard({ icon, title, subtitle, color, onPress }: any) {
  return (
    <Pressable style={styles.card} onPress={onPress}>
      <View style={[styles.cardIcon, { backgroundColor: color + '15' }]}>
        <Ionicons name={icon} size={24} color={color} />
      </View>
      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.cardSubtitle}>{subtitle}</Text>
    </Pressable>
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
  },
  scrollContent: {
    paddingBottom: 40,
  },
  header: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.xl,
    backgroundColor: Colors.headerBg,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderBottomLeftRadius: BorderRadius.xl,
    borderBottomRightRadius: BorderRadius.xl,
    ...Shadows.md,
  },
  welcome: {
    color: Colors.textMuted,
    fontSize: FontSizes.sm,
    fontFamily: 'Inter_400Regular',
  },
  name: {
    color: Colors.white,
    fontSize: FontSizes.xxl,
    fontWeight: 'bold',
    fontFamily: 'Inter_700Bold',
  },
  profileBtn: {
    opacity: 0.8,
  },
  section: {
    padding: Spacing.lg,
  },
  sectionTitle: {
    fontSize: FontSizes.sm,
    fontWeight: '700',
    color: Colors.textSecondary,
    textTransform: 'uppercase',
    marginBottom: Spacing.md,
    letterSpacing: 0.5,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.md,
  },
  card: {
    width: '47%',
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.lg,
    padding: Spacing.md,
    ...Shadows.sm,
  },
  cardIcon: {
    width: 44,
    height: 44,
    borderRadius: BorderRadius.md,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.sm,
  },
  cardTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  cardSubtitle: {
    fontSize: FontSizes.xs,
    color: Colors.textMuted,
    marginTop: 2,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
    backgroundColor: Colors.white,
    borderRadius: BorderRadius.xl,
    marginTop: Spacing.md,
  },
  emptyTitle: {
    fontSize: FontSizes.lg,
    fontWeight: '600',
    color: Colors.text,
    marginTop: Spacing.md,
  },
  emptyText: {
    fontSize: FontSizes.sm,
    color: Colors.textMuted,
    textAlign: 'center',
    paddingHorizontal: Spacing.xl,
    marginTop: 8,
  },
  notice: {
    margin: Spacing.lg,
    padding: Spacing.md,
    backgroundColor: Colors.warningLight,
    borderRadius: BorderRadius.md,
    flexDirection: 'row',
    gap: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.warning + '30',
  },
  noticeText: {
    color: Colors.warning,
    fontSize: FontSizes.xs,
    flex: 1,
    lineHeight: 18,
  },
});
