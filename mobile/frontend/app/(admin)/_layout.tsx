// ADMIN BOTTOM TAB NAVIGATION
// Tabs: Dashboard, DPR, Workers, More

import React, { useEffect } from 'react';
import { Tabs, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import * as SecureStore from 'expo-secure-store';
import { useAuth } from '../../contexts/AuthContext';
import { useProject } from '../../contexts/ProjectContext';

const TAB_BAR_BG = '#1E3A5F';
const ACTIVE_TAB = '#F97316';
const INACTIVE_TAB = '#9CA3AF';

export default function AdminLayout() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  // Redirect to login if no token
  useEffect(() => {
    const checkAuth = async () => {
      if (isLoading) return;
      
      try {
        const token = await SecureStore.getItemAsync('auth_token');
        if (!token && !isAuthenticated) {
          router.replace('/login');
        }
      } catch (error) {
        // SecureStore not available (web), rely on AuthContext
        if (!isAuthenticated) {
          router.replace('/login');
        }
      }
    };
    
    checkAuth();
  }, [isAuthenticated, isLoading]);

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
            <Ionicons name="grid-outline" size={size} color={color} />
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
        name="workers-report"
        options={{
          title: 'Workers',
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="people-outline" size={size} color={color} />
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
      {/* Hidden screens - accessible but not in tab bar */}
      <Tabs.Screen
        name="notifications"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="ocr"
        options={{
          href: null,
        }}
      />
      <Tabs.Screen
        name="petty-cash"
        options={{
          href: null,
        }}
      />
    </Tabs>
  );
}
