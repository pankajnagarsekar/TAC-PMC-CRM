// SETTINGS STACK NAVIGATION
// Handles nested settings screens

import { Stack } from 'expo-router';
import { Colors } from '../../../constants/theme';

export default function SettingsLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.background },
      }}
    >
      <Stack.Screen name="index" />
      <Stack.Screen name="notifications" />
      <Stack.Screen name="help" />
      <Stack.Screen name="users" />
      <Stack.Screen name="codes" />
      <Stack.Screen name="organization" />
      <Stack.Screen name="terms" />
      <Stack.Screen name="currency" />
      <Stack.Screen name="privacy" />
      <Stack.Screen name="appearance" />
    </Stack>
  );
}
