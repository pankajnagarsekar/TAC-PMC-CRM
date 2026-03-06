// PETTY CASH SCREEN (PHASE 7 PARITY)
// Manage petty cash expenses and reimbursements with hardened logic
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  Pressable,
  ActivityIndicator,
  TextInput,
  Modal,
  Alert,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { Picker } from '@react-native-picker/picker';
import { projectsApi, codesApi, cashApi } from '../../services/apiClient';
import { Colors, Spacing, FontSizes, BorderRadius, Shadows } from '../../constants/theme';
import ScreenHeader from '../../components/ScreenHeader';
import { useProject } from '../../contexts/ProjectContext';

const formatCurrency = (amount: number): string => {
  return `₹${amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export default function PettyCashScreen() {
  const { selectedProject } = useProject();
  const [summary, setSummary] = useState<any>(null);
  const [transactions, setTransactions] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [saving, setSaving] = useState(false);

  // Form state
  const [categoryId, setCategoryId] = useState('');
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [type, setType] = useState<'DEBIT' | 'CREDIT'>('DEBIT');
  const [purpose, setPurpose] = useState('');

  const loadData = useCallback(async () => {
    if (!selectedProject) {
      setLoading(false);
      return;
    }

    try {
      const [summaryData, transData, codesData] = await Promise.all([
        cashApi.getSummary(selectedProject.project_id),
        cashApi.listTransactions(selectedProject.project_id, { limit: 50 }),
        codesApi.getAll(true)
      ]);
      setSummary(summaryData);
      setTransactions(transData.items || []);
      setCategories(codesData || []);
    } catch (error) {
      console.error('Error loading petty cash data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedProject]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleSave = async () => {
    if (!selectedProject) return;
    if (!categoryId || !amount || !description.trim()) {
      Alert.alert('Required Fields', 'Please fill Category, Amount and Description.');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        category_id: categoryId,
        amount: parseFloat(amount),
        type,
        purpose: description.trim(), // Use purpose field from backend
        bill_reference: '', // Future: allow entry
      };

      const idempotencyKey = `mob-${Date.now()}`;
      await cashApi.createTransaction(selectedProject.project_id, payload, idempotencyKey);
      
      setModalVisible(false);
      resetForm();
      loadData();
      Alert.alert('Success', 'Transaction recorded.');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to save transaction');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setCategoryId('');
    setDescription('');
    setAmount('');
    setType('DEBIT');
    setPurpose('');
  };

  const renderHeader = () => {
    if (!summary) return null;

    return (
      <View style={styles.headerSection}>
        {/* Threshold Banner */}
        {summary.flags.is_below_threshold && !summary.flags.is_negative && (
          <View style={styles.warningBanner}>
            <Ionicons name="warning" size={20} color={Colors.warning} />
            <Text style={styles.warningText}>Low Cash Warning: Below Threshold</Text>
          </View>
        )}

        {/* Negative Balance Banner */}
        {summary.flags.is_negative && (
          <View style={styles.errorBanner}>
            <Ionicons name="alert-circle" size={20} color={Colors.white} />
            <Text style={styles.errorBannerText}>Negative Balance: Top-up Required</Text>
          </View>
        )}

        {/* Balance Card */}
        <View style={[styles.balanceCard, summary.flags.is_negative && styles.balanceCardNegative]}>
          <Text style={[styles.balanceLabel, summary.flags.is_negative && { color: Colors.white }]}>
            Current Cash in Hand
          </Text>
          <Text style={[styles.balanceAmount, summary.flags.is_negative && { color: Colors.white }]}>
            {formatCurrency(summary.cash_in_hand)}
          </Text>
          
          <View style={styles.balanceFooter}>
            <View style={styles.footerItem}>
              <Text style={[styles.footerLabel, summary.flags.is_negative && { color: Colors.white + '80' }]}>Allocation</Text>
              <Text style={[styles.footerValue, summary.flags.is_negative && { color: Colors.white }]}>{formatCurrency(summary.allocation_total)}</Text>
            </View>
            <View style={styles.footerDivider} />
            <View style={styles.footerItem}>
              <Text style={[styles.footerLabel, summary.flags.is_negative && { color: Colors.white + '80' }]}>Last PC</Text>
              <Text style={[styles.footerValue, summary.flags.is_negative && { color: Colors.white }]}>
                {summary.days_since_last_pc_close !== null ? `${summary.days_since_last_pc_close}d ago` : 'N/A'}
              </Text>
            </View>
          </View>
        </View>

        <Text style={styles.sectionTitle}>Recent Transactions</Text>
      </View>
    );
  };

  const renderTransaction = ({ item }: { item: any }) => {
    const isDebit = item.type === 'DEBIT';
    const categoryName = categories.find(c => (c.code_id || c._id) === item.category_id)?.code_name || 'General';

    return (
      <View style={styles.transCard}>
        <View style={styles.transMain}>
          <View style={styles.transIconContainer}>
            <View style={[styles.transIcon, { backgroundColor: isDebit ? Colors.errorLight : Colors.successLight }]}>
              <Ionicons 
                name={isDebit ? "arrow-down" : "arrow-up"} 
                size={20} 
                color={isDebit ? Colors.error : Colors.success} 
              />
            </View>
          </View>
          <View style={styles.transDetails}>
            <Text style={styles.transPurpose} numberOfLines={1}>{item.purpose || 'No description'}</Text>
            <Text style={styles.transMeta}>{categoryName} • {new Date(item.created_at).toLocaleDateString()}</Text>
          </View>
          <View style={styles.transAmountContainer}>
            <Text style={[styles.transAmount, { color: isDebit ? Colors.error : Colors.success }]}>
              {isDebit ? '-' : '+'}{formatCurrency(item.amount)}
            </Text>
          </View>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ScreenHeader title="Petty Cash" />
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  if (!selectedProject) {
    return (
      <SafeAreaView style={styles.container}>
        <ScreenHeader title="Petty Cash" />
        <View style={styles.centerContainer}>
          <Ionicons name="business-outline" size={64} color={Colors.textMuted} />
          <Text style={styles.emptyTitle}>No Project Selected</Text>
          <Text style={styles.emptySubtitle}>Please select a project from the Dashboard.</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['left', 'right']}>
      <ScreenHeader title="Petty Cash" />

      <FlatList
        data={transactions}
        renderItem={renderTransaction}
        keyExtractor={(item) => item._id}
        ListHeaderComponent={renderHeader}
        contentContainerStyle={styles.listContent}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={styles.centerContainer}>
            <Ionicons name="receipt-outline" size={48} color={Colors.textMuted} />
            <Text style={styles.emptyText}>No recent transactions</Text>
          </View>
        }
      />

      <Pressable style={styles.fab} onPress={() => setModalVisible(true)}>
        <Ionicons name="add" size={28} color={Colors.white} />
      </Pressable>

      <Modal visible={modalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>New Transaction</Text>
              <Pressable onPress={() => setModalVisible(false)} hitSlop={10}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </Pressable>
            </View>

            <ScrollView style={styles.modalBody} keyboardShouldPersistTaps="handled">
              {/* Type Switch */}
              <View style={styles.typeSwitch}>
                <Pressable 
                  style={[styles.typeBtn, type === 'DEBIT' && styles.typeBtnActiveDebit]}
                  onPress={() => setType('DEBIT')}
                >
                  <Text style={[styles.typeBtnText, type === 'DEBIT' && styles.typeBtnTextActive]}>EXPENSE</Text>
                </Pressable>
                <Pressable 
                  style={[styles.typeBtn, type === 'CREDIT' && styles.typeBtnActiveCredit]}
                  onPress={() => setType('CREDIT')}
                >
                  <Text style={[styles.typeBtnText, type === 'CREDIT' && styles.typeBtnTextActive]}>INCOME/TOP-UP</Text>
                </Pressable>
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Category *</Text>
                <View style={styles.pickerContainer}>
                  <Picker 
                    selectedValue={categoryId} 
                    onValueChange={setCategoryId}
                    style={styles.picker}
                  >
                    <Picker.Item label="Select Category" value="" />
                    {categories.map(c => (
                      <Picker.Item key={c.code_id || c._id} label={c.code_name} value={c.code_id || c._id} />
                    ))}
                  </Picker>
                </View>
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Amount (₹) *</Text>
                <TextInput
                  style={styles.input}
                  value={amount}
                  onChangeText={setAmount}
                  placeholder="0.00"
                  keyboardType="decimal-pad"
                  placeholderTextColor={Colors.textMuted}
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Description / Purpose *</Text>
                <TextInput
                  style={[styles.input, styles.textArea]}
                  value={description}
                  onChangeText={setDescription}
                  placeholder="What was this for?"
                  placeholderTextColor={Colors.textMuted}
                  multiline
                  numberOfLines={3}
                />
              </View>

              <View style={styles.spacer} />
            </ScrollView>

            <View style={styles.modalFooter}>
              <Pressable 
                style={[styles.saveButton, saving && styles.saveButtonDisabled]} 
                onPress={handleSave} 
                disabled={saving}
              >
                {saving ? (
                  <ActivityIndicator size="small" color={Colors.white} />
                ) : (
                  <Text style={styles.saveButtonText}>Save Transaction</Text>
                )}
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centerContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: Spacing.xl },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  listContent: { paddingBottom: 100 },
  
  headerSection: { padding: Spacing.md },
  sectionTitle: { fontSize: FontSizes.sm, fontWeight: '700', color: Colors.textSecondary, textTransform: 'uppercase', marginBottom: Spacing.sm, marginTop: Spacing.lg },

  // Banners
  warningBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.warningLight, padding: Spacing.sm, borderRadius: BorderRadius.md, marginBottom: Spacing.md, gap: Spacing.sm, borderWidth: 1, borderColor: Colors.warning },
  warningText: { color: Colors.warning, fontWeight: '600', fontSize: FontSizes.sm },
  errorBanner: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.error, padding: Spacing.sm, borderRadius: BorderRadius.md, marginBottom: Spacing.md, gap: Spacing.sm },
  errorBannerText: { color: Colors.white, fontWeight: '700', fontSize: FontSizes.sm },

  // Balance Card
  balanceCard: { backgroundColor: Colors.white, padding: Spacing.lg, borderRadius: BorderRadius.lg, ...Shadows.md },
  balanceCardNegative: { backgroundColor: Colors.error },
  balanceLabel: { fontSize: FontSizes.sm, color: Colors.textSecondary, marginBottom: 4 },
  balanceAmount: { fontSize: FontSizes.xxxl, fontWeight: 'bold', color: Colors.text, marginBottom: Spacing.md },
  balanceFooter: { flexDirection: 'row', borderTopWidth: 1, borderTopColor: Colors.border, paddingTop: Spacing.md },
  footerItem: { flex: 1 },
  footerLabel: { fontSize: 10, color: Colors.textMuted, textTransform: 'uppercase' },
  footerValue: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.text, marginTop: 2 },
  footerDivider: { width: 1, backgroundColor: Colors.border, marginHorizontal: Spacing.md },

  // Transaction Cards
  transCard: { backgroundColor: Colors.white, marginHorizontal: Spacing.md, marginBottom: Spacing.xs, borderRadius: BorderRadius.md, padding: Spacing.md },
  transMain: { flexDirection: 'row', alignItems: 'center' },
  transIconContainer: { marginRight: Spacing.md },
  transIcon: { width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  transDetails: { flex: 1 },
  transPurpose: { fontSize: FontSizes.md, fontWeight: '600', color: Colors.text },
  transMeta: { fontSize: FontSizes.xs, color: Colors.textMuted, marginTop: 2 },
  transAmountContainer: { alignItems: 'flex-end' },
  transAmount: { fontSize: FontSizes.md, fontWeight: '700' },

  emptyTitle: { fontSize: FontSizes.lg, fontWeight: '600', color: Colors.text, marginTop: Spacing.md },
  emptySubtitle: { fontSize: FontSizes.sm, color: Colors.textMuted, textAlign: 'center', marginTop: 4 },
  emptyText: { fontSize: FontSizes.sm, color: Colors.textMuted, marginTop: Spacing.md },

  // FAB
  fab: { position: 'absolute', right: Spacing.lg, bottom: Spacing.lg, width: 56, height: 56, borderRadius: 28, backgroundColor: Colors.accent, justifyContent: 'center', alignItems: 'center', ...Shadows.lg },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalContent: { backgroundColor: Colors.white, borderTopLeftRadius: BorderRadius.xl, borderTopRightRadius: BorderRadius.xl, maxHeight: '90%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: Spacing.lg, borderBottomWidth: 1, borderBottomColor: Colors.border },
  modalTitle: { fontSize: FontSizes.lg, fontWeight: '700', color: Colors.text },
  modalBody: { padding: Spacing.lg },
  
  typeSwitch: { flexDirection: 'row', backgroundColor: Colors.inputBg, borderRadius: BorderRadius.md, padding: 4, marginBottom: Spacing.lg },
  typeBtn: { flex: 1, paddingVertical: Spacing.sm, alignItems: 'center', borderRadius: BorderRadius.sm },
  typeBtnActiveDebit: { backgroundColor: Colors.error },
  typeBtnActiveCredit: { backgroundColor: Colors.success },
  typeBtnText: { fontSize: FontSizes.xs, fontWeight: '700', color: Colors.textSecondary },
  typeBtnTextActive: { color: Colors.white },

  inputGroup: { marginBottom: Spacing.md },
  inputLabel: { fontSize: FontSizes.sm, fontWeight: '600', color: Colors.text, marginBottom: Spacing.xs },
  input: { backgroundColor: Colors.inputBg, borderRadius: BorderRadius.md, paddingHorizontal: Spacing.md, paddingVertical: Spacing.md, fontSize: FontSizes.md, color: Colors.text, borderWidth: 1, borderColor: Colors.inputBorder },
  textArea: { height: 80, textAlignVertical: 'top' },
  pickerContainer: { backgroundColor: Colors.inputBg, borderRadius: BorderRadius.md, borderWidth: 1, borderColor: Colors.inputBorder, overflow: 'hidden' },
  picker: { height: 50 },
  
  modalFooter: { padding: Spacing.lg, borderTopWidth: 1, borderTopColor: Colors.border },
  saveButton: { backgroundColor: Colors.primary, paddingVertical: Spacing.md, borderRadius: BorderRadius.md, alignItems: 'center' },
  saveButtonDisabled: { opacity: 0.6 },
  saveButtonText: { color: Colors.white, fontSize: FontSizes.md, fontWeight: '700' },
  spacer: { height: 40 },
});
