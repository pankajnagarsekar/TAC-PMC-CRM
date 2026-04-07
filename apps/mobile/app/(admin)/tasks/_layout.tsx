import { Stack } from 'expo-router';
import { useTheme } from '../../../contexts/ThemeContext';

export default function TasksLayout() {
  const { colors: Colors } = useTheme();

  return (
    <Stack
      screenOptions={{
        headerStyle: {
          backgroundColor: Colors.background,
        },
        headerTintColor: Colors.text,
        headerTitleStyle: {
          fontFamily: 'Inter_700Bold',
        },
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen
        name="index"
        options={{
          title: 'Project Tasks',
        }}
      />
      <Stack.Screen
        name="[id]"
        options={{
          title: 'Task Details',
        }}
      />
    </Stack>
  );
}
