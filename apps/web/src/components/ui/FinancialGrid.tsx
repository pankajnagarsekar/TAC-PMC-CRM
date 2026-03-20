"use client";

import React, { useCallback, useMemo, useRef, useState } from "react";
import { AgGridReact } from "ag-grid-react";
import { useTheme } from "next-themes";
import type {
  ColDef,
  GridReadyEvent,
  CellValueChangedEvent,
  CellKeyDownEvent,
  TabToNextCellParams,
  CellPosition,
} from "ag-grid-community";
import { AllCommunityModule, ModuleRegistry } from "ag-grid-community";
import { features, isEnterprise } from "@/lib/features";

// Register AG Grid Community modules
ModuleRegistry.registerModules([AllCommunityModule]);

// ── Indian currency formatter ───────────────────────────────────────────
export function formatINR(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const rawNum = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(rawNum)) return "";

  // Guard against -0 and floating point rounding errors near zero
  const num = Math.abs(rawNum) < 0.0001 ? 0 : rawNum;

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

// ── Currency cell renderer ──────────────────────────────────────────────
function CurrencyCellRenderer(params: { value: number }) {
  return (
    <span className="text-right w-full block">{formatINR(params.value)}</span>
  );
}

// ── Validation result type ──────────────────────────────────────────────
export interface RowValidation {
  rowIndex: number;
  valid: boolean;
  errors: string[];
}

// ── Props ───────────────────────────────────────────────────────────────
export interface FinancialGridProps<T> {
  rowData: T[];
  columnDefs: ColDef<T>[];
  onCellValueChanged?: (event: CellValueChangedEvent<T>) => void;
  onGridReady?: (event: GridReadyEvent<T>) => void;
  onValidationChange?: (
    allValid: boolean,
    validations: RowValidation[],
  ) => void;
  height?: string;
  editable?: boolean;
  showSrNo?: boolean;
  /** Custom row validation function */
  validateRow?: (data: T, rowIndex: number) => RowValidation;
  className?: string;
  getRowId?: (params: any) => string;
  readOnly?: boolean;
  domLayout?: "normal" | "autoHeight" | "print";
  loading?: boolean;
  quickFilterText?: string;
}

