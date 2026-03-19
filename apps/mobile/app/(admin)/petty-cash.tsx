// ============================================================
// Site Funds Screen — Unified Petty Cash + Site Overheads
// ============================================================
// GROUND RULE: ZERO client-side math.
// Every numeric value and every boolean flag is consumed
// directly from the server response. No arithmetic, no
// threshold comparisons, no derived fields on the client.
//
// PERFORMANCE RULE: The ledger uses FlatList, not ScrollView+map.
// The API's `category_id` query param is used so the server
// filters — never the client. Only rows for the active category
// are fetched; switching tabs triggers a fresh fetch.
// ============================================================

import React, {
  useState,
  useCallback,
  useMemo,
  memo,
} from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ListRenderItem,
  TouchableOpacity,
  Modal,
  TextInput,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Platform,
} from "react-native";
import { useFocusEffect } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { format } from "date-fns";

import ScreenHeader from "../../components/ScreenHeader";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import {
  Colors,
  Spacing,
  Shadows,
  BorderRadius,
  FontSizes,
} from "../../constants/theme";
import { useProject } from "../../contexts/ProjectContext";
import { cashApi } from "../../services/apiClient";
import type { CashCategory } from "../../services/apiClient";

// ============================================================
// LOCAL TYPES
// ============================================================

type FundType = "petty" | "ovh";

/**
 * Shape of a single ledger row as returned by
 * `GET /api/projects/:id/cash-transactions`.
 * The `items: any[]` from the API is narrowed to this type
 * at the single fetch boundary in `fetchTransactions`.
 */
export interface CashTransaction {
  id: string;
  category_id: string;
  amount: number;
  type: "DEBIT" | "CREDIT";
  purpose: string;
  recorded_by: string;
  recorded_at: string;
}

interface ExpenseFormData {
  amount: string;
  purpose: string;
}

// ============================================================
// HELPERS — pure display utilities, ZERO calculations
// ============================================================

/** Format a server-provided number as ₹ INR string. */
const formatINR = (value: number): string =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);

// ============================================================
// SUB-COMPONENTS — all memoized to prevent re-renders on
//                 parent state changes unrelated to their props
// ============================================================

// ── Tab Switcher ──────────────────────────────────────────

interface TabSwitcherProps {
  active: FundType;
  onChange: (t: FundType) => void;
}

