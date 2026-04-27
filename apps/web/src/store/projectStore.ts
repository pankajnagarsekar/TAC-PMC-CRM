import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Project } from '@/types/api';
import { mutate } from 'swr';

// ──────────────────────────────────────────────────────────────────────────
// Project Store — project context is mandatory after login
// Switching project purges ALL SWR cache to prevent cross-project data mixing
// ──────────────────────────────────────────────────────────────────────────
export interface ProjectState {
  activeProject: Project | null;
  /** Global override for breadcrumb labels (e.g. {taskId: 'Fix Layout Bug'}) */
  breadcrumbTitle: string | null;
  _hasHydrated: boolean;
  setActiveProject: (project: Project) => void;
  setBreadcrumbTitle: (title: string | null) => void;
  clearProject: () => void;
  setHasHydrated: (state: boolean) => void;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      activeProject: null,
      breadcrumbTitle: null,
      _hasHydrated: false,

      setActiveProject: (project: Project) => {
        const currentActive = get().activeProject;
        const currentId = currentActive?._id || currentActive?.project_id;
        const newId = project._id || project.project_id;

        if (currentId !== newId) {
          // Purge project-scoped SWR caches (keep /projects/ list for registry)
          mutate(
            (key) => typeof key === 'string' && key !== '/api/v1/projects/',
            undefined,
            { revalidate: false }
          );
        }
        set({ activeProject: project });
      },

      setBreadcrumbTitle: (title) => set({ breadcrumbTitle: title }),

      clearProject: () => {
        // Purge project-scoped caches; keep /projects/ list so registry can search
        mutate(
          (key) => typeof key === 'string' && key !== '/api/v1/projects/',
          undefined,
          { revalidate: false }
        );
        set({ activeProject: null });
      },

      setHasHydrated: (state) => set({ _hasHydrated: state }),
    }),
    {
      name: 'crm-project',
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
      partialize: (state) => ({ activeProject: state.activeProject }),
    }
  )
);