export default function FinancialGrid<T extends any>({
  rowData,
  columnDefs,
  onCellValueChanged,
  onGridReady,
  onValidationChange,
  height = "400px",
  editable = true,
  showSrNo = true,
  validateRow,
  className = "",
  getRowId,
  readOnly = false,
  domLayout = "normal",
  loading = false,
  quickFilterText = "",
}: FinancialGridProps<T>) {
  const gridRef = useRef<AgGridReact<T>>(null);
  const [invalidCount, setInvalidCount] = useState(0);
  const [rowValidations, setRowValidations] = useState<
    Map<number, RowValidation>
  >(new Map());

  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Auto-incrementing Sr No column
  const srNoCol: ColDef<T> = useMemo(
    () => ({
      headerName: "Sr",
      valueGetter: (params) => (params.node?.rowIndex ?? 0) + 1,
      width: 60,
      pinned: "left",
      editable: false,
      cellStyle: { textAlign: "center", fontWeight: 600, color: isDark ? "#94a3b8" : "#64748b" },
    }),
    [isDark],
  );

  // Merge columns
  const allColumns = useMemo(() => {
    const cols = showSrNo ? [srNoCol, ...columnDefs] : [...columnDefs];
    return cols.map((col) => ({
      ...col,
      // Default right-align for numeric columns
      cellStyle:
        col.cellStyle ??
        (col.type === "numericColumn" ? { textAlign: "right" } : undefined),
    }));
  }, [columnDefs, showSrNo, srNoCol]);

  // Keyboard navigation handler
  const handleKeyDown = useCallback((event: CellKeyDownEvent<T>) => {
    const { event: keyboardEvent, colDef, api } = event;

    if (!keyboardEvent) return;

    const key = (keyboardEvent as KeyboardEvent).key;

    // Enter: move to next row after editing
    if (key === "Enter") {
      if ((event as unknown as { editing?: boolean }).editing) {
        api.stopEditing();
        const rowIndex = event.node.rowIndex ?? 0;
        const colId = colDef.field;
        if (colId) {
          api.ensureIndexVisible(rowIndex + 1);
          api.setFocusedCell(rowIndex + 1, colId);
          api.startEditingCell({ rowIndex: rowIndex + 1, colKey: colId });
        }
      }
    }

    // Escape: cancel editing
    if (key === "Escape") {
      if ((event as unknown as { editing?: boolean }).editing) {
        api.stopEditing(true);
      }
    }
  }, []);

  // Tab navigation handler - moves to next cell
  const tabToNextCell = useCallback(
    (params: TabToNextCellParams): boolean | CellPosition => {
      const { nextCellPosition, editing, api } = params;

      if (editing) {
        api.stopEditing();
      }

      if (nextCellPosition) {
        // Navigate to the next cell position
        api.setFocusedCell(nextCellPosition.rowIndex, nextCellPosition.column);
        if (!editing) {
          api.startEditingCell({
            rowIndex: nextCellPosition.rowIndex,
            colKey: nextCellPosition.column,
          });
        }
        return true;
      }
      // If no next position, allow default tab behavior
      return true;
    },
    [],
  );

  // Default column definitions
  const defaultColDef = useMemo<ColDef>(
    () => ({
      resizable: true,
      editable: editable,
      singleClickEdit: false, // Double-click to edit
      sortable: true,
      filter: false,
      cellStyle: {
        fontSize: "13px",
        lineHeight: "1.5",
      },
      onKeyDown: handleKeyDown,
    }),
    [editable, handleKeyDown],
  );

  // Check if enterprise features are enabled
  const enterpriseEnabled = isEnterprise();

  // Handle cell value changes with validation
  const handleCellValueChanged = useCallback(
    (event: CellValueChangedEvent<T>) => {
      onCellValueChanged?.(event);

      // Run validation if provided
      if (validateRow && gridRef.current?.api) {
        const validations: RowValidation[] = [];
        const newRowValidations = new Map<number, RowValidation>();
        let allValid = true;

        gridRef.current.api.forEachNode((node) => {
          if (node.data) {
            const result = validateRow(node.data, node.rowIndex ?? 0);
            validations.push(result);
            newRowValidations.set(node.rowIndex ?? 0, result);
            if (!result.valid) allValid = false;
          }
        });

        setRowValidations(newRowValidations);
        const invalids = validations.filter((v) => !v.valid).length;
        setInvalidCount(invalids);
        onValidationChange?.(allValid, validations);
      }
    },
    [onCellValueChanged, onValidationChange, validateRow],
  );

  // Get row class based on validation status
  const getRowClass = useCallback(
    (params: any) => {
      const validation = rowValidations.get(params.node.rowIndex);
      if (validation) {
        if (!validation.valid) {
          return "row-invalid";
        }
        return "row-valid";
      }
      return "";
    },
    [rowValidations],
  );

  const gridTheme = isDark ? "ag-theme-quartz-dark" : "ag-theme-quartz";

  return (
    <div className={`financial-grid-container ${className}`}>
      {invalidCount > 0 && (
        <div
          className="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg text-sm"
          style={{
            background: isDark ? "rgba(239,68,68,0.1)" : "rgba(239,68,68,0.05)",
            color: "#ef4444",
            border: "1px solid rgba(239,68,68,0.2)",
          }}
        >
          <span className="font-semibold">{invalidCount}</span>
          <span>row{invalidCount > 1 ? "s" : ""} with validation errors</span>
        </div>
      )}
      <div
        style={{ height, width: "100%" }}
        className={`${gridTheme} glass-panel-luxury dark:glass-panel-luxury rounded-xl overflow-hidden shadow-2xl transition-all duration-500`}
      >
        <AgGridReact<T>
          ref={gridRef}
          rowData={rowData}
          columnDefs={allColumns}
          defaultColDef={defaultColDef}
          onCellValueChanged={handleCellValueChanged}
          onGridReady={onGridReady}
          animateRows={true}
          stopEditingWhenCellsLoseFocus={true}
          enterNavigatesVertically={true}
          enterNavigatesVerticallyAfterEdit={true}
          tabToNextCell={tabToNextCell}
          suppressClickEdit={readOnly}
          getRowId={getRowId}
          getRowClass={getRowClass}
          domLayout={domLayout}
          loading={loading}
          quickFilterText={quickFilterText}
          headerHeight={48}
          rowHeight={44}
          // Enterprise features - conditionally enabled
          {...(enterpriseEnabled && {
            enableRangeSelection: true,
            enableCellTextSelection: true,
            rowSelection: { mode: "multiRow", checkboxes: false },
          })}
        />
      </div>
      <style jsx global>{`
        .ag-theme-quartz-dark, .ag-theme-quartz {
          --ag-background-color: ${isDark ? 'transparent' : '#ffffff'} !important;
          --ag-header-background-color: ${isDark ? 'rgba(30, 41, 59, 0.4)' : 'rgba(241, 245, 249, 0.6)'} !important;
          --ag-header-foreground-color: ${isDark ? '#94a3b8' : '#64748b'} !important;
          --ag-foreground-color: ${isDark ? '#e2e8f0' : '#1e293b'} !important;
          --ag-border-color: ${isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0, 0, 0, 0.05)'} !important;
          --ag-row-hover-color: ${isDark ? 'rgba(249, 115, 22, 0.08)' : 'rgba(249, 115, 22, 0.05)'} !important;
          --ag-selected-row-background-color: ${isDark ? 'rgba(249, 115, 22, 0.15)' : 'rgba(249, 115, 22, 0.1)'} !important;
          --ag-range-selection-border-color: #f97316 !important;
          --ag-font-size: 13px !important;
          --ag-font-family: inherit !important;
          --ag-border-radius: 12px !important;
          --ag-grid-size: 8px !important;
          --ag-list-item-height: 36px !important;
          --ag-cell-horizontal-padding: 24px !important;
        }

        .ag-theme-quartz-dark .ag-header-cell, .ag-theme-quartz .ag-header-cell {
          font-weight: 700 !important;
          letter-spacing: 0.08em !important;
          text-transform: uppercase !important;
          font-size: 10px !important;
          padding-left: 24px !important;
          padding-right: 24px !important;
        }

        .ag-theme-quartz-dark .ag-cell-inline-editing, .ag-theme-quartz .ag-cell-inline-editing {
          background: ${isDark ? '#1e293b' : '#ffffff'} !important;
          border: 1.5px solid #f97316 !important;
          border-radius: 8px !important;
          box-shadow: 0 0 20px rgba(249, 115, 22, 0.3) !important;
        }

        .ag-theme-quartz-dark .ag-cell-inline-editing input, .ag-theme-quartz .ag-cell-inline-editing input {
          color: ${isDark ? '#f8fafc' : '#0f172a'} !important;
          background: transparent !important;
          font-weight: 600 !important;
        }

        /* Row-level validation indicators */
        .ag-theme-quartz-dark .row-invalid, .ag-theme-quartz .row-invalid {
          border-left: 4px solid #ef4444 !important;
        }
        .ag-theme-quartz-dark .row-valid, .ag-theme-quartz .row-valid {
          border-left: 4px solid #10b981 !important;
        }
      `}</style>
    </div>
  );
}
