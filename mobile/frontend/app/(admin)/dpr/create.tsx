// ADMIN DPR CREATE SCREEN
// Uses shared DPRForm component with project picker

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  Platform,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';
import { projectsApi } from '../../../services/apiClient';
import DPRForm from '../../../components/DPRForm';
import { Card } from '../../../components/ui';
import { Colors, Spacing, FontSizes, BorderRadius } from '../../../constants/theme';

interface Project {
  project_id?: string;
  _id?: string;
  project_name: string;
  project_code?: string;
}

export default function AdminCreateDPRScreen() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  
  // Optional extra fields for admin
  const [weatherConditions, setWeatherConditions] = useState('');
  const [manpowerCount, setManpowerCount] = useState('');

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await projectsApi.getAll();
      setProjects(data || []);
      if (data?.length > 0) {
        setSelectedProject(data[0]);
      }
    } catch (error) {
      console.error('Error loading projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (projectId: string) => {
    const project = projects.find(p => (p.project_id || p._id) === projectId);
    if (project) {
      setSelectedProject(project);
    }
  };

  const handleContinue = () => {
    if (selectedProject) {
      setShowForm(true);
    }
  };

  const handleSuccess = () => {
    router.replace('/(admin)/dpr');
  };

  const handleCancel = () => {
    if (showForm) {
      setShowForm(false);
    } else {
      router.back();
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading projects...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Show DPR Form
  if (showForm && selectedProject) {
    const projectId = selectedProject.project_id || selectedProject._id || '';
    
    return (
      <SafeAreaView style={styles.container} edges={['left', 'right']}>
        <DPRForm
          projectId={projectId}
          projectName={selectedProject.project_name}
          projectCode={selectedProject.project_code}
          onSuccess={handleSuccess}
          onCancel={handleCancel}
          showHeader={true}
          extraPayload={{
            weather_conditions: weatherConditions || undefined,
            manpower_count: manpowerCount ? parseInt(manpowerCount) : undefined,
          }}
        />
      </SafeAreaView>
    );
  }

  // Project Selection Screen
  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={handleCancel} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color={Colors.text} />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.headerTitle}>Create DPR</Text>
          <Text style={styles.headerSubtitle}>Select project and details</Text>
        </View>
      </View>

      <View style={styles.content}>
        {/* Project Selection */}
        <Card style={styles.card}>
          <View style={styles.sectionHeader}>
            <Ionicons name="business" size={20} color={Colors.primary} />
            <Text style={styles.sectionTitle}>Select Project</Text>
          </View>
          
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={selectedProject?.project_id || selectedProject?._id}
              onValueChange={handleProjectChange}
              style={styles.picker}
            >
              {projects.map((p) => (
                <Picker.Item
                  key={p.project_id || p._id}
                  label={p.project_name}
                  value={p.project_id || p._id}
                />
              ))}
            </Picker>
          </View>
        </Card>

        {/* Optional Details */}
        <Card style={styles.card}>
          <View style={styles.sectionHeader}>
            <Ionicons name="settings-outline" size={20} color={Colors.info} />
            <Text style={styles.sectionTitle}>Optional Details</Text>
          </View>
          
          <Text style={styles.label}>Weather Conditions</Text>
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={weatherConditions}
              onValueChange={setWeatherConditions}
              style={styles.picker}
            >
              <Picker.Item label="Select weather (optional)" value="" />
              <Picker.Item label="Sunny" value="Sunny" />
              <Picker.Item label="Cloudy" value="Cloudy" />
              <Picker.Item label="Rainy" value="Rainy" />
              <Picker.Item label="Windy" value="Windy" />
              <Picker.Item label="Hot" value="Hot" />
            </Picker>
          </View>

          <Text style={[styles.label, { marginTop: Spacing.md }]}>Manpower Count</Text>
          <TextInput
            style={styles.input}
            value={manpowerCount}
            onChangeText={setManpowerCount}
            placeholder="Number of workers (optional)"
            placeholderTextColor={Colors.textMuted}
            keyboardType="numeric"
          />
        </Card>

        {/* Continue Button */}
        <TouchableOpacity
          style={[styles.continueButton, !selectedProject && styles.buttonDisabled]}
          onPress={handleContinue}
          disabled={!selectedProject}
        >
          <Text style={styles.continueButtonText}>Continue to DPR</Text>
          <Ionicons name="arrow-forward" size={20} color={Colors.white} />
        </TouchableOpacity>

        <Text style={styles.hint}>
          You'll add photos and summary in the next step
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: Spacing.md,
    fontSize: FontSizes.md,
    color: Colors.textSecondary,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: Spacing.md,
    backgroundColor: Colors.white,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  backButton: {
    padding: Spacing.xs,
    marginRight: Spacing.sm,
  },
  headerInfo: {
    flex: 1,
  },
  headerTitle: {
    fontSize: FontSizes.lg,
    fontWeight: 'bold',
    color: Colors.text,
  },
  headerSubtitle: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
  },
  content: {
    flex: 1,
    padding: Spacing.md,
  },
  card: {
    padding: Spacing.md,
    marginBottom: Spacing.md,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: Spacing.md,
    gap: Spacing.sm,
  },
  sectionTitle: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.text,
  },
  label: {
    fontSize: FontSizes.sm,
    fontWeight: '500',
    color: Colors.text,
    marginBottom: Spacing.xs,
  },
  pickerContainer: {
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: BorderRadius.md,
    overflow: 'hidden',
  },
  picker: {
    height: 50,
  },
  input: {
    backgroundColor: Colors.background,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    fontSize: FontSizes.md,
    color: Colors.text,
  },
  continueButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.primary,
    padding: Spacing.md,
    borderRadius: BorderRadius.md,
    gap: Spacing.sm,
    marginTop: Spacing.md,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  continueButtonText: {
    fontSize: FontSizes.md,
    fontWeight: '600',
    color: Colors.white,
  },
  hint: {
    textAlign: 'center',
    fontSize: FontSizes.sm,
    color: Colors.textMuted,
    marginTop: Spacing.md,
  },
});
