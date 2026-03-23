"use client";

import React, { useState, useEffect } from "react";
import { X, AlertCircle } from "lucide-react";
import api from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { GlassCard } from "@/components/ui/GlassCard";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { Project, UserResponse } from "@tac-pmc/types";

interface CreateUserModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const SCREEN_PERMISSION_OPTIONS = [
  "work_orders",
  "payment_certificates",
  "scheduler",
  "reports",
  "team"
];

export function CreateUserModal({ open, onClose, onCreated }: CreateUserModalProps) {
  const { toast } = useToast();
  const { data: projects = [] } = useSWR<Project[]>(
    open ? "/api/v2/projects" : null,
    fetcher
  );

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    role: "Supervisor",
    dpr_generation_permission: false,
    assigned_projects: [] as string[],
    screen_permissions: [] as string[]
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const isClient = formData.role === "Client";
  const projectsRequired = isClient && formData.assigned_projects.length === 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    // Validation
    if (!formData.name.trim()) {
      setError("Name is required");
      return;
    }
    if (!formData.email.trim()) {
      setError("Email is required");
      return;
    }
    if (!formData.password || formData.password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (isClient && formData.assigned_projects.length === 0) {
      setError("Client users must be assigned to at least one project");
      return;
    }

    setLoading(true);
    try {
      const response = await api.post<UserResponse>("/api/users", {
        name: formData.name.trim(),
        email: formData.email.trim().toLowerCase(),
        password: formData.password,
        role: formData.role,
        dpr_generation_permission: formData.dpr_generation_permission,
        assigned_projects: formData.assigned_projects,
        screen_permissions: formData.screen_permissions
      });

      toast({
        title: "Success",
        description: `User "${formData.name}" created successfully`,
        variant: "default"
      });

      // Reset form
      setFormData({
        name: "",
        email: "",
        password: "",
        role: "Supervisor",
        dpr_generation_permission: false,
        assigned_projects: [],
        screen_permissions: []
      });

      onCreated();
      onClose();
    } catch (err: any) {
      const detail = err.response?.data?.detail || "Failed to create user";
      setError(typeof detail === "string" ? detail : JSON.stringify(detail));
      toast({
        title: "Error",
        description: "Failed to create user",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleProjectToggle = (projectId: string) => {
    setFormData(prev => ({
      ...prev,
      assigned_projects: prev.assigned_projects.includes(projectId)
        ? prev.assigned_projects.filter(id => id !== projectId)
        : [...prev.assigned_projects, projectId]
    }));
  };

  const handlePermissionToggle = (permission: string) => {
    setFormData(prev => ({
      ...prev,
      screen_permissions: prev.screen_permissions.includes(permission)
        ? prev.screen_permissions.filter(p => p !== permission)
        : [...prev.screen_permissions, permission]
    }));
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <GlassCard className="w-full max-w-2xl max-h-[90vh] overflow-y-auto border-orange-500/10">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 sticky top-0">
          <h2 className="text-2xl font-bold text-white">Create New User</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error banner */}
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 flex gap-2 items-start">
              <AlertCircle size={16} className="text-rose-500 flex-shrink-0 mt-0.5" />
              <p className="text-[13px] text-rose-400">{error}</p>
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider">
              Full Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="John Smith"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            />
          </div>

          {/* Email */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider">
              Email Address
            </label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              placeholder="john@example.com"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider">
              Password (min 8 chars)
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              placeholder="••••••••"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            />
          </div>

          {/* Role */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider">
              Role
            </label>
            <select
              value={formData.role}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  role: e.target.value,
                  assigned_projects: e.target.value === "Client" ? formData.assigned_projects : []
                })
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            >
              <option value="Admin">Admin</option>
              <option value="Supervisor">Supervisor</option>
              <option value="Client">Client</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* DPR Permission (only for non-Client) */}
          {!isClient && (
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="dpr_perm"
                checked={formData.dpr_generation_permission}
                onChange={(e) =>
                  setFormData({ ...formData, dpr_generation_permission: e.target.checked })
                }
                className="w-4 h-4 rounded border-slate-600 bg-slate-900 cursor-pointer"
              />
              <label htmlFor="dpr_perm" className="text-sm text-slate-300 cursor-pointer">
                Allow DPR (Daily Project Report) generation
              </label>
            </div>
          )}

          {/* Assigned Projects (only for Client, required) */}
          {isClient && (
            <div>
              <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider flex items-center gap-1">
                Assigned Projects
                <span className="text-rose-400">*</span>
              </label>
              <div className="space-y-2 bg-slate-950 border border-slate-800 rounded-lg p-3">
                {projects.length === 0 ? (
                  <p className="text-sm text-slate-500">No projects available</p>
                ) : (
                  projects.map((proj) => (
                    <label key={proj.project_id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.assigned_projects.includes(proj.project_id || "")}
                        onChange={() => handleProjectToggle(proj.project_id || "")}
                        className="w-4 h-4 rounded border-slate-600 bg-slate-900"
                      />
                      <span className="text-sm text-slate-300">{proj.project_name}</span>
                    </label>
                  ))
                )}
              </div>
              {projectsRequired && (
                <p className="text-xs text-rose-400 mt-1">At least one project is required</p>
              )}
            </div>
          )}

          {/* Screen Permissions */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider">
              Screen Permissions
            </label>
            <div className="space-y-2 bg-slate-950 border border-slate-800 rounded-lg p-3">
              {SCREEN_PERMISSION_OPTIONS.map((perm) => (
                <label key={perm} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.screen_permissions.includes(perm)}
                    onChange={() => handlePermissionToggle(perm)}
                    className="w-4 h-4 rounded border-slate-600 bg-slate-900"
                  />
                  <span className="text-sm text-slate-300 capitalize">{perm.replace(/_/g, " ")}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              type="submit"
              disabled={loading || projectsRequired}
              className="flex-1 px-4 py-2.5 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-bold transition-all"
            >
              {loading ? "Creating..." : "Create User"}
            </button>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-sm font-bold transition-all"
            >
              Cancel
            </button>
          </div>
        </form>
      </GlassCard>
    </div>
  );
}
