import { useCallback, useState, useEffect } from "react";

export type ColumnType =
  | "rownum"
  | "text"
  | "number"
  | "date"
  | "percent"
  | "select"
  | "autocomplete"
  | "indicator"
  | "readonly";

export type GanttColumnDef = {
  id: string;
  label: string;
  width: number;
  minWidth: number;
  visible: boolean;
  order: number;
  editable: boolean;
  type: ColumnType;
  /** The ScheduleTask field this column maps to */
  field: string;
  /** Whether this column is part of the default visible set */
  defaultVisible: boolean;
};

const STORAGE_KEY = "tac-gantt-column-config";

/**
 * Default column definitions matching the MS Project–style task sheet.
 * Order determines initial left-to-right position.
 */
export const DEFAULT_COLUMNS: GanttColumnDef[] = [
  { id: "rownum",          label: "#",              width: 40,  minWidth: 32,  visible: true,  order: 0,  editable: false, type: "rownum",       field: "",                defaultVisible: true  },
  { id: "wbs_code",        label: "WBS",            width: 64,  minWidth: 48,  visible: true,  order: 1,  editable: false, type: "readonly",     field: "wbs_code",        defaultVisible: true  },
  { id: "task_name",       label: "Task Name",      width: 220, minWidth: 120, visible: true,  order: 2,  editable: true,  type: "text",         field: "task_name",       defaultVisible: true  },
  { id: "indicators",      label: "⚡",              width: 40,  minWidth: 32,  visible: true,  order: 3,  editable: false, type: "indicator",    field: "",                defaultVisible: true  },
  { id: "duration",        label: "Duration",       width: 72,  minWidth: 56,  visible: true,  order: 4,  editable: true,  type: "number",       field: "scheduled_duration", defaultVisible: true  },
  { id: "start",           label: "Start",          width: 96,  minWidth: 80,  visible: true,  order: 5,  editable: true,  type: "date",         field: "scheduled_start", defaultVisible: true  },
  { id: "finish",          label: "Finish",         width: 96,  minWidth: 80,  visible: true,  order: 6,  editable: true,  type: "date",         field: "scheduled_finish",defaultVisible: true  },
  { id: "percent_complete", label: "% Complete",    width: 72,  minWidth: 56,  visible: true,  order: 7,  editable: true,  type: "percent",      field: "percent_complete", defaultVisible: true },
  { id: "predecessors",    label: "Predecessors",   width: 110, minWidth: 80,  visible: true,  order: 8,  editable: true,  type: "autocomplete", field: "predecessors",     defaultVisible: true  },
  { id: "successors",      label: "Successors",     width: 110, minWidth: 80,  visible: false, order: 9,  editable: false, type: "readonly",     field: "successors",      defaultVisible: false },
  { id: "resource",        label: "Resource",       width: 100, minWidth: 72,  visible: true,  order: 10, editable: true,  type: "autocomplete", field: "assignee_ids",    defaultVisible: true  },
  { id: "baseline_start",  label: "BL Start",       width: 96,  minWidth: 72,  visible: false, order: 11, editable: false, type: "readonly",     field: "baseline_start",  defaultVisible: false },
  { id: "baseline_finish", label: "BL Finish",      width: 96,  minWidth: 72,  visible: false, order: 12, editable: false, type: "readonly",     field: "baseline_finish", defaultVisible: false },
  { id: "start_variance",  label: "Start Var",     width: 80,  minWidth: 56,  visible: false, order: 13, editable: false, type: "readonly",     field: "start_variance",  defaultVisible: false },
  { id: "finish_variance", label: "Finish Var",    width: 80,  minWidth: 56,  visible: false, order: 14, editable: false, type: "readonly",     field: "finish_variance", defaultVisible: false },
  { id: "total_slack",     label: "Total Float",    width: 80,  minWidth: 56,  visible: false, order: 15, editable: false, type: "readonly",     field: "total_slack",     defaultVisible: false },
  { id: "free_slack",      label: "Free Float",     width: 80,  minWidth: 56,  visible: false, order: 16, editable: false, type: "readonly",     field: "free_slack",      defaultVisible: false },
  { id: "constraint_type", label: "Constraint",     width: 96,  minWidth: 72,  visible: false, order: 17, editable: true,  type: "select",       field: "constraint_type", defaultVisible: false },
  { id: "constraint_date", label: "Cst. Date",      width: 96,  minWidth: 72,  visible: false, order: 18, editable: true,  type: "date",         field: "constraint_date", defaultVisible: false },
  { id: "task_status",     label: "Status",         width: 88,  minWidth: 64,  visible: true,  order: 19, editable: true,  type: "select",       field: "task_status",     defaultVisible: true  },
];

