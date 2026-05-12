import React, { useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    TouchableOpacity,
    TextInput,
    ActivityIndicator,
    Alert,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useProject } from '../../../contexts/ProjectContext';
import { useTheme } from '../../../contexts/ThemeContext';
import { tasksApi } from '../../../services/apiClient';
import { Card } from '../../../components/ui';

export default function NewTaskScreen() {
    const router = useRouter();
    const { selectedProject } = useProject();
    const { colors: Colors } = useTheme();

    const [title, setTitle] = useState('');
    const [description, setDescription] = useState('');
    const [priority, setPriority] = useState<'High' | 'Medium' | 'Low'>('Medium');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async () => {
        if (!title.trim() || !selectedProject) return;

        setIsSubmitting(true);
        try {
            await tasksApi.create(selectedProject.project_id, {
                task_description: title.trim(),
                notes: description.trim(),
                priority,
                project_id: selectedProject.project_id,
                assigned_to_name: 'Unassigned',
            });

            Alert.alert('Success', 'Task created successfully');
            router.back();
        } catch (error: unknown) {
            console.error('Error creating task:', error);
            const msg = error instanceof Error ? error.message : 'Failed to create task';
            Alert.alert('Error', msg);
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!selectedProject) {
        return (
            <SafeAreaView style={{ flex: 1, backgroundColor: Colors.background }}>
                <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 20 }}>
                    <Text style={{ color: Colors.text, fontSize: 16 }}>Please select a project first</Text>
                    <TouchableOpacity
                        onPress={() => router.replace('/(admin)/projects')}
                        style={{ marginTop: 20, padding: 12, backgroundColor: Colors.primary, borderRadius: 8 }}
                    >
                        <Text style={{ color: 'white' }}>Go to Projects</Text>
                    </TouchableOpacity>
                </View>
            </SafeAreaView>
        );
    }

    return (
        <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]} edges={['left', 'right']}>
            <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                        <Ionicons name="arrow-back" size={24} color={Colors.text} />
                    </TouchableOpacity>
                    <Text style={[styles.headerTitle, { color: Colors.text }]}>Create Task</Text>
                </View>

                <ScrollView contentContainerStyle={styles.content}>
                    <Card style={styles.formCard}>
                        <Text style={[styles.label, { color: Colors.textSecondary }]}>Task Title</Text>
                        <TextInput
                            style={[styles.input, { borderColor: Colors.border, color: Colors.text }]}
                            value={title}
                            onChangeText={setTitle}
                            placeholder="What needs to be done?"
                            placeholderTextColor={Colors.textMuted}
                        />

                        <Text style={[styles.label, { color: Colors.textSecondary, marginTop: 20 }]}>Description</Text>
                        <TextInput
                            style={[styles.input, styles.textArea, { borderColor: Colors.border, color: Colors.text }]}
                            value={description}
                            onChangeText={setDescription}
                            placeholder="Add more details..."
                            placeholderTextColor={Colors.textMuted}
                            multiline
                            numberOfLines={4}
                            textAlignVertical="top"
                        />

                        <Text style={[styles.label, { color: Colors.textSecondary, marginTop: 20 }]}>Priority</Text>
                        <View style={styles.priorityRow}>
                            {(['Low', 'Medium', 'High'] as const).map((p) => (
                                <TouchableOpacity
                                    key={p}
                                    style={[
                                        styles.priorityBtn,
                                        { borderColor: Colors.border },
                                        priority === p && { backgroundColor: Colors.primary, borderColor: Colors.primary }
                                    ]}
                                    onPress={() => setPriority(p)}
                                >
                                    <Text style={[styles.priorityText, { color: Colors.text }, priority === p && { color: 'white' }]}>{p}</Text>
                                </TouchableOpacity>
                            ))}
                        </View>
                    </Card>
                </ScrollView>

                <View style={styles.footer}>
                    <TouchableOpacity
                        style={[styles.submitBtn, { backgroundColor: Colors.primary }, (!title.trim() || isSubmitting) && { opacity: 0.6 }]}
                        onPress={handleSubmit}
                        disabled={!title.trim() || isSubmitting}
                    >
                        {isSubmitting ? (
                            <ActivityIndicator color="white" />
                        ) : (
                            <Text style={styles.submitBtnText}>Create Task</Text>
                        )}
                    </TouchableOpacity>
                </View>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1 },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: 'rgba(0,0,0,0.05)',
    },
    backBtn: { padding: 4, marginRight: 12 },
    headerTitle: { fontSize: 20, fontWeight: '700' },
    content: { padding: 16 },
    formCard: { padding: 16 },
    label: { fontSize: 12, fontWeight: '600', textTransform: 'uppercase', marginBottom: 8 },
    input: {
        borderWidth: 1,
        borderRadius: 8,
        padding: 12,
        fontSize: 16,
    },
    textArea: { height: 100 },
    priorityRow: { flexDirection: 'row', gap: 10 },
    priorityBtn: {
        flex: 1,
        paddingVertical: 10,
        borderWidth: 1,
        borderRadius: 8,
        alignItems: 'center',
    },
    priorityText: { fontWeight: '600' },
    footer: { padding: 16, borderTopWidth: 1, borderTopColor: 'rgba(0,0,0,0.05)' },
    submitBtn: {
        paddingVertical: 14,
        borderRadius: 12,
        alignItems: 'center',
        justifyContent: 'center',
    },
    submitBtnText: { color: 'white', fontSize: 16, fontWeight: '700' },
});
