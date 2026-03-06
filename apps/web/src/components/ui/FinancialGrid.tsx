'use client';

import React, { useCallback, useMemo, useRef, useState } from 'react';
import { AgGridReact } from 'ag-grid-react';
import type { ColDef, GridReadyEvent, CellValueChangedEvent } from 'ag-grid-community';
import { AllCommunityModule, ModuleRegistry } from 'ag-grid-community';

// Register AG Grid Community modules
ModuleRegistry.registerModules([AllCommunityModule]);

// ── Indian currency formatter ───────────────────────────────────────────
export function formatINR(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '';
  const num = typeof value === 'string' ? parseFloat(value) : value;
  if (isNaN(num)) return '';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(num);
}

// ── Currency cell renderer ──────────────────────────────────────────────
function CurrencyCellRenderer(params: { value: number }) {
  return <span className="text-right w-full block">{formatINR(params.value)}</span>;
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
  onValidationChange?: (allValid: boolean, validations: RowValidation[]) => void;
  height?: string;
  editable?: boolean;
  showSrNo?: boolean;
  /** Custom row validation function */
  validateRow?: (data: T, rowIndex: number) => RowValidation;
  className?: string;
  getRowId?: (params: any) => string;
  readOnly?: boolean;
  domLayout?: 'normal' | 'autoHeight' | 'print';
  loading?: boolean;
  quickFilterText?: string;
}

export default function FinancialGrid<T extends any>({
  rowData,
  columnDefs,
  onCellValueChanged,
  onGridReady,
  onValidationChange,
  height = '400px',
  editable = true,
  showSrNo = true,
  validateRow,
  className = '',
  getRowId,
  readOnly = false,
  domLayout = 'normal',
  loading = false,
  quickFilterText = '',
}: FinancialGridProps<T>) {
  const gridRef = useRef<AgGridReact<T>>(null);
  const [invalidCount, setInvalidCount] = useState(0);

  // Auto-incrementing Sr No column
  const srNoCol: ColDef<T> = useMemo(() => ({
    headerName: 'Sr',
    valueGetter: (params) => (params.node?.rowIndex ?? 0) + 1,
    width: 60,
    pinned: 'left',
    editable: false,
    cellStyle: { textAlign: 'center', fontWeight: 600, color: '#94a3b8' },
  }), []);

  // Merge columns
  const allColumns = useMemo(() => {
    const cols = showSrNo ? [srNoCol, ...columnDefs] : [...columnDefs];
    return cols.map((col) => ({
      ...col,
      // Default right-align for numeric columns
      cellStyle: col.cellStyle ?? (
        col.type === 'numericColumn'
          ? { textAlign: 'right' }
          : undefined
      ),
    }));
  }, [columnDefs, showSrNo, srNoCol]);

  // Default column definitions
  const defaultColDef = useMemo<ColDef>(() => ({
    resizable: true,
    editable: editable,
    singleClickEdit: false, // Double-click to edit
    sortable: true,
    filter: false,
    cellStyle: {
      fontSize: '13px',
      lineHeight: '1.5',
    },
  }), [editable]);

  // Handle cell value changes with validation
  const handleCellValueChanged = useCallback((event: CellValueChangedEvent<T>) => {
    onCellValueChanged?.(event);

    // Run validation if provided
    if (validateRow && gridRef.current?.api) {
      const validations: RowValidation[] = [];
      let allValid = true;

      gridRef.current.api.forEachNode((node) => {
        if (node.data) {
          const result = validateRow(node.data, node.rowIndex ?? 0);
          validations.push(result);
          if (!result.valid) allValid = false;
        }
      });

      const invalids = validations.filter((v) => !v.valid).length;
      setInvalidCount(invalids);
      onValidationChange?.(allValid, validations);
    }
  }, [onCellValueChanged, onValidationChange, validateRow]);

  return (
    <div className={`financial-grid-container ${className}`}>
      {invalidCount > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 mb-2 rounded-lg text-sm"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>
          <span className="font-semibold">{invalidCount}</span>
          <span>row{invalidCount > 1 ? 's' : ''} with validation errors</span>
        </div>
      )}
      <div style={{ height, width: '100%' }} className="ag-theme-alpine-dark">
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
          tabToNextCell={(params) => params.nextCellPosition || (null as any)}
          suppressClickEdit={readOnly}
          getRowId={getRowId}
          domLayout={domLayout}
          loading={loading}
          quickFilterText={quickFilterText}
        />
      </div>
      <style jsx global>{`
        .ag-theme-alpine-dark {
          --ag-background-color: #0f172a;
          --ag-header-background-color: #1e293b;
          --ag-header-foreground-color: #94a3b8;
          --ag-foreground-color: #e2e8f0;
          --ag-border-color: #334155;
          --ag-row-hover-color: rgba(249, 115, 22, 0.05);
          --ag-selected-row-background-color: rgba(249, 115, 22, 0.1);
          --ag-range-selection-border-color: #f97316;
          --ag-font-size: 13px;
          --ag-row-height: 40px;
          --ag-header-height: 42px;
        }
        .ag-theme-alpine-dark .ag-cell-inline-editing {
          background: #1e293b !important;
          border: 1px solid #f97316 !important;
          border-radius: 4px;
        }
        .ag-theme-alpine-dark .ag-cell-inline-editing input {
          color: #f1f5f9 !important;
          background: #1e293b !important;
        }
      `}</style>
    </div>
  );
}
