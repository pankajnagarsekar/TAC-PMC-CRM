'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useProjectStore } from '@/store/projectStore';
import Sidebar from '@/components/layout/Sidebar';
import ProjectSelectorModal from '@/components/layout/ProjectSelectorModal';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, accessToken, clearAuth } = useAuthStore();
  const { activeProject } = useProjectStore();
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

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

  const isClient = user.role === 'Client';

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

  return (
    <div className={`flex h-screen overflow-hidden ${isClient ? 'is-client' : ''}`} style={{ background: '#0f172a' }}>
      <Sidebar onProjectSwitch={() => setShowProjectModal(true)} />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-14 flex items-center justify-between px-6 border-b"
          style={{ background: '#1e293b', borderColor: '#334155' }}>
          <div className="flex items-center gap-3">
            {activeProject ? (
              <>
                <div className="w-2 h-2 rounded-full bg-green-500" />
                <span className="text-slate-300 text-sm font-medium">{activeProject.project_name}</span>
                <span className="text-slate-600 text-xs">{activeProject.project_code}</span>
                <button
                  id="switch-project-btn"
                  onClick={() => setShowProjectModal(true)}
                  className="ml-2 text-xs px-3 py-1 rounded-lg transition-colors"
                  style={{ background: '#334155', color: '#94a3b8' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#475569')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = '#334155')}
                >
                  Switch
                </button>
              </>
            ) : (
              <button
                onClick={() => setShowProjectModal(true)}
                className="text-sm px-4 py-1.5 rounded-lg font-medium"
                style={{ background: '#F97316', color: 'white' }}
              >
                Select Project
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
              style={{ background: '#1E3A5F', color: '#F97316' }}>
              {user.name?.[0]?.toUpperCase()}
            </div>
            <span className="text-slate-300 text-sm">{user.name}</span>
          </div>
        </header>

        {/* Main content */}
        <main className={`flex-1 overflow-y-auto p-6 ${isClient ? 'client-readonly' : ''}`}>
          {children}
        </main>
      </div>

      {/* Project selector modal */}
      {showProjectModal && (
        <ProjectSelectorModal onClose={() => setShowProjectModal(false)} />
      )}
    </div>
  );
}
