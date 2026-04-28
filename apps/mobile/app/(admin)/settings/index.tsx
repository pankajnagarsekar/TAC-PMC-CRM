// ADMIN SETTINGS SCREEN
// Admin-only settings and configuration

import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Alert, Platform, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../../../contexts/AuthContext';
import { Card } from '../../../components/ui';
import { useTheme, ThemeContextType } from '../../../contexts/ThemeContext';

export default function AdminSettings() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const { colors: Colors, spacing: Spacing, fontSizes: FontSizes, borderRadius: BorderRadius } = useTheme();
  const styles = useMemo(() => getStyles(Colors, Spacing, FontSizes, BorderRadius), [Colors, Spacing, FontSizes, BorderRadius]);

  const handleLogout = () => {
    const onConfirm = async () => {
      setIsLoggingOut(true);
      try {
        await logout();
        router.replace('/login');
      } catch (error) {
        console.error('Logout error:', error);
      } finally {
        setIsLoggingOut(false);
      }
    };

    if (Platform.OS === 'web') {
      if (window.confirm('Are you sure you want to logout?')) {
        onConfirm();
      }
    } else {
      Alert.alert(
        'Logout',
        'Are you sure you want to logout?',
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Logout',
            style: 'destructive',
            onPress: onConfirm
          },
        ]
      );
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScrollView contentContainerStyle={styles.content}>
        {/* User Profile Card */}
        <Card style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {user?.name?.charAt(0).toUpperCase() || 'A'}
            </Text>
          </View>
          <Text style={styles.userName}>{user?.name}</Text>
          <Text style={styles.userEmail}>{user?.email}</Text>
          <View style={styles.roleBadge}>
            <Text style={styles.roleText}>{user?.role}</Text>
          </View>
        </Card>

        {/* Settings Sections */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Work Management</Text>
          <Card padding="none">
            <SettingsItem icon="calendar" title="Scheduler" onPress={() => router.push('/(admin)/scheduler')} Colors={Colors} styles={styles} />
            <SettingsItem icon="checkmark-circle" title="Tasks" onPress={() => router.push('/(admin)/tasks')} Colors={Colors} styles={styles} />
          </Card>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Organization</Text>
          <Card padding="none">
            <SettingsItem icon="people" title="User Management" onPress={() => router.push('/(admin)/settings/users')} Colors={Colors} styles={styles} />
            <SettingsItem icon="business" title="Organization Settings" onPress={() => router.push('/(admin)/settings/organization')} Colors={Colors} styles={styles} />
            <SettingsItem icon="pricetag" title="Activity Codes" onPress={() => router.push('/(admin)/settings/codes')} Colors={Colors} styles={styles} />
          </Card>
        </View>

        {/*
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Preferences</Text>
          <Card padding="none">
            <SettingsItem icon="color-palette" title="Appearance" onPress={() => router.push('/(admin)/settings/appearance')} Colors={Colors} styles={styles} />
          </Card>
        </View>
        */}

        {/* Logout Button */}
        <TouchableOpacity
          style={[styles.logoutButton, isLoggingOut && { opacity: 0.7 }]}
          onPress={handleLogout}
          disabled={isLoggingOut}
        >
          {isLoggingOut ? (
            <ActivityIndicator size="small" color={Colors.error} />
          ) : (
            <>
              <Ionicons name="log-out-outline" size={20} color={Colors.error} />
              <Text style={styles.logoutText}>Logout</Text>
            </>
          )}
        </TouchableOpacity>

        {/* Version Info */}
        <Text style={styles.versionText}>Version 1.0.0</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

function SettingsItem({
  icon,
  title,
  onPress,
  Colors,
  styles
}: {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  onPress: () => void;
  Colors: ThemeContextType['colors'],
  styles: ReturnType<typeof getStyles>
}) {
  return (
    <TouchableOpacity style={styles.settingsItem} onPress={onPress}>
      <Ionicons name={icon} size={22} color={Colors.textSecondary} />
      <Text style={styles.settingsItemText}>{title}</Text>
      <Ionicons name="chevron-forward" size={18} color={Colors.textMuted} />
    </TouchableOpacity>
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
    backgroundColor: Colors.background,
  },
  content: {
    padding: Spacing.md,
  },
  profileCard: {
    alignItems: 'center',
    padding: Spacing.lg,
    marginBottom: Spacing.lg,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: Colors.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  avatarText: {
    fontSize: FontSizes.xxxl,
    fontWeight: 'bold',
    color: Colors.white,
  },
  userName: {
    fontSize: FontSizes.xl,
    fontWeight: '600',
    color: Colors.text,
  },
  userEmail: {
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
    marginTop: Spacing.xs,
  },
  roleBadge: {
    marginTop: Spacing.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.xs,
    backgroundColor: Colors.primaryLight + '20',
    borderRadius: BorderRadius.full,
  },
  roleText: {
    fontSize: FontSizes.sm,
    fontWeight: '500',
    color: Colors.primary,
  },
  section: {
    marginBottom: Spacing.lg,
  },
  sectionTitle: {
    fontSize: FontSizes.sm,
    fontWeight: '600',
    color: Colors.textMuted,
    textTransform: 'uppercase',
    marginBottom: Spacing.sm,
    marginLeft: Spacing.xs,
  },
  settingsItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  settingsItemText: {
    flex: 1,
    fontSize: FontSizes.md,
    color: Colors.text,
    marginLeft: Spacing.md,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: Spacing.md,
    marginTop: Spacing.md,
    gap: Spacing.sm,
  },
  logoutText: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.error,
  },
  versionText: {
    fontSize: FontSizes.sm,
    color: Colors.textMuted,
    textAlign: 'center',
    marginTop: Spacing.md,
  },
});
