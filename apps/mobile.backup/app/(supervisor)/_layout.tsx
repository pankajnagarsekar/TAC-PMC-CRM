// SUPERVISOR BOTTOM TAB NAVIGATION
// Tabs: Dashboard, Attendance, DPR, Profile

import React, { useEffect } from 'react';
import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../contexts/AuthContext';

const TAB_BAR_BG = '#1E3A5F';
const ACTIVE_TAB = '#F97316';
const INACTIVE_TAB = '#9CA3AF';

export default function SupervisorLayout() {
  const router = useRouter();
  const { isAuthenticated, isLoading, user } = useAuth();

  // Redirect to login if not authenticated, or to home if wrong role
  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        router.replace('/login');
      } else if (user?.role !== 'Supervisor') {
        // Non-supervisors get routed back to the role-aware index
        router.replace('/');
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
          backgroundColor: TAB_BAR_BG,
          borderTopWidth: 0,
          height: 60,
          paddingBottom: 8,
          paddingTop: 8,
        },
        tabBarActiveTintColor: ACTIVE_TAB,
        tabBarInactiveTintColor: INACTIVE_TAB,
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '500',
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="home-outline" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="attendance"
        options={{
          title: 'Attendance',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="finger-print-outline" size={size} color={color} />
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
        name="profile"
        options={{
          title: 'Profile',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person-outline" size={size} color={color} />
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
        name="voice-log"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}
