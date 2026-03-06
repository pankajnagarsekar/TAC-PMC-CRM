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
    (set) => ({
      activeProject: null,

      setActiveProject: (project: Project) => {
        // CRITICAL: Purge all SWR caches on project switch
        // This prevents cross-project data bleeding
        mutate(() => true, undefined, { revalidate: false });
        set({ activeProject: project });
        
        // Force full page reload to ensure fresh session and state
        if (typeof window !== 'undefined') {
          window.location.reload();
        }
      },

      clearProject: () => {
        mutate(() => true, undefined, { revalidate: false });
        set({ activeProject: null });
        if (typeof window !== 'undefined') {
          window.location.reload();
        }
      },
    }),
    {
      name: 'crm-project',
      partialize: (state) => ({ activeProject: state.activeProject }),
    }
  )
);
