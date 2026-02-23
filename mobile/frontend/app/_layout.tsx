// ROOT LAYOUT
// Wraps entire app in AuthContext and ProjectContext providers

import React from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider } from '../contexts/AuthContext';
import { ProjectProvider } from '../contexts/ProjectContext';

export default function RootLayout() {
  return (
    <AuthProvider>
      <ProjectProvider>
        <StatusBar style="light" />
        <Stack
          screenOptions={{
            headerShown: false,
          }}
        >
          <Stack.Screen name="index" />
          <Stack.Screen name="login" />
          <Stack.Screen name="(admin)" />
          <Stack.Screen name="(supervisor)" />
        </Stack>
      </ProjectProvider>
    </AuthProvider>
  );
}