const TabSwitcher = memo(function TabSwitcher({
  active,
  onChange,
}: TabSwitcherProps) {
  return (
    <View style={styles.tabRow}>
      {(["petty", "ovh"] as FundType[]).map((type) => {
        const isActive = active === type;
        return (
          <TouchableOpacity
            key={type}
            style={[styles.tab, isActive && styles.tabActive]}
            onPress={() => onChange(type)}
            activeOpacity={0.8}
            accessibilityRole="tab"
            accessibilityState={{ selected: isActive }}
          >
            <Ionicons
              name={type === "petty" ? "cash-outline" : "business-outline"}
              size={16}
              color={isActive ? Colors.white : Colors.textSecondary}
            />
            <Text style={[styles.tabLabel, isActive && styles.tabLabelActive]}>
              {type === "petty" ? "Petty Cash" : "Site Overheads"}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
});

// ── Summary Card ──────────────────────────────────────────

interface SummaryCardProps {
  category: CashCategory;
}

/**
 * Renders server-provided values only.
 * All warning badges are driven by server boolean flags —
 * `category.is_negative` and `category.threshold_breached`.
 * No arithmetic is performed here.
 */
const SummaryCard = memo(function SummaryCard({ category }: SummaryCardProps) {
  const hasWarning = category.is_negative || category.threshold_breached;

  return (
    <Card variant="elevated" padding="lg" style={styles.summaryCard}>
      {/* Primary balance figure */}
      <View style={styles.cashInHandBlock}>
        <Text style={styles.cashLabel}>Cash in Hand</Text>
        <Text
          style={[
            styles.cashValue,
            category.is_negative && styles.valueDanger,
          ]}
        >
          {formatINR(category.cash_in_hand)}
        </Text>
      </View>

      <View style={styles.divider} />

      {/* Allocation total — server-provided scalar, no math */}
      <View style={styles.metaRow}>
        <Text style={styles.metaLabel}>Total Allocation</Text>
        <Text style={styles.metaValue}>
          {formatINR(category.allocation_total)}
        </Text>
      </View>

      {/* Server-driven warning badges */}
      {hasWarning && (
        <View style={styles.flagRow}>
          {category.is_negative && (
            <View style={[styles.flag, styles.flagDanger]}>
              <Ionicons name="alert-circle" size={13} color={Colors.white} />
              <Text style={styles.flagText}>Negative Balance</Text>
            </View>
          )}
          {category.threshold_breached && (
            <View style={[styles.flag, styles.flagWarning]}>
              <Ionicons name="trending-down" size={13} color={Colors.white} />
              <Text style={styles.flagText}>Below Threshold</Text>
            </View>
          )}
        </View>
      )}
    </Card>
  );
});

// ── Transaction Item ──────────────────────────────────────
//
// Design spec (from task):
//   Left  — date pill (DD MMM) stacked above truncated purpose text
//   Right — signed amount in bold, type badge below
//
// Wrapped in React.memo: FlatList calls renderItem on every
// re-render of the parent by default. memo() ensures the cell
// only re-renders when its `tx` prop reference changes.

interface TransactionItemProps {
  tx: CashTransaction;
}

const TransactionItem = memo(function TransactionItem({
  tx,
}: TransactionItemProps) {
  const isDebit = tx.type === "DEBIT";
  const dateStr = format(new Date(tx.recorded_at), "dd MMM");
  const timeStr = format(new Date(tx.recorded_at), "h:mm a");

  return (
    <View style={styles.txRow}>
      {/* LEFT: date + purpose */}
      <View style={styles.txLeft}>
        <View style={styles.txDatePill}>
          <Text style={styles.txDateText}>{dateStr}</Text>
        </View>
        <View style={styles.txBody}>
          <Text style={styles.txPurpose} numberOfLines={2}>
            {tx.purpose}
          </Text>
          <Text style={styles.txMeta}>
            {tx.recorded_by} · {timeStr}
          </Text>
        </View>
      </View>

      {/* RIGHT: amount */}
      <View style={styles.txRight}>
        <Text
          style={[
            styles.txAmount,
            isDebit ? styles.txAmountDebit : styles.txAmountCredit,
          ]}
        >
          {isDebit ? "−" : "+"}
          {formatINR(tx.amount)}
        </Text>
        <View
          style={[
            styles.txTypeBadge,
            isDebit ? styles.txTypeBadgeDebit : styles.txTypeBadgeCredit,
          ]}
        >
          <Text style={styles.txTypeText}>
            {isDebit ? "DEBIT" : "CREDIT"}
          </Text>
        </View>
      </View>
    </View>
  );
});

// ── Ledger Empty State ────────────────────────────────────

interface LedgerEmptyProps {
  fundLabel: string;
}

const LedgerEmpty = memo(function LedgerEmpty({ fundLabel }: LedgerEmptyProps) {
  return (
    <Card style={styles.emptyCard} padding="lg">
      <Ionicons name="receipt-outline" size={44} color={Colors.textMuted} />
      <Text style={styles.emptyTitle}>No transactions yet</Text>
      <Text style={styles.emptySubtext}>
        Tap &quot;Record Expense&quot; to log the first{" "}
        {fundLabel.toLowerCase()} entry.
      </Text>
    </Card>
  );
});

// ── Expense Entry Modal ───────────────────────────────────
//
// SECURITY DESIGN:
//   • No type toggle — `type` is never a prop or state here.
//     The screen hardcodes `type: "DEBIT"` in handleSubmit.
//   • No category picker — category_id is auto-bound to the
//     active tab's categoryId in the screen, never user-selected.
//   • Submit is disabled until amount is parseable AND purpose
//     has at least 5 trimmed characters.

const PURPOSE_MIN_CHARS = 5;

interface ExpenseModalProps {
  visible: boolean;
  fundLabel: string;
  submitting: boolean;
  formData: ExpenseFormData;
  onChangeForm: (data: ExpenseFormData) => void;
  onClose: () => void;
  onSubmit: () => void;
}

const ExpenseModal = memo(function ExpenseModal({
  visible,
  fundLabel,
  submitting,
  formData,
  onChangeForm,
  onClose,
  onSubmit,
}: ExpenseModalProps) {
  // Derived validation state — computed inside the presentation
  // component so the parent's handleSubmit stays the authority
  // and this is purely for real-time UI feedback.
  const purposeLen = formData.purpose.trim().length;
  const purposeValid = purposeLen >= PURPOSE_MIN_CHARS;
  const amountValid =
    formData.amount.trim().length > 0 &&
    !isNaN(parseFloat(formData.amount)) &&
    parseFloat(formData.amount) > 0;
  const canSubmit = !submitting && amountValid && purposeValid;

  /**
   * Strip any character that is not a digit or the first decimal
   * point. This prevents '.' alone, multiple dots, and any letter
   * from ever reaching the amount state.
   */
  const handleAmountChange = (raw: string) => {
    // Allow digits and at most one decimal point
    const cleaned = raw.replace(/[^0-9.]/g, "");
    const parts = cleaned.split(".");
    // Collapse multiple dots: keep only first fragment + one optional decimal
    const sanitised =
      parts.length > 2
        ? `${parts[0]}.${parts.slice(1).join("")}`
        : cleaned;
    onChangeForm({ ...formData, amount: sanitised });
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          {/* Handle bar */}
          <View style={styles.sheetHandle} />

          {/* Header */}
          <View style={styles.sheetHeader}>
            <Text style={styles.sheetTitle}>Record Expense</Text>
            <TouchableOpacity
              onPress={onClose}
              style={styles.sheetClose}
              accessibilityLabel="Close modal"
              hitSlop={{ top: 8, right: 8, bottom: 8, left: 8 }}
            >
              <Ionicons name="close" size={22} color={Colors.textSecondary} />
            </TouchableOpacity>
          </View>

          {/* Security context label — no type toggle ever rendered */}
          <Text style={styles.sheetSubtitle}>
            {fundLabel} · Debit Entry Only
          </Text>

          {/* ── Amount ── */}
          <View style={styles.field}>
            <Text style={styles.fieldLabel}>Amount (₹)</Text>
            <TextInput
              style={[
                styles.input,
                formData.amount.length > 0 && !amountValid && styles.inputError,
              ]}
              value={formData.amount}
              onChangeText={handleAmountChange}
              placeholder="0"
              placeholderTextColor={Colors.placeholder}
              keyboardType="decimal-pad"
              returnKeyType="next"
              autoFocus
            />
            {formData.amount.length > 0 && !amountValid && (
              <Text style={styles.fieldHintError}>
                Enter a valid amount greater than zero.
              </Text>
            )}
          </View>

          {/* ── Purpose ── */}
          <View style={styles.field}>
            <View style={styles.fieldLabelRow}>
              <Text style={styles.fieldLabel}>Purpose</Text>
              {/* Live char count — only appears once the user starts typing */}
              {formData.purpose.length > 0 && (
                <Text
                  style={[
                    styles.fieldCharCount,
                    purposeValid
                      ? styles.fieldCharCountOk
                      : styles.fieldCharCountWarn,
                  ]}
                >
                  {purposeLen}/{PURPOSE_MIN_CHARS} min
                </Text>
              )}
            </View>
            <TextInput
              style={[styles.input, styles.inputMultiline]}
              value={formData.purpose}
              onChangeText={(text) =>
                onChangeForm({ ...formData, purpose: text })
              }
              placeholder="What was this expense for?"
              placeholderTextColor={Colors.placeholder}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
              returnKeyType="done"
            />
            {!purposeValid && formData.purpose.length > 0 && (
              <Text style={styles.fieldHintError}>
                Purpose must be at least {PURPOSE_MIN_CHARS} characters.
              </Text>
            )}
          </View>

          {/* ── Actions ── */}
          <View style={styles.sheetActions}>
            <Button
              title="Cancel"
              onPress={onClose}
              variant="outline"
              style={styles.sheetBtn}
              disabled={submitting}
            />
            <Button
              title={submitting ? "Saving…" : "Save Expense"}
              onPress={onSubmit}
              variant="primary"
              loading={submitting}
              style={styles.sheetBtn}
              disabled={!canSubmit}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
});

// ============================================================
// SCREEN
// ============================================================

export default function SiteFundsScreen() {
  // -- Tab state
  const [activeFundType, setActiveFundType] = useState<FundType>("petty");

  // -- Summary data (all categories, fetched once on focus)
  const [categories, setCategories] = useState<CashCategory[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(true);

  // -- Transaction ledger data (refetched when active category changes)
  const [transactions, setTransactions] = useState<CashTransaction[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null); // reserved for future infinite scroll
  const [txLoading, setTxLoading] = useState(false);

  // -- Pull-to-refresh
  const [refreshing, setRefreshing] = useState(false);

  // -- Expense modal
  const [modalVisible, setModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState<ExpenseFormData>({
    amount: "",
    purpose: "",
  });

  // -- Project context
  const { selectedProject } = useProject();

  // --------------------------------------------------------
  // DERIVED — pure selection, zero math
  // --------------------------------------------------------

  /**
   * Locate the CashCategory for the active tab by matching
   * the server-returned category_name. All numeric and boolean
   * fields on the result come unmodified from the server.
   */
  const currentCategory = useMemo<CashCategory | undefined>(() => {
    return categories.find((cat) => {
      const name = cat.category_name.toLowerCase();
      if (activeFundType === "petty") return name.includes("petty");
      return name.includes("ovh") || name.includes("overhead");
    });
  }, [categories, activeFundType]);

  const categoryId = currentCategory?.category_id;

  const fundLabel =
    activeFundType === "petty" ? "Petty Cash" : "Site Overheads";

  // --------------------------------------------------------
  // DATA FETCHING
  // --------------------------------------------------------

  /**
   * Fetch the cash summary (all categories).
   * Called once on screen focus; categories are stable across
   * tab switches so we don't re-fetch them on every tab change.
   */
  const fetchSummary = useCallback(
    async (isRefresh = false) => {
      if (!selectedProject?.project_id) return;
      if (!isRefresh) setSummaryLoading(true);

      try {
        const res = await cashApi.getSummary(selectedProject.project_id);
        setCategories(res.categories ?? []);
      } catch (err) {
        console.error("[SiteFunds] fetchSummary error:", err);
        Alert.alert(
          "Error",
          "Failed to load fund summary. Please pull to refresh."
        );
      } finally {
        setSummaryLoading(false);
      }
    },
    [selectedProject?.project_id]
  );

  /**
   * Fetch transactions for the currently active category.
   *
   * KEY ARCHITECTURE NOTE:
   * We pass `category_id` directly to the API so the server filters.
   * We do NOT fetch all 100 transactions and filter client-side.
   * This keeps the payload small and the filtering authoritative.
   */
  const fetchTransactions = useCallback(
    async (catId: string, isRefresh = false) => {
      if (!selectedProject?.project_id || !catId) return;
      if (!isRefresh) setTxLoading(true);

      try {
        const res = await cashApi.listTransactions(selectedProject.project_id, {
          category_id: catId,   // ← server-side filter, not client-side
          limit: 50,
        });

        // Narrow `items: any[]` to `CashTransaction[]` at the fetch boundary.
        // This is the single point where the wire type meets the local interface.
        setTransactions((res.items as CashTransaction[]) ?? []);
        setNextCursor(res.next_cursor);
      } catch (err) {
        console.error("[SiteFunds] fetchTransactions error:", err);
        Alert.alert(
          "Error",
          "Failed to load transactions. Please pull to refresh."
        );
      } finally {
        setTxLoading(false);
        setRefreshing(false);
      }
    },
    [selectedProject?.project_id]
  );

  /**
   * Full refresh: summary first (to get fresh category_ids),
   * then transactions for the now-resolved category.
   */
  const refreshAll = useCallback(
    async (isRefresh = false) => {
      if (!selectedProject?.project_id) return;

      // Fetch summary afresh to get current categories
      if (!isRefresh) setSummaryLoading(true);
      try {
        const sumRes = await cashApi.getSummary(selectedProject.project_id);
        const freshCategories = sumRes.categories ?? [];
        setCategories(freshCategories);

        // Resolve the active category from the freshly-fetched list
        const freshCategory = freshCategories.find((cat) => {
          const name = cat.category_name.toLowerCase();
          if (activeFundType === "petty") return name.includes("petty");
          return name.includes("ovh") || name.includes("overhead");
        });

        if (freshCategory) {
          await fetchTransactions(freshCategory.category_id, isRefresh);
        }
      } catch (err) {
        console.error("[SiteFunds] refreshAll error:", err);
        Alert.alert("Error", "Failed to refresh. Please try again.");
      } finally {
        setSummaryLoading(false);
        setRefreshing(false);
      }
    },
    [selectedProject?.project_id, activeFundType, fetchTransactions]
  );

  // Initial load on screen focus
  useFocusEffect(
    useCallback(() => {
      refreshAll();
    }, [refreshAll])
  );

  // Refetch transactions whenever the active category changes
  // (summary categories are already in state; no need to re-fetch them)
  React.useEffect(() => {
    if (categoryId) {
      fetchTransactions(categoryId);
    } else {
      // Category not yet resolved (summary still loading) — clear stale rows
      setTransactions([]);
    }
  }, [categoryId, fetchTransactions]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    refreshAll(true);
  }, [refreshAll]);

  // --------------------------------------------------------
  // MODAL HANDLERS
  // --------------------------------------------------------

  const openModal = useCallback(() => {
    setFormData({ amount: "", purpose: "" });
    setModalVisible(true);
  }, []);

  const closeModal = useCallback(() => {
    setModalVisible(false);
    setFormData({ amount: "", purpose: "" });
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!selectedProject?.project_id || !categoryId) {
      Alert.alert("Error", "No project or category selected.");
      return;
    }

    const parsed = parseFloat(formData.amount);
    if (isNaN(parsed) || parsed <= 0) {
      Alert.alert("Invalid Amount", "Please enter a valid positive amount.");
      return;
    }

    if (!formData.purpose.trim()) {
      Alert.alert(
        "Missing Purpose",
        "Please describe what this expense was for."
      );
      return;
    }

    setSubmitting(true);

    try {
      // Idempotency key: project + category + timestamp
      const idempotencyKey = `${selectedProject.project_id}-${categoryId}-${Date.now()}`;

      // POST raw values ONLY. The server performs all
      // balance updates and flag recalculations server-side.
      await cashApi.createTransaction(
        selectedProject.project_id,
        {
          category_id: categoryId,
          amount: parsed,
          type: "DEBIT",
          purpose: formData.purpose.trim(),
        },
        idempotencyKey
      );

      // Refresh both summary (updated cash_in_hand) and ledger
      await refreshAll(true);
      closeModal();
      Alert.alert("Recorded", "Expense saved successfully.");
    } catch (err: any) {
      console.error("[SiteFunds] createTransaction error:", err);
      Alert.alert(
        "Error",
        err?.data?.detail ?? "Failed to record expense. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }, [
    selectedProject?.project_id,
    categoryId,
    formData,
    refreshAll,
    closeModal,
  ]);

  // --------------------------------------------------------
  // FLATLIST CONFIGURATION
  // --------------------------------------------------------

  /**
   * `renderItem` is stable (no inline arrow functions) so FlatList
   * can bail out of unnecessary re-renders via its own internal memo.
   */
  const renderItem = useCallback<ListRenderItem<CashTransaction>>(
    ({ item }) => <TransactionItem tx={item} />,
    []
  );

  const keyExtractor = useCallback(
    (item: CashTransaction) => item.id,
    []
  );

  const ItemSeparator = useCallback(
    () => <View style={styles.separator} />,
    []
  );

  /**
   * ListHeaderComponent — injects the Balance Card, CTA button,
   * and ledger section heading INSIDE the FlatList scroll region.
   * This avoids the forbidden ScrollView-inside-FlatList nesting.
   */
  const ListHeader = useMemo(
    () => (
      <View style={styles.listHeader}>
        {/* Balance Card */}
        {summaryLoading ? (
          <View style={styles.skeletonCard}>
            <ActivityIndicator color={Colors.primary} />
          </View>
        ) : currentCategory ? (
          <SummaryCard category={currentCategory} />
        ) : (
          <Card style={styles.emptyCard} padding="lg">
            <Ionicons
              name="folder-open-outline"
              size={40}
              color={Colors.textMuted}
            />
            <Text style={styles.emptyTitle}>No {fundLabel} category</Text>
            <Text style={styles.emptySubtext}>
              This project has no {fundLabel.toLowerCase()} category
              configured.
            </Text>
          </Card>
        )}

        {/* Record Expense CTA */}
        <Button
          title="Record Expense"
          onPress={openModal}
          variant="primary"
          size="lg"
          fullWidth
          icon={
            <Ionicons
              name="add-circle-outline"
              size={20}
              color={Colors.white}
            />
          }
          disabled={!currentCategory || summaryLoading}
        />

        {/* Ledger section heading */}
        <View style={styles.ledgerHeadingRow}>
          <Text style={styles.ledgerHeading}>{fundLabel} Ledger</Text>
          {txLoading && (
            <ActivityIndicator
              size="small"
              color={Colors.primary}
              style={styles.ledgerSpinner}
            />
          )}
        </View>
      </View>
    ),
    // Re-compute when any of these change:
    [
      summaryLoading,
      currentCategory,
      fundLabel,
      openModal,
      txLoading,
    ]
  );

  const ListEmpty = useMemo(
    () =>
      txLoading ? null : <LedgerEmpty fundLabel={fundLabel} />,
    [txLoading, fundLabel]
  );

  // --------------------------------------------------------
  // RENDER: Full-screen loading (first paint only)
  // --------------------------------------------------------

  if (summaryLoading && categories.length === 0) {
    return (
      <View style={styles.container}>
        <ScreenHeader title="Site Funds" />
        <View style={styles.tabHost}>
          <TabSwitcher active={activeFundType} onChange={setActiveFundType} />
        </View>
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Loading funds…</Text>
        </View>
      </View>
    );
  }

  // --------------------------------------------------------
  // RENDER: Main
  // --------------------------------------------------------

  return (
    <View style={styles.container}>
      <ScreenHeader title="Site Funds" />

      {/* Sticky segmented control — lives OUTSIDE FlatList */}
      <View style={styles.tabHost}>
        <TabSwitcher active={activeFundType} onChange={setActiveFundType} />
      </View>

      {/*
        FlatList replaces the former ScrollView+map pattern.
        Performance props:
          - renderItem: stable callback ref (useCallback, no inline arrow)
          - keyExtractor: stable callback ref
          - removeClippedSubviews: Android memory optimisation
          - maxToRenderPerBatch: controls batching of off-screen renders
          - windowSize: visible window = 5 × viewport height
          - ListHeaderComponent: balance card + CTA inside the scroll region
          - ListEmptyComponent: empty state, rendered by FlatList itself
          - ItemSeparatorComponent: thin rule between rows
      */}
      <FlatList<CashTransaction>
        data={transactions}
        renderItem={renderItem}
        keyExtractor={keyExtractor}
        ListHeaderComponent={ListHeader}
        ListEmptyComponent={ListEmpty}
        ItemSeparatorComponent={ItemSeparator}
        contentContainerStyle={styles.flatListContent}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={Colors.primary}
            colors={[Colors.primary]}
          />
        }
        removeClippedSubviews={Platform.OS === "android"}
        maxToRenderPerBatch={10}
        windowSize={5}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      />

      {/* Expense Entry Bottom Sheet */}
      <ExpenseModal
        visible={modalVisible}
        fundLabel={fundLabel}
        submitting={submitting}
        formData={formData}
        onChangeForm={setFormData}
        onClose={closeModal}
        onSubmit={handleSubmit}
      />
    </View>
  );
}

// ============================================================
// STYLES — all tokens from theme.ts, zero magic values
// ============================================================

const styles = StyleSheet.create({
  // ── Root
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },

  // ── Full-screen loading
  loadingWrap: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    gap: Spacing.md,
  },
  loadingText: {
    fontSize: FontSizes.md,
    color: Colors.textMuted,
  },

  // ── Sticky Tab Host
  tabHost: {
    backgroundColor: Colors.white,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    ...Shadows.sm,
  },
  tabRow: {
    flexDirection: "row",
    backgroundColor: Colors.background,
    borderRadius: BorderRadius.lg,
    borderWidth: 1,
    borderColor: Colors.border,
    overflow: "hidden",
  },
  tab: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.xs,
    paddingVertical: Spacing.sm + 2,
    paddingHorizontal: Spacing.sm,
  },
  tabActive: {
    backgroundColor: Colors.primary,
  },
  tabLabel: {
    fontSize: FontSizes.sm,
    fontWeight: "600",
    color: Colors.textSecondary,
  },
  tabLabelActive: {
    color: Colors.white,
  },

  // ── FlatList content container
  flatListContent: {
    paddingBottom: Spacing.xxl,
  },

  // ── ListHeaderComponent wrapper
  listHeader: {
    padding: Spacing.md,
    gap: Spacing.md,
  },

  // ── Skeleton placeholder while summary loads
  skeletonCard: {
    height: 140,
    borderRadius: BorderRadius.lg,
    backgroundColor: Colors.divider,
    justifyContent: "center",
    alignItems: "center",
    ...Shadows.sm,
  },

  // ── Summary Card
  summaryCard: {},
  cashInHandBlock: {
    alignItems: "center",
    paddingVertical: Spacing.md,
    gap: Spacing.xs,
  },
  cashLabel: {
    fontSize: FontSizes.sm,
    color: Colors.textMuted,
    fontWeight: "500",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  cashValue: {
    fontSize: FontSizes.xxxl,
    fontWeight: "700",
    color: Colors.text,
  },
  valueDanger: {
    color: Colors.error,
  },
  divider: {
    height: 1,
    backgroundColor: Colors.border,
    marginVertical: Spacing.sm,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: Spacing.xs,
  },
  metaLabel: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
    fontWeight: "500",
  },
  metaValue: {
    fontSize: FontSizes.sm,
    fontWeight: "700",
    color: Colors.text,
  },
  flagRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: Spacing.xs,
    marginTop: Spacing.md,
    paddingTop: Spacing.md,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  flag: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.xs,
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    borderRadius: BorderRadius.full,
  },
  flagDanger: {
    backgroundColor: Colors.error,
  },
  flagWarning: {
    backgroundColor: Colors.warning,
  },
  flagText: {
    fontSize: FontSizes.xs,
    fontWeight: "700",
    color: Colors.white,
  },

  // ── Ledger section heading row
  ledgerHeadingRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
  },
  ledgerHeading: {
    fontSize: FontSizes.lg,
    fontWeight: "700",
    color: Colors.text,
  },
  ledgerSpinner: {
    marginLeft: Spacing.xs,
  },

  // ── Transaction Item
  // Layout: [date pill | purpose + meta] [amount + type badge]
  txRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    backgroundColor: Colors.white,
    gap: Spacing.sm,
  },
  txLeft: {
    flex: 1,
    flexDirection: "row",
    alignItems: "flex-start",
    gap: Spacing.sm,
  },
  txDatePill: {
    backgroundColor: Colors.infoLight,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.sm,
    paddingVertical: Spacing.xs,
    minWidth: 52,
    alignItems: "center",
    marginTop: 2, // optical alignment with first text line
  },
  txDateText: {
    fontSize: FontSizes.xs,
    fontWeight: "700",
    color: Colors.accent,
    textAlign: "center",
  },
  txBody: {
    flex: 1,
    gap: 2,
  },
  txPurpose: {
    fontSize: FontSizes.sm,
    fontWeight: "500",
    color: Colors.text,
    lineHeight: FontSizes.sm * 1.4,
  },
  txMeta: {
    fontSize: FontSizes.xs,
    color: Colors.textMuted,
  },
  txRight: {
    alignItems: "flex-end",
    gap: Spacing.xs,
  },
  txAmount: {
    fontSize: FontSizes.md,
    fontWeight: "700",
  },
  txAmountDebit: {
    color: Colors.error,
  },
  txAmountCredit: {
    color: Colors.success,
  },
  txTypeBadge: {
    paddingHorizontal: Spacing.xs + 2,
    paddingVertical: 2,
    borderRadius: BorderRadius.sm,
  },
  txTypeBadgeDebit: {
    backgroundColor: Colors.errorLight,
  },
  txTypeBadgeCredit: {
    backgroundColor: Colors.successLight,
  },
  txTypeText: {
    fontSize: 9,
    fontWeight: "700",
    letterSpacing: 0.5,
    color: Colors.textSecondary,
  },

  // ── Row separator
  separator: {
    height: 1,
    backgroundColor: Colors.border,
    marginLeft: Spacing.md, // aligns with txBody, not the date pill
  },

  // ── Empty states
  emptyCard: {
    alignItems: "center",
    gap: Spacing.sm,
  },
  emptyTitle: {
    fontSize: FontSizes.md,
    fontWeight: "600",
    color: Colors.textMuted,
  },
  emptySubtext: {
    fontSize: FontSizes.sm,
    color: Colors.textMuted,
    textAlign: "center",
  },

  // ── Expense Bottom Sheet Modal
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.45)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: Colors.white,
    borderTopLeftRadius: BorderRadius.xl,
    borderTopRightRadius: BorderRadius.xl,
    padding: Spacing.lg,
    paddingBottom: Platform.OS === "ios" ? Spacing.xxl : Spacing.lg,
    ...Shadows.lg,
    gap: Spacing.md,
  },
  sheetHandle: {
    alignSelf: "center",
    width: 36,
    height: 4,
    borderRadius: BorderRadius.full,
    backgroundColor: Colors.divider,
    marginBottom: Spacing.xs,
  },
  sheetHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  sheetTitle: {
    fontSize: FontSizes.xl,
    fontWeight: "700",
    color: Colors.text,
  },
  sheetClose: {
    padding: Spacing.xs,
  },
  sheetSubtitle: {
    fontSize: FontSizes.sm,
    color: Colors.textSecondary,
  },
  field: {
    gap: Spacing.xs,
  },
  fieldLabelRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  fieldLabel: {
    fontSize: FontSizes.sm,
    fontWeight: "600",
    color: Colors.text,
  },
  fieldCharCount: {
    fontSize: FontSizes.xs,
    fontWeight: "500",
  },
  fieldCharCountWarn: {
    color: Colors.warning,
  },
  fieldCharCountOk: {
    color: Colors.success,
  },
  fieldHintError: {
    fontSize: FontSizes.xs,
    color: Colors.error,
    marginTop: 2,
  },
  input: {
    borderWidth: 1,
    borderColor: Colors.inputBorder,
    borderRadius: BorderRadius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm + 2,
    fontSize: FontSizes.md,
    color: Colors.text,
    backgroundColor: Colors.inputBg,
  },
  inputError: {
    borderColor: Colors.error,
    backgroundColor: Colors.errorLight,
  },
  inputMultiline: {
    minHeight: 80,
    paddingTop: Spacing.sm + 2,
  },
  sheetActions: {
    flexDirection: "row",
    gap: Spacing.md,
  },
  sheetBtn: {
    flex: 1,
  },
});
