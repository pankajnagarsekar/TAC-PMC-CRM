"use client";

import React, { useState, useEffect } from "react";
import { X, AlertCircle } from "lucide-react";
import api from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { GlassCard } from "@/components/ui/GlassCard";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { Project, UserResponse, Client } from "@tac-pmc/types";

interface EditUserModalProps {
  user: UserResponse | null;
  onClose: () => void;
  onUpdated: () => void;
}

const SCREEN_PERMISSION_OPTIONS = [
  "work_orders",
  "payment_certificates",
  "scheduler",
  "reports",
  "team"
];

export function EditUserModal({ user, onClose, onUpdated }: EditUserModalProps) {
  const { toast } = useToast();

  const isClient = user?.role === "Client";

  const { data: projects = [] } = useSWR<Project[]>(
    user && isClient ? "/api/v1/projects/" : null,
    fetcher
  );

  useSWR<Client[]>(
    user && isClient ? "/api/v1/clients/" : null,
    fetcher
  );

  const [formData, setFormData] = useState({
    name: user?.name || "",
    role: user?.role || "Supervisor",
    active_status: user?.active_status ?? true,
    dpr_generation_permission: user?.dpr_generation_permission ?? false,
    assigned_projects: user?.assigned_projects || [],
    screen_permissions: user?.screen_permissions || []
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (user) {
      setFormData({
        name: user.name,
        role: user.role,
        active_status: user.active_status,
        dpr_generation_permission: user.dpr_generation_permission,
        assigned_projects: user.assigned_projects,
        screen_permissions: user.screen_permissions
      });
      setHasChanges(false);
    }
  }, [user]);

  const isClientRole = formData.role === "Client";
  const projectsRequired = isClientRole && formData.assigned_projects.length === 0;

  const handleChange = (field: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setHasChanges(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;

    setError("");

    if (!formData.name.trim()) {
      setError("Name is required");
      return;
    }

    if (isClientRole && formData.assigned_projects.length === 0) {
      setError("Client users must be assigned to at least one project");
      return;
    }

    setLoading(true);
    try {
      // Build update payload with only changed fields
      const updateData: Record<string, unknown> = {};
      if (formData.name !== user.name) updateData.name = formData.name;
      if (formData.role !== user.role) updateData.role = formData.role;
      if (formData.active_status !== user.active_status) updateData.active_status = formData.active_status;
      if (formData.dpr_generation_permission !== user.dpr_generation_permission) {
        updateData.dpr_generation_permission = formData.dpr_generation_permission;
      }
      if (JSON.stringify(formData.assigned_projects) !== JSON.stringify(user.assigned_projects)) {
        updateData.assigned_projects = formData.assigned_projects;
      }
      if (JSON.stringify(formData.screen_permissions) !== JSON.stringify(user.screen_permissions)) {
        updateData.screen_permissions = formData.screen_permissions;
      }

      await api.put(`/api/v1/users/${user.user_id}`, updateData);

      toast({
        title: "Success",
        description: `User &quot;${formData.name}&quot; updated successfully`,
        variant: "default"
      });

      onUpdated();
      onClose();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string | object } } };
      const detail = error.response?.data?.detail || "Failed to update user";
      setError(typeof detail === "string" ? detail : JSON.stringify(detail));
      toast({
        title: "Error",
        description: "Failed to update user",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleProjectToggle = (projectId: string) => {
    handleChange(
      "assigned_projects",
      formData.assigned_projects.includes(projectId)
        ? formData.assigned_projects.filter(id => id !== projectId)
        : [...formData.assigned_projects, projectId]
    );
  };

  const handlePermissionToggle = (permission: string) => {
    handleChange(
      "screen_permissions",
      formData.screen_permissions.includes(permission)
        ? formData.screen_permissions.filter(p => p !== permission)
        : [...formData.screen_permissions, permission]
    );
  };

  if (!user) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <GlassCard className="w-full max-w-2xl max-h-[90vh] overflow-y-auto border-orange-500/10">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 sticky top-0">
          <h2 className="text-2xl font-bold text-white">Edit User</h2>
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
              onChange={(e) => handleChange("name", e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            />
          </div>

          {/* Email (read-only) */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider">
              Email Address (read-only)
            </label>
            <input
              type="email"
              value={user.email}
              disabled
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-slate-500 cursor-not-allowed opacity-50"
            />
          </div>

          {/* Role */}
          <div>
            <label className="block text-xs font-bold text-slate-300 uppercase mb-2 tracking-wider">
              Role
            </label>
            <select
              value={formData.role}
              onChange={(e) => {
                handleChange("role", e.target.value);
                // Keep assigned_projects if switching to Client
                if (e.target.value !== "Client") {
                  handleChange("assigned_projects", []);
                }
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            >
              <option value="Admin">Admin</option>
              <option value="Supervisor">Supervisor</option>
              <option value="Client">Client</option>
              <option value="Other">Other</option>
            </select>
          </div>

          {/* Active Status */}
          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="active_status"
              checked={formData.active_status}
              onChange={(e) => handleChange("active_status", e.target.checked)}
              className="w-4 h-4 rounded border-slate-600 bg-slate-900 cursor-pointer"
            />
            <label htmlFor="active_status" className="text-sm text-slate-300 cursor-pointer">
              User is active
            </label>
          </div>

          {/* DPR Permission (only for non-Client) */}
          {!isClientRole && (
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="dpr_perm"
                checked={formData.dpr_generation_permission}
                onChange={(e) => handleChange("dpr_generation_permission", e.target.checked)}
                className="w-4 h-4 rounded border-slate-600 bg-slate-900 cursor-pointer"
              />
              <label htmlFor="dpr_perm" className="text-sm text-slate-300 cursor-pointer">
                Allow DPR (Daily Project Report) generation
              </label>
            </div>
          )}

          {/* Client Info (if applicable) */}
          {isClientRole && user.assigned_projects.length > 0 && (
            <div className="p-3 rounded-lg bg-orange-500/5 border border-orange-500/20">
              <p className="text-[12px] text-slate-400 mb-2">
                <span className="text-orange-500 font-semibold">Assigned to {user.assigned_projects.length} project(s)</span>
              </p>
            </div>
          )}

          {/* Assigned Projects (only for Client, required) */}
          {isClientRole && (
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
              disabled={loading || projectsRequired || !hasChanges}
              className="flex-1 px-4 py-2.5 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-bold transition-all"
            >
              {loading ? "Updating..." : "Update User"}
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
