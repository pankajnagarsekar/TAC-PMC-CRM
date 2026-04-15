import { Stack } from 'expo-router';
import { useTheme } from '../../../contexts/ThemeContext';

export default function SchedulerLayout() {
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
                    headerShown: false, // Scheduler has its own custom header
                }}
            />
            <Stack.Screen
                name="task/[taskId]"
                options={{
                    title: 'Task Details',
                }}
            />
        </Stack>
    );
}
