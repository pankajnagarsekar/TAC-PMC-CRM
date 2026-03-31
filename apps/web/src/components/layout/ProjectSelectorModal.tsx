import React, { useState, useMemo } from 'react';
import { useProjectStore } from '@/store/projectStore';
import { useAuthStore } from '@/store/authStore';
import useSWR from 'swr';
import { fetcher } from '@/lib/api';
import { Project } from '@/types/api';
import { FolderOpen, Search, X, ChevronRight, AlertTriangle, Building2, Loader2, Target } from 'lucide-react';

interface ProjectSelectorModalProps {
  onClose: () => void;
}

export default function ProjectSelectorModal({ onClose }: ProjectSelectorModalProps) {
  const { user } = useAuthStore();
  const { activeProject, setActiveProject } = useProjectStore();
  const [search, setSearch] = useState('');

  const { data: projects, error, isLoading, mutate } = useSWR<Project[]>(
    user ? '/api/v1/projects/' : null,
    fetcher,
    { revalidateOnFocus: true }
  );

  const filtered = useMemo(() => {
    if (!projects) return [];
    const q = search.toLowerCase();
    return projects.filter(
      (p) =>
        p.project_name.toLowerCase().includes(q) ||
        (p.project_code || '').toLowerCase().includes(q)
    );
  }, [search, projects]);



  function selectProject(project: Project) {
    console.log("Selecting project:", project);
    console.log("Project has project_id?", project.project_id);
    setActiveProject(project);
    // Force a full page reload to ensure absolute financial data isolation and clear all state
    window.location.reload();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}>
      <div className="w-full max-w-lg mx-4 rounded-2xl overflow-hidden"
        style={{ background: '#1e293b', border: '1px solid #334155' }}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: '#334155' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'rgba(249,115,22,0.15)' }}>
              <FolderOpen size={18} style={{ color: '#F97316' }} />
            </div>
            <div>
              <h2 className="text-white font-semibold text-base">Select Project</h2>
              <p className="text-slate-500 text-xs">Project context is required to continue</p>
            </div>
          </div>
          {activeProject && (
            <button onClick={onClose}
              className="text-slate-500 hover:text-slate-300 transition-colors">
              <X size={18} />
            </button>
          )}
        </div>

        {/* Search */}
        <div className="px-6 py-4 border-b" style={{ borderColor: '#334155' }}>
          <div className="relative">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name or code..."
              className="w-full pl-9 pr-4 py-2.5 rounded-xl text-sm text-white placeholder:text-slate-600 outline-none"
              style={{ background: '#0f172a', border: '1px solid #334155' }}
            />
          </div>
        </div>

        {/* List */}
        <div className="max-h-80 overflow-y-auto p-3 custom-scrollbar">
          {isLoading && (
            <div className="flex flex-col items-center justify-center py-12 gap-3">
              <Loader2 size={24} className="text-orange-500 animate-spin opacity-50" />
              <span className="text-slate-500 text-[10px] font-black uppercase tracking-widest">Synchronizing Registry...</span>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-10 px-6 text-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-500">
                <AlertTriangle size={20} />
              </div>
              <div className="space-y-1">
                <p className="text-white text-sm font-bold">Failed to load projects</p>
                <p className="text-slate-500 text-xs text-balance">The system couldn't verify your project permissions.</p>
              </div>
              <button
                onClick={() => mutate()}
                className="px-4 py-2 bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all"
              >
                Retry Auth Sync
              </button>
            </div>
          )}

          {!isLoading && !error && filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 gap-3 opacity-40">
              <Building2 size={32} className="text-slate-600" />
              <span className="text-slate-500 text-[10px] font-black uppercase tracking-widest italic">No assets match your search</span>
            </div>
          )}

          {!isLoading && !error && filtered.map((project: Project) => {
            const isActive = activeProject?.project_id === project.project_id;
            return (
              <button
                key={project.project_id || project._id}
                id={`project-${project.project_id || project._id}`}
                onClick={() => selectProject(project)}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-all mb-1"
                style={{
                  background: isActive ? 'rgba(249,115,22,0.12)' : 'transparent',
                  border: isActive ? '1px solid rgba(249,115,22,0.3)' : '1px solid transparent',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'transparent';
                }}
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  style={{ background: isActive ? 'rgba(249,115,22,0.2)' : '#1E3A5F' }}>
                  <span className="text-xs font-bold" style={{ color: isActive ? '#F97316' : '#94a3b8' }}>
                    {project.project_code?.[0] || project.project_name[0]}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium truncate">{project.project_name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    {project.project_code && (
                      <span className="text-slate-500 text-xs">{project.project_code}</span>
                    )}
                    <span className="text-xs px-1.5 py-0.5 rounded"
                      style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>
                      {project.status}
                    </span>
                  </div>
                </div>
                {isActive && <ChevronRight size={14} style={{ color: '#F97316' }} />}
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t text-center" style={{ borderColor: '#334155' }}>
          <p className="text-slate-600 text-xs">
            {projects?.length || 0} project{projects?.length !== 1 ? 's' : ''} available
          </p>
        </div>
      </div>
    </div>
  );
}
