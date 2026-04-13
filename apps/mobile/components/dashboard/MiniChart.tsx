import React, { useMemo } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import { DayMetric } from '../../types/api';

interface MiniChartProps {
  data: DayMetric[];
  label: string;
  metric: 'budget' | 'completion' | 'utilization';
  value: number;
  unit?: string;
}

export function MiniChart({ data, label, metric, value, unit = '' }: MiniChartProps) {
  const { colors: Colors } = useTheme();

  // Calculate sparkline visual (simple bar chart)
  const max = useMemo(() => Math.max(...(data?.map(d => d.value) || [1])), [data]);

  // Determine color based on metric
  const getColor = () => {
    if (metric === 'budget') return '#ef4444'; // red for spend
    if (metric === 'completion') return '#10b981'; // green for completion
    return '#3b82f6'; // blue for utilization
  };

  const trendValue = data && data.length >= 2 ?
    ((data[data.length - 1].value - data[data.length - 2].value) / data[data.length - 2].value) * 100
    : 0;

  const trendIcon = trendValue > 0 ? 'trending-up' : 'trending-down';
  const trendColor = trendValue > 0 ? '#10b981' : '#ef4444';

  return (
    <View style={[styles.container, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
      <View style={styles.header}>
        <Text style={[styles.label, { color: Colors.textSecondary }]}>{label}</Text>
        <View style={styles.trendBadge}>
          <Ionicons name={trendIcon} size={12} color={trendColor} />
          <Text style={[styles.trendText, { color: trendColor }]}>
            {Math.abs(trendValue).toFixed(0)}%
          </Text>
        </View>
      </View>

      {/* Sparkline bars */}
      <View style={styles.sparklineContainer}>
        {data?.map((point, idx) => (
          <View
            key={idx}
            style={[
              styles.sparklineBar,
              {
                height: `${(point.value / max) * 100}%`,
                backgroundColor: getColor(),
              },
            ]}
          />
        ))}
      </View>

      {/* Value display */}
      <View style={styles.footer}>
        <Text style={[styles.value, { color: Colors.text }]}>
          {value.toFixed(1)}{unit}
        </Text>
        <Text style={[styles.period, { color: Colors.textSecondary }]}>
          Last 7 days
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  label: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  trendBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  trendText: {
    fontSize: 9,
    fontWeight: '700',
  },
  sparklineContainer: {
    flexDirection: 'row',
    height: 40,
    gap: 2,
    alignItems: 'flex-end',
    marginBottom: 10,
  },
  sparklineBar: {
    flex: 1,
    borderRadius: 2,
    minHeight: 2,
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  value: {
    fontSize: 14,
    fontWeight: '800',
  },
  period: {
    fontSize: 9,
    fontWeight: '500',
  },
});
