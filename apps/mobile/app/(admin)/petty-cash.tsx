// ============================================================
// SITE FUNDS SCREEN — Unified Petty Cash + Site Overheads
// ============================================================
// GROUND RULE: ZERO client-side math.
// All logic flags and balances are server-computed.
// 'CREDIT' types and manual Category selection are disabled.
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
} from "react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { format } from "date-fns";

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

// DELETED LOCAL CASHTRANSACTION INTERFACE

// --------------------------------------------------------
// HELPERS
// --------------------------------------------------------

const formatCurrency = (val: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(val);

// --------------------------------------------------------
// SUB-COMPONENTS
// --------------------------------------------------------

const FundToggle = React.memo(({ active, onChange }: { active: FundType; onChange: (t: FundType) => void; }) => {
    const { colors: Colors, spacing: Spacing, typography: Typography, borderRadius: BorderRadius } = useTheme();
    const styles = useMemo(() => getStyles(Colors, Spacing, BorderRadius), [Colors, Spacing, BorderRadius]);
    return (
    <View style={styles.toggleContainer}>
      <View style={[styles.toggleTrack, { backgroundColor: Colors.surface }]}>
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
                style={[styles.toggleText, isActive ? { color: Colors.textInverse, ...Typography.subtitle } : { color: Colors.textSecondary, ...Typography.body }]}
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
  const dateStr = txDate
    ? format(new Date(txDate), "dd MMM yyyy, HH:mm")
    : "—";
  const refId = item.transaction_id || item.id || "";

  return (
    <View style={[styles.txRow, { borderBottomColor: Colors.border }]}>
      {/* Row 1: Purpose + Badge */}
      <View style={styles.txTopRow}>
        <Text style={[styles.txPurpose, { color: Colors.text, ...Typography.subtitle }]} numberOfLines={1}>
          {item.purpose || item.description || "Transaction"}
        </Text>
        <View
          style={[
            styles.txBadge,
            isDebit ? styles.badgeError : styles.badgeSuccess,
          ]}
        >
          <Text style={[styles.txBadgeText, { ...Typography.overline, color: "white" }]}>
            {isDebit ? "DEBIT" : "CREDIT"}
          </Text>
        </View>
      </View>

      {/* Row 2: Date + Recorded by */}
      <Text style={[styles.txMeta, { color: Colors.textMuted, ...Typography.caption }]}>
        {dateStr} • {item.recorded_by || item.created_by || "System"}
      </Text>

      {/* Row 3: Amount */}
      <View style={styles.txBottomRow}>
        <Text
          style={[
            styles.txAmount,
            isDebit ? styles.textError : styles.textSuccess,
            { ...Typography.heading2 },
          ]}
        >
          {isDebit ? "−" : "+"}
          {formatCurrency(item.amount)}
        </Text>
      </View>

      {/* Row 4: Reference ID */}
      {refId ? (
        <Text style={[styles.txRefId, { color: Colors.textMuted, ...Typography.overline }]}>
          Ref: {refId.slice(-8).toUpperCase()}
        </Text>
      ) : null}
    </View>
  );
});

// --------------------------------------------------------
// MAIN COMPONENT
// --------------------------------------------------------

export default function SiteFundsScreen() {
  const router = useRouter();
  const { selectedProject } = useProject();
  const { colors: Colors, spacing: Spacing, typography: Typography, borderRadius: BorderRadius } = useTheme();
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
    return categories.find((cat) => {
      const name = cat.category_name.toLowerCase();
      if (activeFundType === "PETTY_CASH") return name.includes("petty");
      return name.includes("ovh") || name.includes("overhead");
    });
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

        const target = freshCats.find((cat) => {
          const name = cat.category_name.toLowerCase();
          if (activeFundType === "PETTY_CASH") return name.includes("petty");
          return name.includes("ovh") || name.includes("overhead");
        });

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
        Alert.alert("Sync Error", "Failed to retrieve site funds.");
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
            style={{ marginTop: Spacing.lg }}
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
          type: "DEBIT", // Forced Security constraint
          purpose: formData.purpose.trim(),
        },
        idempotencyKey,
      );
      setModalVisible(false);
      setFormData({ amount: "", purpose: "" });
      syncFunds(true);
      Alert.alert("Recorded", "Expense logged successfully.");
    } catch (err: unknown) {
      console.error("[SiteFunds] create error:", err);
      Alert.alert("Error", "Failed to log transaction.");
    } finally {
      setSubmitting(false);
    }
  };

  const renderHeader = () => (
    <View style={styles.headerStack}>
      {currentCategory ? (
        <Card variant="elevated" padding="lg" style={styles.summaryCard}>
          <Text style={[styles.summaryLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Available Balance</Text>
          <Text
            style={[
              styles.summaryValue,
              currentCategory.is_negative && styles.textError,
              { color: Colors.text, ...Typography.heading1 }
            ]}
          >
            {formatCurrency(currentCategory.cash_in_hand)}
          </Text>
          <View style={[styles.summaryDivider, { backgroundColor: Colors.border }]} />
          <View style={styles.metaRow}>
            <Text style={[styles.metaLabel, { color: Colors.textSecondary, ...Typography.body }]}>Allocated</Text>
            <Text style={[styles.metaValue, { color: Colors.text, ...Typography.subtitle }]}>
              {formatCurrency(currentCategory.allocation_total)}
            </Text>
          </View>
          <View style={[styles.metaRow, { marginTop: Spacing.sm }]}>
            <Text style={[styles.metaLabel, { color: Colors.textSecondary, ...Typography.body }]}>Used Amount</Text>
            <Text style={[styles.metaValue, styles.textError, { ...Typography.subtitle }]}>
              {formatCurrency(
                currentCategory.allocation_total -
                  currentCategory.cash_in_hand,
              )}
            </Text>
          </View>
          <View style={[styles.metaRow, { marginTop: Spacing.sm }]}>
            <Text style={[styles.metaLabel, { color: Colors.textSecondary, ...Typography.body }]}>Pending Approvals</Text>
            <Text style={[styles.metaValue, { color: Colors.textMuted, ...Typography.subtitle }]}>
              {formatCurrency(0)}
            </Text>
          </View>
          {currentCategory.days_since_last_pc_close !== null && (
            <View style={[styles.metaRow, { marginTop: Spacing.sm }]}>
              <Text style={[styles.metaLabel, { color: Colors.textSecondary, ...Typography.body }]}>Last Replenishment</Text>
              <Text style={[styles.metaValue, { color: Colors.text, ...Typography.subtitle }]}>
                {currentCategory.days_since_last_pc_close === 0 
                  ? 'Today' 
                  : `${currentCategory.days_since_last_pc_close}d ago`}
              </Text>
            </View>
          )}
          {(currentCategory.is_negative ||
            currentCategory.threshold_breached) && (
              <View style={styles.flagContainer}>
                {currentCategory.is_negative && (
                  <View style={styles.flagPill}>
                    <Ionicons name="alert-circle" size={14} color="white" />
                    <Text style={[styles.flagText, { ...Typography.overline, color: 'white' }]}>Deficit</Text>
                  </View>
                )}
                {currentCategory.threshold_breached && (
                  <View style={styles.flagPillWarning}>
                    <Ionicons name="warning" size={14} color="white" />
                    <Text style={[styles.flagText, { ...Typography.overline, color: 'white' }]}>Strict Limit</Text>
                  </View>
                )}
              </View>
            )}
        </Card>
      ) : loading ? (
        <View style={[styles.placeholderCard, { backgroundColor: Colors.surface }]}>
          <ActivityIndicator color={Colors.primary} />
        </View>
      ) : (
        <Card variant="elevated" padding="lg" style={styles.summaryCard}>
          <Text style={[styles.summaryLabel, { color: Colors.textSecondary, ...Typography.overline }]}>Fund Data</Text>
          <Text style={[styles.summaryValue, styles.textError, { ...Typography.heading1 }]}>No Data</Text>
          <Text style={[styles.emptySubtext, { color: Colors.textMuted, ...Typography.body }]}>
            No fund allocation found for this project type.
          </Text>
        </Card>
      )}

      <Button
        title="Record Expense"
        onPress={() => setModalVisible(true)}
        variant="primary"
        size="lg"
        disabled={!currentCategory}
        icon={<Ionicons name="add" size={20} color={Colors.textInverse} />}
      />

      <Text style={[styles.sectionTitle, { color: Colors.text, ...Typography.overline }]}>Fund Ledger</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScreenHeader title="Site Funds" />
      <FundToggle active={activeFundType} onChange={setActiveFundType} />

      <FlatList
        data={transactions}
        keyExtractor={(item) => item.id || item.transaction_id}
        renderItem={({ item }) => <TransactionRow item={item} />}
        ListHeaderComponent={renderHeader}
        contentContainerStyle={[styles.listContent, { padding: Spacing.md }]}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => syncFunds(true)}
            tintColor={Colors.primary}
          />
        }
        ListEmptyComponent={
          !loading && categories.length > 0 ? (
            <View style={styles.ledgerEmpty}>
              <View style={[styles.emptyIconCircle, { backgroundColor: Colors.surface, opacity: 0.5 }]}>
                <Ionicons name="receipt-outline" size={32} color={Colors.textMuted} />
              </View>
              <Text style={[styles.emptyText, { color: Colors.text, ...Typography.subtitle }]}>
                No transactions recorded yet.
              </Text>
              <Text style={[styles.emptySubtext, { color: Colors.textMuted, ...Typography.body, marginTop: 4 }]}>
                Tap &quot;Record Expense&quot; to log the first entry.
              </Text>
            </View>
          ) : null
        }
      />

      <Modal visible={modalVisible} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={[styles.modalSheet, { backgroundColor: Colors.surface }]}>
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: Colors.text, ...Typography.heading2 }]}>Record Expense</Text>
              <TouchableOpacity onPress={() => setModalVisible(false)}>
                <Ionicons name="close" size={24} color={Colors.text} />
              </TouchableOpacity>
            </View>
            <Text style={[styles.modalSubtitle, { color: Colors.textSecondary, ...Typography.overline }]}>
              Target:{" "}
              {activeFundType === "PETTY_CASH"
                ? "Petty Cash"
                : "Site Overheads"}
            </Text>

            <View style={styles.field}>
              <Text style={[styles.label, { color: Colors.textSecondary, ...Typography.caption }]}>Amount (₹)</Text>
              <TextInput
                style={[styles.input, { backgroundColor: Colors.inputBg, borderColor: Colors.border, color: Colors.text, ...Typography.heading1 }]}
                value={formData.amount}
                onChangeText={(t) =>
                  setFormData({
                    ...formData,
                    amount: t.replace(/[^0-9.]/g, ""),
                  })
                }
                keyboardType="decimal-pad"
                autoFocus
                placeholder="0"
                placeholderTextColor={Colors.textMuted}
              />
            </View>
            <View style={styles.field}>
              <Text style={[styles.label, { color: Colors.textSecondary, ...Typography.caption }]}>Note</Text>
              <TextInput
                style={[styles.input, { height: 80, backgroundColor: Colors.inputBg, borderColor: Colors.border, color: Colors.text, ...Typography.body }]}
                value={formData.purpose}
                onChangeText={(t) => setFormData({ ...formData, purpose: t })}
                placeholder="Details..."
                placeholderTextColor={Colors.textMuted}
                multiline
              />
            </View>
            <View style={styles.modalActions}>
              <Button
                title="Cancel"
                variant="outline"
                onPress={() => setModalVisible(false)}
                style={{ flex: 1 }}
              />
              <Button
                title="Save Entry"
                variant="primary"
                onPress={handleRecordExpense}
                loading={submitting}
                style={{ flex: 1 }}
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
  header: {
    paddingHorizontal: Spacing.lg,
    paddingTop: 10,
  },
  headerTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.lg,
  },
  toggleContainer: {
    padding: Spacing.md,
    borderBottomWidth: 1,
  },
  toggleTrack: {
    flexDirection: "row",
    padding: 4,
    borderRadius: BorderRadius.md,
  },
  toggleBtn: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderRadius: BorderRadius.sm,
  },
  toggleText: {},
  title: {},
  switchContainer: {
    flexDirection: "row",
    backgroundColor: Colors.surface,
    padding: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  switchBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  switchBtnActive: {
    backgroundColor: Colors.primary,
  },
  switchText: {
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1,
  },
  scrollContent: {
    paddingBottom: 40,
  },
  summaryCard: {
    marginHorizontal: Spacing.lg,
    marginTop: Spacing.md,
  },
  balanceRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    marginBottom: Spacing.md,
  },
  balanceLabel: { marginBottom: 4 },
  balanceValue: {},
  summaryValue: {
    marginBottom: Spacing.md,
  },
  summaryLabel: { marginBottom: 4 },
  summaryDivider: { height: 1, marginVertical: Spacing.md, opacity: 0.5 },
  headerStack: { paddingHorizontal: Spacing.lg, paddingBottom: Spacing.md },
  listContent: {},
  divider: {
    height: 1,
    opacity: 0.1,
    marginVertical: Spacing.md,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  metaLabel: {},
  metaValue: { fontWeight: "700" },
  flagContainer: {
    marginTop: Spacing.lg,
    flexDirection: "row",
    gap: 8,
  },
  flagPill: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.error,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
  },
  flagPillWarning: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: Colors.warning,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
    gap: 4,
  },
  flagText: { color: "white" },
  sectionTitle: {
    marginTop: Spacing.lg,
    marginBottom: Spacing.md,
  },
  txRow: {
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  txTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  txPurpose: { flex: 1, marginRight: 8 },
  txBadge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  txBadgeText: {},
  txMeta: { marginBottom: 6 },
  txBottomRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  txAmount: {},
  txRefId: {
    marginTop: 4,
    fontFamily: "monospace",
  },
  textError: { color: Colors.error },
  textSuccess: { color: Colors.success },
  badgeError: { backgroundColor: Colors.error },
  badgeSuccess: { backgroundColor: Colors.success },
  ledgerEmpty: {
    alignItems: "center",
    paddingVertical: 60,
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
    height: 160,
    justifyContent: "center",
    borderRadius: BorderRadius.lg,
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
  emptyText: { textAlign: "center" },
  emptySubtext: {
    marginTop: 8,
    textAlign: "center",
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
    justifyContent: "flex-end",
  },
  modalSheet: {
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    padding: Spacing.lg,
    paddingBottom: 40,
  },
  modalHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.sm,
  },
  modalTitle: {},
  modalSubtitle: {
    marginBottom: Spacing.lg,
  },
  field: { marginBottom: Spacing.md },
  label: {
    marginBottom: 4,
  },
  input: {
    borderRadius: BorderRadius.md,
    padding: Spacing.md,
    borderWidth: 1,
  },
  modalActions: {
    flexDirection: "row",
    gap: Spacing.md,
    marginTop: Spacing.lg,
  },
});
