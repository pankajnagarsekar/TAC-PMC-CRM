'use client';

import { useEffect, useState } from 'react';
import { useProjectStore } from '@/store/projectStore';
import api from '@/lib/api';
import { Project } from '@/types/api';
import { FolderOpen, Search, X, ChevronRight } from 'lucide-react';

interface ProjectSelectorModalProps {
  onClose: () => void;
}

export default function ProjectSelectorModal({ onClose }: ProjectSelectorModalProps) {
  const { activeProject, setActiveProject } = useProjectStore();
  const [projects, setProjects] = useState<Project[]>([]);
  const [filtered, setFiltered] = useState<Project[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadProjects() {
      try {
        const res = await api.get<Project[]>('/api/projects');
        setProjects(res.data);
        setFiltered(res.data);
      } catch {
        setError('Failed to load projects.');
      } finally {
        setLoading(false);
      }
    }
    loadProjects();
  }, []);

  useEffect(() => {
    const q = search.toLowerCase();
    setFiltered(
      projects.filter(
        (p) =>
          p.project_name.toLowerCase().includes(q) ||
          (p.project_code || '').toLowerCase().includes(q)
      )
    );
  }, [search, projects]);

  function selectProject(project: Project) {
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
        <div className="max-h-80 overflow-y-auto p-3">
          {loading && (
            <div className="flex items-center justify-center py-8 gap-3">
              <div className="w-5 h-5 border-2 border-orange-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-slate-400 text-sm">Loading projects...</span>
            </div>
          )}

          {error && (
            <div className="text-center py-8 text-red-400 text-sm">{error}</div>
          )}

          {!loading && !error && filtered.length === 0 && (
            <div className="text-center py-8 text-slate-500 text-sm">No projects found</div>
          )}

          {!loading && !error && filtered.map((project) => {
            const isActive = activeProject?.project_id === project.project_id;
            return (
              <button
                key={project.project_id}
                id={`project-${project.project_id}`}
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
            {projects.length} project{projects.length !== 1 ? 's' : ''} available
          </p>
        </div>
      </div>
    </div>
  );
}
