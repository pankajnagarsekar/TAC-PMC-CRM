import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ──────────────────────────────────────────────────────────────────────────
// Dashboard Layout Store
// Manages draggable widget configuration, order, and column spans per project
// ──────────────────────────────────────────────────────────────────────────

export interface WidgetConfig {
  id: string;          // 'ai_brief' | 'task_ai' | 'timeline' | 'tasks' | etc.
  colSpan: 1 | 2;      // Spans 1 or 2 grid columns
}

export interface DashboardLayoutState {
  layouts: Record<string, WidgetConfig[]>; // Record key is projectId or 'global'
  _hasHydrated: boolean;
  reorderWidgets: (projectId: string, sourceIndex: number, destIndex: number) => void;
  resetToDefault: (projectId: string) => void;
  loadProjectLayout: (projectId: string) => void;
  setLayoutForProject: (projectId: string, layout: WidgetConfig[]) => void;
  setHasHydrated: (state: boolean) => void;
}

export const DEFAULT_LAYOUT: WidgetConfig[] = [
  { id: 'ai_brief',   colSpan: 1 },
  { id: 'task_ai',    colSpan: 1 },
  { id: 'timeline',   colSpan: 2 },
  { id: 'tasks',      colSpan: 1 },
  { id: 'budget',     colSpan: 1 },
  { id: 'calendar',   colSpan: 2 },
  { id: 'log',        colSpan: 1 },
  { id: 'scheduler',  colSpan: 1 },
  { id: 'site_feed',  colSpan: 1 },
];

const migrateLegacyLayout = (projectId: string): WidgetConfig[] | null => {
  if (typeof window === 'undefined') return null;

  const legacyProjectKey = `dashboard_layout_${projectId}`;
  const legacyGlobalKey = 'dashboard_global_layout';

  const savedProject = localStorage.getItem(legacyProjectKey);
  const savedGlobal = localStorage.getItem(legacyGlobalKey);

  const legacyData = savedProject || savedGlobal;
  if (!legacyData) return null;

  try {
    const parsed = JSON.parse(legacyData);
    if (!Array.isArray(parsed)) return null;

    // Filter out S-Curve ('analytics') as it is promoted to Zone 2
    const cleanLegacyIds = (parsed as string[]).filter(id => id !== 'analytics');

    // Build the migrated list
    const migrated: WidgetConfig[] = [];

    // First add legacy ones that are still in our allowed list
    cleanLegacyIds.forEach(id => {
      const def = DEFAULT_LAYOUT.find(item => item.id === id);
      if (def) {
        migrated.push({ id, colSpan: def.colSpan });
      }
    });

    // Make sure new widgets ('ai_brief', 'site_feed') are present
    DEFAULT_LAYOUT.forEach(def => {
      if (!migrated.some(item => item.id === def.id)) {
        migrated.push({ id: def.id, colSpan: def.colSpan });
      }
    });

    // Delete legacy keys so we don't migrate again
    localStorage.removeItem(legacyProjectKey);
    localStorage.removeItem(legacyGlobalKey);

    return migrated;
  } catch (e) {
    console.error('Failed to migrate legacy dashboard layout:', e);
    return null;
  }
};

export const useDashboardLayoutStore = create<DashboardLayoutState>()(
  persist(
    (set, get) => ({
      layouts: {},
      _hasHydrated: false,

      reorderWidgets: (projectId, sourceIndex, destIndex) => {
        const key = projectId || 'global';
        const currentLayout = get().layouts[key] || [...DEFAULT_LAYOUT];
        const newLayout = [...currentLayout];
        const [removed] = newLayout.splice(sourceIndex, 1);
        newLayout.splice(destIndex, 0, removed);

        set((state) => ({
          layouts: {
            ...state.layouts,
            [key]: newLayout,
          },
        }));
      },

      resetToDefault: (projectId) => {
        const key = projectId || 'global';
        set((state) => ({
          layouts: {
            ...state.layouts,
            [key]: [...DEFAULT_LAYOUT],
          },
        }));
      },

      loadProjectLayout: (projectId) => {
        const key = projectId || 'global';
        const existing = get().layouts[key];
        
        // If layout already loaded and complete, do nothing
        if (existing && existing.length === DEFAULT_LAYOUT.length) {
          return;
        }

        // Try migrating legacy first
        const migrated = migrateLegacyLayout(projectId);
        if (migrated) {
          set((state) => ({
            layouts: {
              ...state.layouts,
              [key]: migrated,
            },
          }));
          return;
        }

        // If no existing or incomplete, initialize to default
        if (!existing) {
          set((state) => ({
            layouts: {
              ...state.layouts,
              [key]: [...DEFAULT_LAYOUT],
            },
          }));
        }
      },

      setLayoutForProject: (projectId, layout) => {
        const key = projectId || 'global';
        set((state) => ({
          layouts: {
            ...state.layouts,
            [key]: layout,
          },
        }));
      },

      setHasHydrated: (state) => set({ _hasHydrated: state }),
    }),
    {
      name: 'crm-dashboard-layout',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
