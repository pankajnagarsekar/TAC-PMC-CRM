// ============================================================
// SITE FUNDS SCREEN — Unified Petty Cash + Site Overheads
// ============================================================
// GROUND RULE: ZERO client-side math.
// All logic flags and balances are server-computed.
// 'CREDIT' types and manual Category selection are disabled.
// ============================================================

import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Modal,
  TextInput,
  ActivityIndicator,
  Alert,
  RefreshControl,
  SafeAreaView,
} from 'react-native';
import { useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { format } from 'date-fns';

import ScreenHeader from '../../components/ScreenHeader';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import {
  Colors,
  Spacing,
  Shadows,
  BorderRadius,
  FontSizes,
} from '../../constants/theme';
import { useProject } from '../../contexts/ProjectContext';
import { cashApi } from '../../services/apiClient';
import type { CashCategory } from '../../services/apiClient';

// --------------------------------------------------------
// LOCAL TYPES
// --------------------------------------------------------

type FundType = 'PETTY_CASH' | 'OVH';

interface CashTransaction {
  id: string;
  category_id: string;
  amount: number;
  type: 'DEBIT' | 'CREDIT';
  purpose: string;
  recorded_by: string;
  recorded_at: string;
}

// --------------------------------------------------------
// HELPERS
// --------------------------------------------------------

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(val);

// --------------------------------------------------------
// SUB-COMPONENTS
// --------------------------------------------------------

const FundToggle = React.memo(({ active, onChange }: { active: FundType; onChange: (t: FundType) => void }) => (
  <View style={styles.toggleContainer}>
    <View style={styles.toggleTrack}>
      {(['PETTY_CASH', 'OVH'] as FundType[]).map((type) => {
        const isActive = active === type;
        return (
          <TouchableOpacity
            key={type}
            onPress={() => onChange(type)}
            style={[styles.toggleBtn, isActive && styles.toggleBtnActive]}
            activeOpacity={0.7}
          >
            <Text style={[styles.toggleText, isActive && styles.toggleTextActive]}>
              {type === 'PETTY_CASH' ? 'Petty Cash' : 'Site Overheads'}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  </View>
));

const TransactionRow = React.memo(({ item }: { item: CashTransaction }) => {
  const isDebit = item.type === 'DEBIT';
  return (
    <View style={styles.txRow}>
      <View style={styles.txLeft}>
        <Text style={styles.txPurpose} numberOfLines={1}>{item.purpose}</Text>
        <Text style={styles.txMeta}>
          {format(new Date(item.recorded_at), 'dd MMM, HH:mm')} • {item.recorded_by}
        </Text>
      </View>
      <View style={styles.txRight}>
        <Text style={[styles.txAmount, isDebit ? styles.textError : styles.textSuccess]}>
          {isDebit ? '-' : '+'}{formatCurrency(item.amount)}
        </Text>
        <View style={[styles.txBadge, isDebit ? styles.badgeError : styles.badgeSuccess]}>
          <Text style={styles.txBadgeText}>{item.type}</Text>
        </View>
      </View>
    </View>
  );
});

// --------------------------------------------------------
// MAIN COMPONENT
// --------------------------------------------------------

export default function SiteFundsScreen() {
  const { selectedProject } = useProject();
  const [activeFundType, setActiveFundType] = useState<FundType>('PETTY_CASH');
  const [categories, setCategories] = useState<CashCategory[]>([]);
  const [transactions, setTransactions] = useState<CashTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({ amount: '', purpose: '' });

  // Server-driven selection matching names
  const currentCategory = useMemo(() => {
    return categories.find((cat) => {
      const name = cat.category_name.toLowerCase();
      if (activeFundType === 'PETTY_CASH') return name.includes('petty');
      return name.includes('ovh') || name.includes('overhead');
    });
  }, [categories, activeFundType]);

  const syncFunds = useCallback(async (isSilent = false) => {
    if (!selectedProject?.project_id) return;
    if (!isSilent) setLoading(true);

    try {
      const summary = await cashApi.getSummary(selectedProject.project_id);
      const freshCats = summary.categories || [];
      setCategories(freshCats);

      const target = freshCats.find((cat) => {
        const name = cat.category_name.toLowerCase();
        if (activeFundType === 'PETTY_CASH') return name.includes('petty');
        return name.includes('ovh') || name.includes('overhead');
      });

      if (target) {
        const txRes = await cashApi.listTransactions(selectedProject.project_id, {
          category_id: target.category_id,
          limit: 50,
        });
        setTransactions(txRes.items as CashTransaction[]);
      } else {
        setTransactions([]);
      }
    } catch (err) {
      console.error('[SiteFunds] sync error:', err);
      Alert.alert('Sync Error', 'Failed to retrieve site funds.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedProject?.project_id, activeFundType]);

  useFocusEffect(
    useCallback(() => {
      syncFunds();
    }, [syncFunds])
  );

  useEffect(() => {
    syncFunds(true);
  }, [activeFundType]);

  const handleRecordExpense = async () => {
    if (!currentCategory || !selectedProject) return;
    const amount = parseFloat(formData.amount);
    if (!amount || amount <= 0) return Alert.alert('Invalid amount');
    if (formData.purpose.trim().length < 3) return Alert.alert('Description too short');

    setSubmitting(true);
    try {
      const idempotencyKey = `tx-${Date.now()}`;
      await cashApi.createTransaction(
        selectedProject.project_id,
        {
          category_id: currentCategory.category_id,
          amount,
          type: 'DEBIT', // Forced Security constraint
          purpose: formData.purpose.trim(),
        },
        idempotencyKey
      );
      setModalVisible(false);
      setFormData({ amount: '', purpose: '' });
      syncFunds(true);
      Alert.alert('Recorded', 'Expense logged successfully.');
    } catch (err) {
      Alert.alert('Error', 'Failed to log transaction.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderHeader = () => (
    <View style={styles.headerStack}>
      {currentCategory ? (
        <Card variant="elevated" padding="lg" style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>Available Balance</Text>
          <Text style={[styles.summaryValue, currentCategory.is_negative && styles.textError]}>
            {formatCurrency(currentCategory.cash_in_hand)}
          </Text>
          <View style={styles.summaryDivider} />
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Allocation Total</Text>
            <Text style={styles.metaValue}>{formatCurrency(currentCategory.allocation_total)}</Text>
          </View>
          {(currentCategory.is_negative || currentCategory.threshold_breached) && (
            <View style={styles.flagContainer}>
              {currentCategory.is_negative && (
                <View style={styles.flagPillError}>
                  <Ionicons name="alert-circle" size={14} color="white" />
                  <Text style={styles.flagText}>Deficit</Text>
                </View>
              )}
              {currentCategory.threshold_breached && (
                <View style={styles.flagPillWarning}>
                  <Ionicons name="warning" size={14} color="white" />
                  <Text style={styles.flagText}>Strict Limit</Text>
                </View>
              )}
            </View>
          )}
        </Card>
      ) : (
        <View style={styles.placeholderCard}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      )}

      <Button
        title="Record Expense"
        onPress={() => setModalVisible(true)}
        variant="primary"
        size="lg"
        disabled={!currentCategory}
        icon={<Ionicons name="add" size={20} color="white" />}
      />

      <Text style={styles.sectionTitle}>Fund Ledger</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScreenHeader title="Site Funds" />
      <FundToggle active={activeFundType} onChange={setActiveFundType} />

      <FlatList
        data={transactions}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <TransactionRow item={item} />}
        ListHeaderComponent={renderHeader}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => syncFunds(true)} tintColor={Colors.primary} />
        }
        ListEmptyComponent={
          !loading && <Text style={styles.emptyText}>No recent entries found.</Text>
        }
      />

      <Modal visible={modalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Record Expense</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>
            <Text style={styles.modalSubtitle}>Target: {activeFundType === 'PETTY_CASH' ? 'Petty Cash' : 'Site Overheads'}</Text>

            <View style={styles.field}>
              <Text style={styles.label}>Amount (₹)</Text>
              <TextInput
                style={styles.input}
                value={formData.amount}
                onChangeText={(t) => setFormData({ ...formData, amount: t.replace(/[^0-9.]/g, '') })}
                keyboardType="decimal-pad"
                autoFocus
                placeholder="0"
              />
            </View>
            <View style={styles.field}>
              <Text style={styles.label}>Note</Text>
              <TextInput
                style={[styles.input, { height: 80 }]}
                value={formData.purpose}
                onChangeText={(t) => setFormData({ ...formData, purpose: t })}
                placeholder="Details..."
                multiline
              />
            </View>
            <View style={styles.modalActions}>
              <Button title="Cancel" variant="outline" onPress={() => setModalVisible(false)} style={{ flex: 1 }} />
              <Button title="Save Entry" variant="primary" onPress={handleRecordExpense} loading={submitting} style={{ flex: 1 }} />
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  listContent: { padding: Spacing.md },
  toggleContainer: { backgroundColor: Colors.background, padding: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  toggleTrack: { flexDirection: 'row', backgroundColor: Colors.inputBg, borderRadius: BorderRadius.lg, padding: 2 },
  toggleBtn: { flex: 1, paddingVertical: 10, alignItems: 'center', borderRadius: BorderRadius.md },
  toggleBtnActive: { backgroundColor: Colors.surface, ...Shadows.sm },
  toggleText: { fontSize: FontSizes.sm, color: Colors.textSecondary, fontWeight: '600' },
  toggleTextActive: { color: Colors.primary },
  headerStack: { marginVertical: Spacing.md },
  summaryCard: { marginBottom: Spacing.md },
  summaryLabel: { fontSize: FontSizes.xs, color: Colors.textSecondary, textTransform: 'uppercase' },
  summaryValue: { fontSize: 32, fontWeight: 'bold', color: Colors.primary, marginVertical: 4 },
  summaryDivider: { height: 1, backgroundColor: Colors.divider, marginVertical: Spacing.md },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between' },
  metaLabel: { fontSize: FontSizes.sm, color: Colors.textSecondary },
  metaValue: { fontSize: FontSizes.sm, fontWeight: '600' },
  flagContainer: { flexDirection: 'row', marginTop: Spacing.md, gap: 8 },
  flagPillError: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.error, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 20, gap: 4 },
  flagPillWarning: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.warning, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 20, gap: 4 },
  flagText: { color: 'white', fontSize: 10, fontWeight: 'bold' },
  sectionTitle: { fontSize: FontSizes.sm, fontWeight: 'bold', color: Colors.textMuted, textTransform: 'uppercase', marginTop: Spacing.xl, marginBottom: Spacing.sm },
  txRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: Spacing.md, borderBottomWidth: 1, borderBottomColor: Colors.border },
  txLeft: { flex: 1 },
  txPurpose: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  txMeta: { fontSize: FontSizes.xs, color: Colors.textMuted, marginTop: 2 },
  txRight: { alignItems: 'flex-end' },
  txAmount: { fontSize: FontSizes.md, fontWeight: 'bold' },
  txBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, marginTop: 4 },
  txBadgeText: { fontSize: 9, fontWeight: '800', color: 'white' },
  textError: { color: Colors.error },
  textSuccess: { color: Colors.success },
  badgeError: { backgroundColor: Colors.error },
  badgeSuccess: { backgroundColor: Colors.success },
  placeholderCard: { height: 160, justifyContent: 'center', backgroundColor: Colors.surface, borderRadius: BorderRadius.lg, marginBottom: Spacing.md },
  emptyText: { textAlign: 'center', color: Colors.textMuted, marginTop: 40 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalSheet: { backgroundColor: Colors.surface, borderTopLeftRadius: BorderRadius.xl, borderTopRightRadius: BorderRadius.xl, padding: Spacing.lg, paddingBottom: 40 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  modalTitle: { fontSize: FontSizes.xl, fontWeight: 'bold' },
  modalSubtitle: { fontSize: FontSizes.xs, color: Colors.textSecondary, marginBottom: Spacing.lg },
  field: { marginBottom: Spacing.md },
  label: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.textSecondary, marginBottom: 4 },
  input: { backgroundColor: Colors.inputBg, borderRadius: BorderRadius.md, padding: Spacing.md, fontSize: FontSizes.md, borderWidth: 1, borderColor: Colors.border, color: Colors.text },
  modalActions: { flexDirection: 'row', gap: Spacing.md, marginTop: Spacing.md },
});
