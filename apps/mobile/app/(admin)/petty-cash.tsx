// ============================================================
// SITE FUNDS SCREEN — Unified Petty Cash + Site Overheads
// ============================================================
// Luxury Industrial Design System Enforcement
// ============================================================

import React, { useState, useCallback, useMemo, useEffect } from "react";
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
  StatusBar,
  Platform,
} from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { format } from "date-fns";
import { BlurView } from 'expo-blur';

import ScreenHeader from "../../components/ScreenHeader";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { useTheme } from "../../contexts/ThemeContext";
import { useProject } from "../../contexts/ProjectContext";
import { cashApi } from "../../services/apiClient";
import type { CashCategory, CashTransaction } from "../../services/apiClient";

// --------------------------------------------------------
// LOCAL TYPES
// --------------------------------------------------------

type FundType = "PETTY_CASH" | "OVH";

const formatCurrency = (val: number) => {
  try {
    const num = typeof val === 'number' ? val : parseFloat(val as any);
    if (isNaN(num)) return "₹0";
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(num);
  } catch (e) {
    return "₹0";
  }
};

// --------------------------------------------------------
// SUB-COMPONENTS
// --------------------------------------------------------

const FundToggle = React.memo(({ active, onChange }: { active: FundType; onChange: (t: FundType) => void; }) => {
    const { colors: Colors, spacing: Spacing, borderRadius: BorderRadius } = useTheme();
    const styles = useMemo(() => getStyles(Colors, Spacing, BorderRadius), [Colors, Spacing, BorderRadius]);
    
    return (
    <View style={styles.toggleWrapper}>
      <View style={[styles.toggleTrack, { backgroundColor: Colors.surface, borderColor: Colors.border }]}>
        {(["PETTY_CASH", "OVH"] as FundType[]).map((type) => {
          const isActive = active === type;
          return (
            <TouchableOpacity
              key={type}
              onPress={() => onChange(type)}
              style={[styles.toggleBtn, isActive && { backgroundColor: Colors.primary }]}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.toggleText, 
                  isActive 
                    ? { color: Colors.textInverse, fontWeight: '700' } 
                    : { color: Colors.textSecondary, fontWeight: '500' },
                  { fontSize: 13 }
                ]}
              >
                {type === "PETTY_CASH" ? "Petty Cash" : "Site Overheads"}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
    );
});

const TransactionRow = React.memo(({ item }: { item: CashTransaction }) => {
  const { colors: Colors, spacing: Spacing, typography: Typography, borderRadius: BorderRadius } = useTheme();
  const styles = useMemo(() => getStyles(Colors, Spacing, BorderRadius), [Colors, Spacing, BorderRadius]);
  const isDebit = item.type === "DEBIT";
  const txDate = item.recorded_at || item.transaction_date || item.created_at;
  let dateStr = "—";
  if (txDate) {
    try {
      const d = new Date(txDate);
      if (!isNaN(d.getTime())) {
        dateStr = format(d, "dd MMM, HH:mm");
      }
    } catch (e) {
      dateStr = "—";
    }
  }
  
  return (
    <View style={[styles.txRow, { borderBottomColor: Colors.border }]}>
      <View style={styles.txIconContainer}>
        <View style={[styles.txIcon, { backgroundColor: isDebit ? Colors.error + '15' : Colors.success + '15' }]}>
            <Ionicons 
                name={isDebit ? "arrow-down-outline" : "arrow-up-outline"} 
                size={20} 
                color={isDebit ? Colors.error : Colors.success} 
            />
        </View>
      </View>

      <View style={styles.txInfo}>
        <View style={styles.txTopRow}>
            <Text style={[styles.txPurpose, { color: Colors.text, ...Typography.subtitle }]} numberOfLines={1}>
            {item.purpose || item.description || "Transaction"}
            </Text>
            <Text
                style={[
                    styles.txAmount,
                    isDebit ? styles.textError : styles.textSuccess,
                    { fontWeight: '700', fontSize: 16 },
                ]}
            >
                {isDebit ? "−" : "+"}
                {formatCurrency(item.amount)}
            </Text>
        </View>

        <View style={styles.txMetaRow}>
            <Text style={[styles.txMeta, { color: Colors.textMuted, fontSize: 11 }]}>
                {dateStr} • {item.recorded_by || item.created_by || "System"}
            </Text>
            {item.transaction_id && (
                <Text style={[styles.txRefId, { color: Colors.textMuted, fontSize: 9 }]}>
                    #{item.transaction_id.slice(-6).toUpperCase()}
                </Text>
            )}
        </View>
      </View>
    </View>
  );
});

// --------------------------------------------------------
// MAIN COMPONENT
// --------------------------------------------------------

export default function SiteFundsScreen() {
  const router = useRouter();
  const { selectedProject } = useProject();
  const { colors: Colors, spacing: Spacing, typography: Typography, borderRadius: BorderRadius, isDark } = useTheme();
  
  const [activeFundType, setActiveFundType] = useState<FundType>("PETTY_CASH");
  const [categories, setCategories] = useState<CashCategory[]>([]);
  const [transactions, setTransactions] = useState<CashTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState({ amount: "", purpose: "" });

  const styles = useMemo(() => getStyles(Colors, Spacing, BorderRadius), [Colors, Spacing, BorderRadius]);

  // Server-driven selection matching names
  const currentCategory = useMemo(() => {
    // Priority 1: Match by specific name patterns
    const target = categories.find((cat) => {
      const name = cat.category_name.toLowerCase();
      if (activeFundType === "PETTY_CASH") return name.includes("petty");
      return name.includes("ovh") || name.includes("overhead") || name.includes("site expense");
    });
    
    // Priority 2: If none found, but categories exist, pick first (safety fallback)
    return target || categories[0] || null;
  }, [categories, activeFundType]);

  const syncFunds = useCallback(
    async (isSilent = false) => {
      if (!selectedProject?.project_id) {
        setLoading(false);
        return;
      }
      if (!isSilent) setLoading(true);

      try {
        const summary = await cashApi.getSummary(selectedProject.project_id);
        const freshCats = summary.categories || [];
        setCategories(freshCats);

        // Find matching category for the active tab to load its transactions
        const target = freshCats.find((cat) => {
          const name = cat.category_name.toLowerCase();
          if (activeFundType === "PETTY_CASH") return name.includes("petty");
          return name.includes("ovh") || name.includes("overhead");
        }) || freshCats[0];

        if (target) {
          const txRes = await cashApi.listTransactions(
            selectedProject.project_id,
            {
              category_id: target.category_id,
              limit: 50,
            },
          );
          setTransactions(txRes.items as CashTransaction[]);
        } else {
          setTransactions([]);
        }
      } catch (err: unknown) {
        console.error("[SiteFunds] sync error:", err);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedProject?.project_id, activeFundType],
  );

  useFocusEffect(
    useCallback(() => {
      syncFunds();
    }, [syncFunds]),
  );

  useEffect(() => {
    if (selectedProject?.project_id) {
      syncFunds(true);
    }
  }, [activeFundType, selectedProject?.project_id, syncFunds]);

  if (!selectedProject) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
        <StatusBar barStyle={isDark ? "light-content" : "dark-content"} />
        <ScreenHeader title="Site Funds" />
        <View style={styles.emptyState}>
          <View style={[styles.emptyIconCircle, { backgroundColor: Colors.surface }]}>
            <Ionicons name="business-outline" size={48} color={Colors.primary} />
          </View>
          <Text style={[styles.emptyTitle, { color: Colors.text, ...Typography.heading2 }]}>No Project Selected</Text>
          <Text style={[styles.emptySubtext, { color: Colors.textMuted, ...Typography.body }]}>
            Please select an active project to view operational cash ledgers and record site expenses.
          </Text>
          <Button
            title="Select Project"
            onPress={() => router.push("/(admin)/select-project")}
            style={{ marginTop: Spacing.lg, paddingHorizontal: 40 }}
          />
        </View>
      </SafeAreaView>
    );
  }

  const handleRecordExpense = async () => {
    if (!currentCategory || !selectedProject) return;
    const amount = parseFloat(formData.amount);
    if (!amount || amount <= 0) return Alert.alert("Invalid amount");
    if (formData.purpose.trim().length < 3)
      return Alert.alert("Description too short");

    setSubmitting(true);
    try {
      const idempotencyKey = `tx-${Date.now()}`;
      await cashApi.createTransaction(
        selectedProject.project_id,
        {
          category_id: currentCategory.category_id,
          amount,
          type: "DEBIT",
          purpose: formData.purpose.trim(),
        },
        idempotencyKey,
      );
      setModalVisible(false);
      setFormData({ amount: "", purpose: "" });
      syncFunds(true);
      Alert.alert("Success", "Expense logged successfully.");
    } catch (err: unknown) {
      console.error("[SiteFunds] create error:", err);
      Alert.alert("Error", "Failed to log transaction. Check permissions or balance.");
    } finally {
      setSubmitting(false);
    }
  };

  const renderHeader = () => (
    <View style={styles.headerStack}>
      {currentCategory ? (
        <Card variant="elevated" padding="none" style={styles.summaryCard}>
            <View style={[styles.summaryPrimary, { backgroundColor: Colors.surface }]}>
                <Text style={[styles.summaryLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Available Balance</Text>
                <Text
                    style={[
                    styles.summaryValue,
                    currentCategory.is_negative && styles.textError,
                    { color: Colors.text, ...Typography.heading1, fontSize: 32 }
                    ]}
                >
                    {formatCurrency(currentCategory.cash_in_hand)}
                </Text>
                
                {(currentCategory.is_negative || currentCategory.threshold_breached) && (
                    <View style={styles.flagContainer}>
                        {currentCategory.is_negative && (
                        <View style={[styles.flagPill, { backgroundColor: Colors.error }]}>
                            <Ionicons name="alert-circle" size={12} color="white" />
                            <Text style={[styles.flagText, { fontSize: 10, fontWeight: '700' }]}>DEFICIT</Text>
                        </View>
                        )}
                        {currentCategory.threshold_breached && (
                        <View style={[styles.flagPill, { backgroundColor: Colors.warning }]}>
                            <Ionicons name="warning" size={12} color="white" />
                            <Text style={[styles.flagText, { fontSize: 10, fontWeight: '700' }]}>LOW BALANCE</Text>
                        </View>
                        )}
                    </View>
                )}
            </View>

            <View style={[styles.summarySecondary, { borderTopWidth: 1, borderTopColor: Colors.border }]}>
                <View style={styles.metaRow}>
                    <View style={styles.metaCol}>
                        <Text style={[styles.metaLabel, { color: Colors.textMuted, fontSize: 10 }]}>ALLOCATED</Text>
                        <Text style={[styles.metaValue, { color: Colors.text, fontSize: 14 }]}>
                            {formatCurrency(currentCategory.allocation_total)}
                        </Text>
                    </View>
                    <View style={[styles.metaDivider, { backgroundColor: Colors.border }]} />
                    <View style={styles.metaCol}>
                        <Text style={[styles.metaLabel, { color: Colors.textMuted, fontSize: 10 }]}>USED</Text>
                        <Text style={[styles.metaValue, { color: Colors.error, fontSize: 14 }]}>
                            {formatCurrency(currentCategory.allocation_total - currentCategory.cash_in_hand)}
                        </Text>
                    </View>
                </View>
            </View>
        </Card>
      ) : loading ? (
        <View style={[styles.placeholderCard, { backgroundColor: Colors.surface }]}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : (
        <Card variant="elevated" padding="lg" style={styles.summaryCard}>
          <Text style={[styles.summaryLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Fund Data</Text>
          <Text style={[styles.summaryValue, styles.textError, { ...Typography.heading1 }]}>Not Configured</Text>
          <Text style={[styles.emptySubtext, { color: Colors.textMuted, ...Typography.body }]}>
            No fund allocation found for this project. Contact Admin to initialize.
          </Text>
        </Card>
      )}

      <View style={styles.actionRow}>
        <Button
            title="Record Expense"
            onPress={() => setModalVisible(true)}
            variant="primary"
            size="lg"
            disabled={!currentCategory || currentCategory.is_negative}
            style={styles.recordBtn}
            icon={<Ionicons name="add" size={20} color={Colors.textInverse} />}
        />
      </View>

      <View style={styles.sectionHeader}>
        <Text style={[styles.sectionTitle, { color: Colors.textSecondary, ...Typography.overline }]}>Transaction History</Text>
        <Ionicons name="filter-outline" size={16} color={Colors.textMuted} />
      </View>
    </View>
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: Colors.background }]}>
      <StatusBar barStyle={isDark ? "light-content" : "dark-content"} />
      <ScreenHeader title="Site Funds" />
      
      <FundToggle active={activeFundType} onChange={setActiveFundType} />

      <FlatList
        data={transactions}
        keyExtractor={(item) => item.transaction_id || item.id || Math.random().toString()}
        renderItem={({ item }) => <TransactionRow item={item} />}
        ListHeaderComponent={renderHeader}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => syncFunds(true)}
            tintColor={Colors.primary}
          />
        }
        ListEmptyComponent={
          !loading ? (
            <View style={styles.ledgerEmpty}>
              <View style={[styles.emptyIconCircle, { backgroundColor: Colors.surface, opacity: 0.5 }]}>
                <Ionicons name="receipt-outline" size={32} color={Colors.textMuted} />
              </View>
              <Text style={[styles.emptyTitle, { color: Colors.text, ...Typography.subtitle }]}>
                No transactions yet
              </Text>
              <Text style={[styles.emptySubtext, { color: Colors.textMuted, ...Typography.body, marginTop: 4 }]}>
                All expenditures will appear here.
              </Text>
            </View>
          ) : null
        }
      />

      <Modal visible={modalVisible} transparent animationType="fade">
        <View style={styles.modalOverlay}>
          <BlurView intensity={20} style={StyleSheet.absoluteFill} />
          <View style={[styles.modalSheet, { backgroundColor: Colors.surface }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: Colors.text, ...Typography.heading2 }]}>Record Expense</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)} style={styles.closeBtn}>
                <Ionicons name="close" size={20} color={Colors.textSecondary} />
              </TouchableOpacity>
            </View>
            
            <View style={[styles.modalBadge, { backgroundColor: Colors.primary + '15' }]}>
                <Text style={{ color: Colors.primary, fontSize: 11, fontWeight: '700' }}>
                    FROM: {activeFundType === "PETTY_CASH" ? "PETTY CASH" : "SITE OVERHEADS"}
                </Text>
            </View>

            <View style={styles.field}>
              <Text style={[styles.label, { color: Colors.textSecondary, ...Typography.caption }]}>Amount (₹)</Text>
              <TextInput
                style={[styles.input, { backgroundColor: Colors.background, borderColor: Colors.border, color: Colors.text, fontSize: 28, fontWeight: '700' }]}
                value={formData.amount}
                onChangeText={(t) =>
                  setFormData({
                    ...formData,
                    amount: t.replace(/[^0-9.]/g, ""),
                  })
                }
                keyboardType="decimal-pad"
                autoFocus
                placeholder="0.00"
                placeholderTextColor={Colors.textMuted}
              />
            </View>
            
            <View style={styles.field}>
              <Text style={[styles.label, { color: Colors.textSecondary, ...Typography.caption }]}>Description / Purpose</Text>
              <TextInput
                style={[styles.input, { height: 80, backgroundColor: Colors.background, borderColor: Colors.border, color: Colors.text, ...Typography.body, textAlignVertical: 'top' }]}
                value={formData.purpose}
                onChangeText={(t) => setFormData({ ...formData, purpose: t })}
                placeholder="What was this spent on?"
                placeholderTextColor={Colors.textMuted}
                multiline
              />
            </View>
            
            <View style={styles.modalActions}>
              <Button
                title="Save Transaction"
                variant="primary"
                onPress={handleRecordExpense}
                loading={submitting}
                style={{ flex: 1, height: 55 }}
              />
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const getStyles = (Colors: any, Spacing: any, BorderRadius: any) => StyleSheet.create({
  container: { flex: 1 },
  toggleWrapper: {
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  toggleTrack: {
    flexDirection: "row",
    padding: 4,
    borderRadius: 12,
    borderWidth: 1,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 12,
    alignItems: "center",
    borderRadius: 10,
  },
  toggleText: {
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  headerStack: { 
    paddingHorizontal: Spacing.lg, 
    paddingBottom: Spacing.md 
  },
  summaryCard: {
    marginTop: Spacing.sm,
    borderRadius: 20,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: Colors.border,
  },
  summaryPrimary: {
    padding: Spacing.xl,
    alignItems: 'center',
  },
  summarySecondary: {
    flexDirection: 'row',
    padding: Spacing.md,
    backgroundColor: Colors.background,
  },
  summaryLabel: { 
    marginBottom: 8,
    letterSpacing: 1,
  },
  summaryValue: {
    fontWeight: '800',
  },
  metaRow: {
    flex: 1,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
  },
  metaCol: {
    alignItems: 'center',
    flex: 1,
  },
  metaDivider: {
    width: 1,
    height: '60%',
    opacity: 0.5,
  },
  metaLabel: { 
    marginBottom: 4,
    letterSpacing: 0.5,
  },
  metaValue: { 
    fontWeight: "700" 
  },
  flagContainer: {
    marginTop: 12,
    flexDirection: "row",
    gap: 8,
  },
  flagPill: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    gap: 4,
  },
  flagText: { color: "white" },
  actionRow: {
    marginTop: Spacing.lg,
    marginBottom: Spacing.xl,
  },
  recordBtn: {
    borderRadius: 14,
    height: 55,
    shadowColor: Colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: Spacing.md,
  },
  sectionTitle: {
    letterSpacing: 1,
  },
  listContent: {
    paddingBottom: 100,
  },
  txRow: {
    flexDirection: 'row',
    paddingVertical: Spacing.lg,
    paddingHorizontal: Spacing.lg,
    alignItems: 'center',
  },
  txIconContainer: {
    marginRight: Spacing.md,
  },
  txIcon: {
    width: 44,
    height: 44,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  txInfo: {
    flex: 1,
  },
  txTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 2,
  },
  txPurpose: { 
    flex: 1, 
    marginRight: 8,
    fontWeight: '600',
  },
  txMetaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  txAmount: {
  },
  txMeta: { 
    opacity: 0.8,
  },
  txRefId: {
    fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace',
    opacity: 0.5,
  },
  textError: { color: Colors.error },
  textSuccess: { color: Colors.success },
  ledgerEmpty: {
    alignItems: "center",
    paddingVertical: 80,
  },
  emptyIconCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: Spacing.md,
  },
  placeholderCard: {
    height: 180,
    justifyContent: "center",
    borderRadius: 20,
    marginBottom: Spacing.md,
  },
  emptyState: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: Spacing.xl,
  },
  emptyTitle: {
    marginTop: Spacing.md,
    textAlign: "center",
  },
  emptySubtext: {
    marginTop: 12,
    textAlign: "center",
    opacity: 0.7,
    lineHeight: 20,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "flex-end",
  },
  modalSheet: {
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    padding: Spacing.xl,
    paddingBottom: 50,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.md,
  },
  closeBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.background,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalTitle: {
    fontWeight: '800',
  },
  modalBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginBottom: Spacing.lg,
  },
  field: { marginBottom: Spacing.lg },
  label: {
    marginBottom: 8,
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  input: {
    borderRadius: 14,
    padding: Spacing.lg,
    borderWidth: 1,
  },
  modalActions: {
    marginTop: Spacing.md,
  },
});
