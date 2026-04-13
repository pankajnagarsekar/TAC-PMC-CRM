import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  Modal,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import {
  ScheduleHealthMetrics,
  ResourceUtilizationData,
  FinancialSummaryData,
} from '../../types/api';

interface MetricsDetailProps {
  type: 'schedule' | 'resources' | 'financial';
  schedule?: ScheduleHealthMetrics;
  resources?: ResourceUtilizationData;
  financial?: FinancialSummaryData;
}

export function MetricsDetail({
  type,
  schedule,
  resources,
  financial,
}: MetricsDetailProps) {
  const { colors: Colors } = useTheme();
  const [expanded, setExpanded] = useState(false);

  const renderScheduleDetail = () => {
    if (!schedule) return null;
    return (
      <>
        <DetailRow label="Days Remaining" value={`${schedule.days_remaining}d`} />
        <DetailRow label="Tasks At Risk" value={`${schedule.tasks_at_risk}`} />
        <DetailRow label="Critical Path" value={`${schedule.critical_path_days}d`} />
        <StatusChip
          status={schedule.status}
          label={`Status: ${schedule.status.toUpperCase()}`}
        />
      </>
    );
  };

  const renderResourceDetail = () => {
    if (!resources) return null;
    return (
      <>
        <Text style={[styles.sectionLabel, { color: Colors.textSecondary }]}>
          BY RESOURCE
        </Text>
        {Object.entries(resources.by_resource || {}).slice(0, 3).map(([name, metrics]) => (
          <DetailRow
            key={name}
            label={name}
            value={`${metrics.allocation_percent.toFixed(0)}%`}
            valueColor={metrics.allocation_percent > 100 ? '#ef4444' : undefined}
          />
        ))}
        {resources.over_allocated?.length > 0 && (
          <View style={[styles.warningBox, { backgroundColor: Colors.surface }]}>
            <Ionicons name="alert-circle" size={14} color="#ef4444" />
            <Text style={[styles.warningText, { color: '#ef4444' }]}>
              {resources.over_allocated.length} resource(s) over-allocated
            </Text>
          </View>
        )}
      </>
    );
  };

  const renderFinancialDetail = () => {
    if (!financial) return null;
    const budgetPercent = (financial.budget_spent / financial.budget_total) * 100;
    return (
      <>
        <DetailRow
          label="Total Budget"
          value={`₹${(financial.budget_total / 100000).toFixed(1)}L`}
        />
        <DetailRow
          label="Spent"
          value={`₹${(financial.budget_spent / 100000).toFixed(1)}L`}
        />
        <DetailRow
          label="Remaining"
          value={`₹${(financial.budget_remaining / 100000).toFixed(1)}L`}
          valueColor={financial.budget_remaining < 0 ? '#ef4444' : undefined}
        />
        <View style={[styles.progressBar, { backgroundColor: Colors.border }]}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${Math.min(budgetPercent, 100)}%`,
                backgroundColor: budgetPercent > 100 ? '#ef4444' : '#10b981',
              },
            ]}
          />
        </View>
        <Text style={[styles.progressLabel, { color: Colors.textSecondary }]}>
          {budgetPercent.toFixed(1)}% consumed
        </Text>
        <DetailRow
          label="Daily Burn"
          value={`₹${(financial.burn_rate_daily / 1000).toFixed(0)}K/day`}
        />
      </>
    );
  };

  const title = type === 'schedule' ? 'Schedule Health' :
    type === 'resources' ? 'Resource Utilization' : 'Financial Summary';

  return (
    <>
      <Pressable
        onPress={() => setExpanded(true)}
        style={[styles.trigger, { borderColor: Colors.border, backgroundColor: Colors.surface }]}
      >
        <View style={styles.triggerContent}>
          <Text style={[styles.triggerLabel, { color: Colors.text }]}>{title}</Text>
          <Ionicons name="chevron-forward" size={18} color={Colors.primary} />
        </View>
      </Pressable>

      <Modal
        visible={expanded}
        transparent
        animationType="slide"
        onRequestClose={() => setExpanded(false)}
      >
        <View style={[styles.modal, { backgroundColor: Colors.background }]}>
          <View style={[styles.modalHeader, { borderBottomColor: Colors.border }]}>
            <Text style={[styles.modalTitle, { color: Colors.text }]}>{title}</Text>
            <Pressable onPress={() => setExpanded(false)}>
              <Ionicons name="close" size={24} color={Colors.text} />
            </Pressable>
          </View>
          <ScrollView
            contentContainerStyle={styles.modalContent}
            showsVerticalScrollIndicator={false}
          >
            {type === 'schedule' && renderScheduleDetail()}
            {type === 'resources' && renderResourceDetail()}
            {type === 'financial' && renderFinancialDetail()}
          </ScrollView>
        </View>
      </Modal>
    </>
  );
}

function DetailRow({
  label,
  value,
  valueColor,
}: {
  label: string;
  value: string;
  valueColor?: string;
}) {
  const { colors: Colors } = useTheme();
  return (
    <View style={styles.detailRow}>
      <Text style={[styles.detailLabel, { color: Colors.textSecondary }]}>
        {label}
      </Text>
      <Text
        style={[styles.detailValue, { color: valueColor || Colors.text }]}
      >
        {value}
      </Text>
    </View>
  );
}

function StatusChip({
  status,
  label,
}: {
  status: 'green' | 'yellow' | 'red';
  label: string;
}) {
  const statusColors = {
    green: '#10b981',
    yellow: '#eab308',
    red: '#ef4444',
  };
  return (
    <View
      style={[styles.statusChip, { backgroundColor: `${statusColors[status]}20` }]}
    >
      <View
        style={[styles.statusDot, { backgroundColor: statusColors[status] }]}
      />
      <Text style={[styles.statusText, { color: statusColors[status] }]}>
        {label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  trigger: {
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
    marginVertical: 6,
  },
  triggerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  triggerLabel: {
    fontSize: 13,
    fontWeight: '700',
  },
  modal: {
    flex: 1,
    paddingTop: 40,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '800',
  },
  modalContent: {
    padding: 16,
    paddingBottom: 40,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: 12,
    marginBottom: 8,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 0.5,
    borderBottomColor: 'rgba(0,0,0,0.1)',
  },
  detailLabel: {
    fontSize: 13,
    fontWeight: '600',
  },
  detailValue: {
    fontSize: 14,
    fontWeight: '700',
  },
  progressBar: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
    marginVertical: 8,
  },
  progressFill: {
    height: '100%',
  },
  progressLabel: {
    fontSize: 11,
    fontWeight: '500',
    marginBottom: 8,
  },
  warningBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    borderRadius: 6,
    marginTop: 8,
    borderWidth: 1,
    borderColor: '#fecaca',
  },
  warningText: {
    fontSize: 12,
    fontWeight: '600',
  },
  statusChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 6,
    alignSelf: 'flex-start',
    marginTop: 8,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
  },
});