function loadFromStorage(): GanttColumnDef[] | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as GanttColumnDef[];
    // Validate structure — must have same IDs as defaults
    const defaultIds = new Set(DEFAULT_COLUMNS.map(c => c.id));
    if (!parsed.every(c => defaultIds.has(c.id))) return null;
    // Merge any new columns from defaults that don't exist in stored config
    const storedIds = new Set(parsed.map(c => c.id));
    const missing = DEFAULT_COLUMNS.filter(c => !storedIds.has(c.id));
    return [...parsed, ...missing];
  } catch {
    return null;
  }
}

function saveToStorage(columns: GanttColumnDef[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(columns));
  } catch {
    // localStorage may be full or unavailable — silently ignore
  }
}

/**
 * Hook managing Gantt task sheet column configuration.
 * Provides resize, reorder, show/hide, and persistence.
 */
export function useColumnConfig() {
  const [columns, setColumns] = useState<GanttColumnDef[]>(() => {
    return loadFromStorage() ?? [...DEFAULT_COLUMNS];
  });

  // Persist on every change
  useEffect(() => {
    saveToStorage(columns);
  }, [columns]);

  /** Sorted visible columns */
  const visibleColumns = columns
    .filter(c => c.visible)
    .sort((a, b) => a.order - b.order);

  /** Total width of all visible columns */
  const totalWidth = visibleColumns.reduce((sum, c) => sum + c.width, 0);

  const resizeColumn = useCallback((columnId: string, newWidth: number) => {
    setColumns(prev =>
      prev.map(c =>
        c.id === columnId
          ? { ...c, width: Math.max(c.minWidth, newWidth) }
          : c
      )
    );
  }, []);

  const toggleColumn = useCallback((columnId: string) => {
    setColumns(prev =>
      prev.map(c =>
        c.id === columnId ? { ...c, visible: !c.visible } : c
      )
    );
  }, []);

  const reorderColumn = useCallback((columnId: string, newOrder: number) => {
    setColumns(prev => {
      const sorted = [...prev].sort((a, b) => a.order - b.order);
      const idx = sorted.findIndex(c => c.id === columnId);
      if (idx === -1) return prev;

      const [moved] = sorted.splice(idx, 1);
      sorted.splice(newOrder, 0, moved);

      return sorted.map((c, i) => ({ ...c, order: i }));
    });
  }, []);

  const resetToDefaults = useCallback(() => {
    setColumns([...DEFAULT_COLUMNS]);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // silently ignore
    }
  }, []);

  const showAllColumns = useCallback(() => {
    setColumns(prev => prev.map(c => ({ ...c, visible: true })));
  }, []);

  const showDefaultsOnly = useCallback(() => {
    setColumns(prev =>
      prev.map(c => ({ ...c, visible: c.defaultVisible }))
    );
  }, []);

  return {
    columns,
    visibleColumns,
    totalWidth,
    resizeColumn,
    toggleColumn,
    reorderColumn,
    resetToDefaults,
    showAllColumns,
    showDefaultsOnly,
  };
}
