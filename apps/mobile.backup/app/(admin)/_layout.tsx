// ADMIN BOTTOM TAB NAVIGATION
// Tabs: Dashboard, DPR, Workers, More

import React, { useEffect } from 'react';
import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';

import { useTheme } from '../../contexts/ThemeContext';

export default function AdminLayout() {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();
  const { colors: Colors, isDark } = useTheme();

  // Redirect to login if not authenticated or not admin
  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace('/login');
      } else if (user?.role !== 'Admin') {
        // Force redirect to supervisor dashboard if they somehow hit this layout
        router.replace('/(supervisor)/dashboard');
      }
    }
  }, [isAuthenticated, isLoading, user, router]);

  // Guard: render nothing while auth is resolving to prevent tab-bar flash
  if (isLoading) return null;


  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: Colors.background,
          borderTopWidth: 1,
          borderTopColor: Colors.border,
          height: 65,
          paddingBottom: 10,
          paddingTop: 8,
          elevation: 0,
        },
        tabBarActiveTintColor: Colors.primary,
        tabBarInactiveTintColor: Colors.textMuted,
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: '800',
          textTransform: 'uppercase',
          letterSpacing: 0.5,
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="grid-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="projects"
        options={{
          title: 'Projects',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="business-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="dpr"
        options={{
          title: 'DPR',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="document-text-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="attendance-view"
        options={{
          title: 'Attendance',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="calendar-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="petty-cash"
        options={{
          title: 'Petty Cash',
          href: null, // Keep null to hide from bottom tab strip, but reachable via push
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'More',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="ellipsis-horizontal-outline" size={size} color={color} />
          ),
        }}
      />
      {/* Hidden screens - accessible but not in tab bar */}
      <Tabs.Screen
        name="select-project"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="worker-log"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="notifications"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="ocr"
        options={{
          title: 'Scanner',
          href: null,
        }}
      />

      <Tabs.Screen
        name="workers-report"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}
