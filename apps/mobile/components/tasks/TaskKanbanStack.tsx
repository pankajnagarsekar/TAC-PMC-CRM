import React from 'react';
import { View, Text, StyleSheet, ScrollView, Dimensions } from 'react-native';
import { Task } from '../../types/api';
import { useTheme } from '../../contexts/ThemeContext';
import { Card, Badge } from '../ui';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

const { width } = Dimensions.get('window');
const COLUMN_WIDTH = width * 0.85;

interface TaskKanbanStackProps {
    tasks: Task[];
}

export default function TaskKanbanStack({ tasks }: TaskKanbanStackProps) {
    const { colors: Colors } = useTheme();
    const router = useRouter();
    const statuses = ["Open", "In Progress", "Review", "Completed", "Closed"];

    const getPriorityColor = (priority: string) => {
        switch (priority.toLowerCase()) {
            case 'high': return '#ef4444';
            case 'normal': return '#3b82f6';
            case 'low': return '#10b981';
            default: return Colors.textMuted;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status.toLowerCase()) {
            case 'open': return '#3b82f6';
            case 'in progress': return '#f59e0b';
            case 'review': return '#fbbf24';
            case 'completed': return '#10b981';
            case 'closed': return Colors.textSecondary;
            default: return Colors.textMuted;
        }
    };

    return (
        <ScrollView
            horizontal
            pagingEnabled
            snapToAlignment="center"
            snapToInterval={COLUMN_WIDTH + 16}
            decelerationRate="fast"
            contentContainerStyle={styles.scrollContent}
            showsHorizontalScrollIndicator={false}
        >
            {statuses.map((status) => {
                const filteredTasks = tasks.filter(t => t.status === status);
                return (
                    <View key={status} style={[styles.column, { backgroundColor: Colors.cardBg, borderColor: Colors.border }]}>
                        <View style={[styles.columnHeader, { borderBottomColor: Colors.border }]}>
                            <View style={styles.headerTitle}>
                                <View style={[styles.statusDot, { backgroundColor: getStatusColor(status) }]} />
                                <Text style={[styles.statusText, { color: Colors.text }]}>{status.toUpperCase()}</Text>
                            </View>
                            <Badge label={filteredTasks.length.toString()} variant="solid" />
                        </View>

                        <ScrollView style={styles.taskList} showsVerticalScrollIndicator={false}>
                            {filteredTasks.length > 0 ? (
                                filteredTasks.map((item) => (
                                    <Card
                                        key={item.id || item._id}
                                        variant="elevated"
                                        style={styles.taskCard}
                                        onPress={() => router.push(`/(admin)/tasks/${item.id || item._id}` as any)}
                                        padding="md"
                                    >
                                        <View style={styles.taskHeader}>
                                            <Text style={[styles.taskSrNo, { color: Colors.textSecondary }]}>#{item.sr_no}</Text>
                                            <Badge
                                                label={item.priority}
                                                color={getPriorityColor(item.priority)}
                                                variant="outline"
                                            />
                                        </View>
                                        <Text style={[styles.taskDescription, { color: Colors.text }]} numberOfLines={2}>
                                            {item.task_description}
                                        </Text>
                                        <View style={styles.taskFooter}>
                                            <View style={styles.assigneeBox}>
                                                <Ionicons name="person-outline" size={12} color={Colors.textSecondary} />
                                                <Text style={[styles.assigneeName, { color: Colors.textSecondary }]}>
                                                    {item.assigned_to_name}
                                                </Text>
                                            </View>
                                        </View>
                                    </Card>
                                ))
                            ) : (
                                <View style={styles.emptyColumn}>
                                    <Text style={{ color: Colors.textMuted }}>No tasks in {status}</Text>
                                </View>
                            )}
                        </ScrollView>
                    </View>
                );
            })}
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    scrollContent: {
        paddingHorizontal: 16,
        paddingBottom: 20,
        gap: 16,
    },
    column: {
        width: COLUMN_WIDTH,
        borderRadius: 16,
        borderWidth: 1,
        overflow: 'hidden',
        height: '100%',
    },
    columnHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
    },
    headerTitle: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
    },
    statusDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
    },
    statusText: {
        fontSize: 14,
        fontWeight: '800',
        letterSpacing: 1,
    },
    taskList: {
        padding: 12,
    },
    taskCard: {
        marginBottom: 12,
    },
    taskHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    taskSrNo: {
        fontSize: 12,
        fontWeight: '700',
    },
    taskDescription: {
        fontSize: 14,
        fontWeight: '600',
        marginBottom: 12,
    },
    taskFooter: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    assigneeBox: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    assigneeName: {
        fontSize: 12,
    },
    emptyColumn: {
        padding: 40,
        alignItems: 'center',
        justifyContent: 'center',
        opacity: 0.5,
    },
});
