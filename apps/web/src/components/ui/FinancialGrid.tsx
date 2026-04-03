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
import { isEnterprise } from "@/lib/features";

// Register AG Grid Community modules
ModuleRegistry.registerModules([AllCommunityModule]);

// ── Indian currency formatter ───────────────────────────────────────────
export function formatINR(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const rawNum = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(rawNum)) return "";

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(rawNum);
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
  getRowId?: (params: { data: T }) => string;
  readOnly?: boolean;
  domLayout?: "normal" | "autoHeight" | "print";
  loading?: boolean;
  quickFilterText?: string;
}

export default function FinancialGrid<T>({
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

  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';

  // Auto-incrementing Sr No column
  const srNoCol: ColDef<T> = useMemo(
    () => ({
      headerName: "Sr",
      valueGetter: (params) => (params.node?.rowIndex ?? 0) + 1,
      width: 60,
      pinned: "left",
      editable: false,
      cellStyle: { textAlign: "center", fontWeight: 600, color: isDark ? "#94a3b8" : "#475569" },
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
        const rowIndex = event.node?.rowIndex ?? 0;
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

      return nextCellPosition || false;
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
    (params: { node: { rowIndex: number | null } | null }) => {
      const validation = rowValidations.get(params.node?.rowIndex ?? 0);
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
        className={`${gridTheme} glass-panel-luxury rounded-[1.5rem] overflow-hidden shadow-2xl transition-all duration-500 border border-white/5`}
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
          suppressColumnVirtualisation={true}
          // Enterprise features - conditionally enabled
          {...(enterpriseEnabled && {
            enableRangeSelection: true,
            enableCellTextSelection: true,
            rowSelection: { mode: "multiRow", checkboxes: false },
          })}
        />
      </div>
    </div>
  );
}
