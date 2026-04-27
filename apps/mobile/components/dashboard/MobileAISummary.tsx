import React, { useCallback, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Pressable,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { useProject } from '../../contexts/ProjectContext';
import { authApi } from '../../services/apiClient';
import { Card } from '../ui';

export function MobileAISummary() {
  const { selectedProject } = useProject();
  const { colors: Colors } = useTheme();
  const [summaries, setSummaries] = useState<Record<string, string>>({
    schedule: '',
    financial: '',
    resources: '',
  });
  const [loading, setLoading] = useState<Record<string, boolean>>({
    schedule: false,
    financial: false,
    resources: false,
  });
  const [expanded, setExpanded] = useState<string | null>(null);

  const generateSummary = useCallback(
    async (type: 'schedule' | 'financial' | 'resources') => {
      if (!selectedProject) return;

      setLoading((prev) => ({ ...prev, [type]: true }));
      try {
        // Stream AI summary from backend
        const token = await authApi.getToken();
        const response = await fetch(
          `${process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/v1/reporting/${selectedProject.project_id}/ai-summary/stream/${type}`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token || ''}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error(`Failed to generate summary: ${response.statusText}`);
        }

        // Read streaming response
        const reader = response.body?.getReader();
        const decoder = new TextDecoder();
        let text = '';

        if (reader) {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            text += decoder.decode(value, { stream: true });
            setSummaries((prev) => ({ ...prev, [type]: text }));
          }
        }
      } catch (err) {
        const error = err instanceof Error ? err.message : 'Failed to generate summary';
        setSummaries((prev) => ({ ...prev, [type]: error }));
      } finally {
        setLoading((prev) => ({ ...prev, [type]: false }));
      }
    },
    [selectedProject]
  );

  if (!selectedProject) {
    return (
      <View style={[styles.emptyContainer, { backgroundColor: Colors.surface }]}>
        <Text style={[styles.emptyText, { color: Colors.textSecondary }]}>
          Select a project to view AI insights
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={[styles.sectionTitle, { color: Colors.textSecondary }]}>
        AI INSIGHTS
      </Text>

      {/* Summary Cards */}
      {(['schedule', 'financial', 'resources'] as const).map((type) => (
        <Card
          key={type}
          padding="md"
          style={[
            styles.summaryCard,
            { borderColor: Colors.border },
          ]}
        >
          <Pressable
            onPress={() => setExpanded(expanded === type ? null : type)}
            style={styles.cardHeader}
          >
            <View style={styles.headerLeft}>
              <Ionicons
                name={
                  type === 'schedule'
                    ? 'calendar-outline'
                    : type === 'financial'
                      ? 'trending-up-outline'
                      : 'people-outline'
                }
                size={16}
                color={Colors.primary}
                style={styles.icon}
              />
              <Text
                style={[
                  styles.cardTitle,
                  { color: Colors.text },
                ]}
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </Text>
            </View>
            <Ionicons
              name={expanded === type ? 'chevron-up' : 'chevron-down'}
              size={16}
              color={Colors.textSecondary}
            />
          </Pressable>

          {/* Expanded Content */}
          {expanded === type && (
            <View style={styles.expandedContent}>
              {loading[type] ? (
                <View style={styles.loadingContainer}>
                  <ActivityIndicator size="small" color={Colors.primary} />
                  <Text style={[styles.loadingText, { color: Colors.textSecondary }]}>
                    Generating insights...
                  </Text>
                </View>
              ) : summaries[type] ? (
                <Text style={[styles.summaryText, { color: Colors.text }]}>
                  {summaries[type]}
                </Text>
              ) : (
                <Pressable
                  onPress={() => generateSummary(type)}
                  style={[
                    styles.generateButton,
                    { backgroundColor: Colors.primary },
                  ]}
                >
                  <Text style={styles.generateButtonText}>
                    Generate Insight
                  </Text>
                </Pressable>
              )}
            </View>
          )}
        </Card>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: 16,
  },
  sectionTitle: {
    fontSize: 10,
    fontWeight: '900',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: 10,
    opacity: 0.6,
  },
  summaryCard: {
    marginBottom: 10,
    borderWidth: 1,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  icon: {
    marginRight: 4,
  },
  cardTitle: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'capitalize',
  },
  expandedContent: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.1)',
  },
  summaryText: {
    fontSize: 12,
    lineHeight: 18,
    fontWeight: '500',
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    justifyContent: 'center',
    paddingVertical: 12,
  },
  loadingText: {
    fontSize: 11,
    fontWeight: '500',
  },
  generateButton: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignItems: 'center',
  },
  generateButtonText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  emptyContainer: {
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
  },
});
