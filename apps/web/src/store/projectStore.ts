import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Project } from '@/types/api';
import { mutate } from 'swr';

// ──────────────────────────────────────────────────────────────────────────
// Project Store — project context is mandatory after login
// Switching project purges ALL SWR cache to prevent cross-project data mixing
// ──────────────────────────────────────────────────────────────────────────
interface ProjectState {
  activeProject: Project | null;
  setActiveProject: (project: Project) => void;
  clearProject: () => void;
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      activeProject: null,

      setActiveProject: (project: Project) => {
        const currentActive = get().activeProject;
        const currentId = currentActive?._id || currentActive?.project_id;
        const newId = project._id || project.project_id;

        if (currentId !== newId) {
          // CRITICAL: Purge all SWR caches on project switch
          mutate(() => true, undefined, { revalidate: false });
        }
        set({ activeProject: project });
      },

      clearProject: () => {
        mutate(() => true, undefined, { revalidate: false });
        set({ activeProject: null });
      },
    }),
    {
      name: 'crm-project',
      partialize: (state) => ({ activeProject: state.activeProject }),
    }
  )
);
