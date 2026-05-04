// ADMIN BOTTOM TAB NAVIGATION
// Tabs: Dashboard, Projects, Tasks, DPR, Attendance, More

import React, { useEffect } from 'react';
import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';

import { useTheme } from '../../contexts/ThemeContext';

import { useSafeAreaInsets } from 'react-native-safe-area-context';

export default function AdminLayout() {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();
  const { colors: Colors } = useTheme();
  const insets = useSafeAreaInsets();

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
          height: 75 + (insets.bottom > 0 ? insets.bottom - 10 : 0),
          paddingBottom: insets.bottom > 0 ? insets.bottom : 12,
          paddingTop: 12,
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
        name="tasks"
        options={{
          title: 'Tasks',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="checkmark-circle-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="scheduler"
        options={{
          title: 'Schedule',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="calendar-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="petty-cash"
        options={{
          title: 'Budget',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="wallet-outline" size={size} color={color} />
          ),
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
      <Tabs.Screen
        name="projects"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="dpr"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="attendance-view"
        options={{
          href: null,
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
        name="attendance"
        options={{
          href: null,
        }}
      />

      <Tabs.Screen
        name="workers-report"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="analytics"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="tasks/index"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="tasks/new"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="tasks/[id]"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="scheduler/index"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="scheduler/task/[taskId]"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}
