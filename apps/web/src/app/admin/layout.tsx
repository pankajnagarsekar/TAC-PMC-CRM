'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useProjectStore } from '@/store/projectStore';
import Sidebar from '@/components/layout/Sidebar';
import ProjectSelectorModal from '@/components/layout/ProjectSelectorModal';
import ErrorBoundary from '@/components/ui/ErrorBoundary';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';

// CE-01: Register AG Grid modules globally once
ModuleRegistry.registerModules([AllCommunityModule]);

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, accessToken, clearAuth } = useAuthStore();
  const { activeProject } = useProjectStore();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (typeof window !== 'undefined') {
      const savedState = localStorage.getItem('sidebar-collapsed');
      if (savedState === 'true') {
        setIsSidebarCollapsed(true);
      }
    }
  }, []);

  const handleToggleSidebar = () => {
    const newState = !isSidebarCollapsed;
    setIsSidebarCollapsed(newState);
    localStorage.setItem('sidebar-collapsed', String(newState));
  };

  // Auth guard
  useEffect(() => {
    console.log('AdminLayout: checking auth...', { hasUser: !!user, hasToken: !!accessToken, role: user?.role });
    if (!accessToken || !user) {
      console.log('AdminLayout: No auth, redirecting to login');
      router.replace('/login');
      return;
    }
    if (user.role !== 'Admin' && user.role !== 'Client') {
      console.log('AdminLayout: Invalid role, clearing auth and redirecting');
      clearAuth();
      router.replace('/login');
      return;
    }
  }, [accessToken, user, router, clearAuth, mounted]);

  const isClient = user?.role === 'Client';

  useEffect(() => {
    if (!mounted) return;
    if (isClient) {
      document.body.classList.add('is-client');
    } else {
      document.body.classList.remove('is-client');
    }
    return () => {
      document.body.classList.remove('is-client');
    };
  }, [isClient, mounted]);

  if (!mounted) return null;

  if (!user || !accessToken) {
    return (
      <div className="min-h-screen bg-[#0f172a] flex items-center justify-center">
        <div className="text-orange-500 animate-pulse font-bold tracking-widest uppercase text-xs">
          Authenticating Secure Session...
        </div>
      </div>
    );
  }

  return (
    <div className={`flex h-screen overflow-hidden ${isClient ? 'is-client' : ''} bg-[#0b0f1a]`}>
      <Sidebar
        onProjectSwitch={() => setShowProjectModal(true)}
        isCollapsed={isSidebarCollapsed}
        onToggle={handleToggleSidebar}
      />

      <div className={`flex-1 flex flex-col transition-all duration-300 overflow-hidden relative ${isSidebarCollapsed ? 'pl-20' : 'pl-64'}`}>
        {/* Background Decor - Subtle Ambient Light */}
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-orange-500/5 blur-[120px] -z-10 pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-blue-500/5 blur-[100px] -z-10 pointer-events-none" />

        {/* Top bar - Glass Header */}
        <header className="h-16 flex items-center justify-between px-8 glass-header border-b border-white/[0.03] z-40">
          <div className="flex items-center gap-4">
            {activeProject ? (
              <div className="flex items-center gap-3 px-4 py-2 rounded-2xl bg-white/[0.02] border border-white/[0.03] group hover:bg-white/[0.04] transition-all duration-300">
                <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                <div className="flex flex-col">
                  <span className="text-slate-200 text-xs font-bold leading-none tracking-tight">Active Project</span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-white text-sm font-black">{activeProject.project_name}</span>
                    <span className="text-slate-500 text-[10px] font-mono border border-white/5 bg-white/[0.02] px-1.5 py-0.5 rounded uppercase tracking-wider">{activeProject.project_code}</span>
                  </div>
                </div>
                <button
                  id="switch-project-btn"
                  onClick={() => setShowProjectModal(true)}
                  className="ml-4 px-3 py-1.5 rounded-xl bg-orange-500/10 text-orange-500 text-[11px] font-bold uppercase tracking-wider hover:bg-orange-500/20 transition-all duration-300 border border-orange-500/10"
                >
                  Switch
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowProjectModal(true)}
                className="btn-premium-orange px-5 py-2 rounded-2xl text-xs font-bold uppercase tracking-widest shadow-[0_5px_15px_rgba(249,115,22,0.2)]"
              >
                Select Project
              </button>
            )}
          </div>

          <div className="flex items-center gap-4">
            {/* User Indicator */}
            <div className="flex items-center gap-3 py-1.5 pl-1.5 pr-4 rounded-full bg-white/[0.02] border border-white/5">
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-black shadow-inner bg-slate-800 text-orange-500 border border-white/5">
                {user.name?.[0]?.toUpperCase()}
              </div>
              <div className="flex flex-col">
                <span className="text-slate-100 text-sm font-bold leading-none">{user.name}</span>
                <span className="text-slate-500 text-[10px] font-semibold tracking-wide mt-0.5">{user.role}</span>
              </div>
            </div>
          </div>
        </header>

        {/* Main content - Refined Spacing */}
        <main className={`flex-1 overflow-y-auto p-8 relative ${isClient ? 'client-readonly' : ''} custom-scrollbar animate-in fade-in slide-in-from-bottom-2 duration-700 ease-out`}>
          <div className="max-w-[1700px] mx-auto">
            <ErrorBoundary>
              {children}
            </ErrorBoundary>
          </div>
        </main>
      </div>

      {/* Project selector modal */}
      {showProjectModal && (
        <ProjectSelectorModal onClose={() => setShowProjectModal(false)} />
      )}
    </div>
  );
}
