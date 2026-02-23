// DPR STACK NAVIGATION
// Handles nested DPR screens: create, [id] (details)

import { Stack } from 'expo-router';
import { Colors } from '../../../constants/theme';

export default function DPRLayout() {
  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.background },
      }}
    >
      <Stack.Screen name="create" />
      <Stack.Screen name="[id]" />
    </Stack>
  );
}
