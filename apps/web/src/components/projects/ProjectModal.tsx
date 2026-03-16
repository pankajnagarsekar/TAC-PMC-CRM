"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import { fetcher } from "@/lib/api";
import axios from "@/lib/api";
import { Project, Client, CodeMaster } from "@/types/api";
import {
  Layout,
  Hash,
  MapPin,
  Building,
  DollarSign,
  Save,
  Loader2,
  AlertCircle,
} from "lucide-react";

interface ProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  project?: Project;
}

export default function ProjectModal({
  isOpen,
  onClose,
  onSuccess,
  project,
}: ProjectModalProps) {
  const { data: clients } = useSWR<Client[]>("/api/clients", fetcher);
  const { data: codes } = useSWR<CodeMaster[]>("/api/codes", fetcher);

  const [formData, setFormData] = useState({
    project_name: "",
    project_code: "",
    client_id: "",
    status: "active",
    address: "",
    city: "",
    state: "",
    project_retention_percentage: 0,
    project_cgst_percentage: 9,
    project_sgst_percentage: 9,
    completion_percentage: 0,
    threshold_petty: 0,
    threshold_ovh: 0,
  });

  const [budgets, setBudgets] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (project) {
      setFormData({
        project_name: project.project_name,
        project_code: project.project_code || "",
        client_id: project.client_id || "",
        status: project.status,
        address: project.address || "",
        city: project.city || "",
        state: project.state || "",
        project_retention_percentage: project.project_retention_percentage,
        project_cgst_percentage: project.project_cgst_percentage,
        project_sgst_percentage: project.project_sgst_percentage,
        completion_percentage: project.completion_percentage || 0,
        threshold_petty: project.threshold_petty || 0,
        threshold_ovh: project.threshold_ovh || 0,
      });

      // Fetch existing budgets if editing
      if (project._id) {
        axios.get(`/api/projects/${project._id}/budgets`).then((res) => {
          const budgetMap: Record<string, number> = {};
          res.data.forEach((b: any) => {
            budgetMap[b.code_id] = b.original_budget;
          });
          setBudgets(budgetMap);
        });
      }
    } else {
      setFormData({
        project_name: "",
        project_code: "",
        client_id: "",
        status: "active",
        address: "",
        city: "",
        state: "",
        project_retention_percentage: 0,
        project_cgst_percentage: 9,
        project_sgst_percentage: 9,
        completion_percentage: 0,
        threshold_petty: 0,
        threshold_ovh: 0,
      });
      setBudgets({});
    }
  }, [project, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      let projectId = project?._id;

      if (project) {
        await axios.put(`/api/projects/${project._id}`, formData);
      } else {
        const res = await axios.post("/api/projects", formData);
        projectId = res.data._id;
      }

      // Save budgets
      const budgetPromises = Object.entries(budgets).map(
        ([code_id, amount]) => {
          if (amount > 0) {
            return axios.post(`/api/projects/${projectId}/budgets`, {
              code_id,
              original_budget: amount,
            });
          }
          return Promise.resolve();
        },
      );

      await Promise.all(budgetPromises);

      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to save project");
    } finally {
      setLoading(false);
    }
  };

  const handleBudgetChange = (code_id: string, value: string) => {
    const amount = parseFloat(value) || 0;
    setBudgets((prev) => ({ ...prev, [code_id]: amount }));
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto bg-slate-950 border-slate-800 text-white">
        <DialogHeader>
          <DialogTitle className="text-xl flex items-center gap-2">
            <Layout className="text-orange-500" />
            {project ? "Edit Project" : "Create New Project"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6 py-4">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-3 rounded-lg text-sm flex items-center gap-2">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Basic Info */}
            <div className="space-y-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800/50">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Basic Information
              </h3>

              <div className="space-y-2">
                <label className="text-xs text-slate-500">Project Name</label>
                <div className="relative">
                  <Building
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600"
                  />
                  <input
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-sm focus:border-orange-500/50 outline-none"
                    value={formData.project_name}
                    onChange={(e) =>
                      setFormData({ ...formData, project_name: e.target.value })
                    }
                    placeholder="Enter project name"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-slate-500">Project Code</label>
                  <div className="relative">
                    <Hash
                      size={14}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600"
                    />
                    <input
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-sm focus:border-orange-500/50 outline-none"
                      value={formData.project_code}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          project_code: e.target.value,
                        })
                      }
                      placeholder="P-001"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-slate-500">Client</label>
                  <select
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                    value={formData.client_id}
                    onChange={(e) =>
                      setFormData({ ...formData, client_id: e.target.value })
                    }
                  >
                    <option value="">Select Client</option>
                    {clients?.map((c) => (
                      <option key={c._id} value={c._id}>
                        {c.client_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-500">Address</label>
                <div className="relative">
                  <MapPin
                    size={14}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600"
                  />
                  <input
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-sm focus:border-orange-500/50 outline-none"
                    value={formData.address}
                    onChange={(e) =>
                      setFormData({ ...formData, address: e.target.value })
                    }
                    placeholder="Site location address"
                  />
                </div>
              </div>
            </div>

            {/* Financial Details */}
            <div className="space-y-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800/50">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Financial Invariants
              </h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-slate-500">CGST %</label>
                  <input
                    type="number"
                    step="0.01"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                    value={formData.project_cgst_percentage}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        project_cgst_percentage: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-slate-500">SGST %</label>
                  <input
                    type="number"
                    step="0.01"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                    value={formData.project_sgst_percentage}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        project_sgst_percentage: parseFloat(e.target.value),
                      })
                    }
                  />
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-500">Retention %</label>
                <input
                  type="number"
                  step="0.1"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                  value={formData.project_retention_percentage}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      project_retention_percentage: parseFloat(e.target.value),
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-500">
                  Petty Cash Threshold
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                  value={formData.threshold_petty}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      threshold_petty: parseFloat(e.target.value),
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-500">OVH Threshold</label>
                <input
                  type="number"
                  step="0.01"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                  value={formData.threshold_ovh}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      threshold_ovh: parseFloat(e.target.value),
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-500">Status</label>
                <select
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                  value={formData.status}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value })
                  }
                >
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="on-hold">On Hold</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs text-slate-500">
                  Project Completion %
                </label>
                <div className="flex items-center gap-3">
                  <div className="flex-1">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="1"
                      className="w-full accent-orange-500"
                      value={formData.completion_percentage}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          completion_percentage: parseInt(e.target.value),
                        })
                      }
                    />
                  </div>
                  <div className="w-12 text-center">
                    <span className="text-sm font-bold text-orange-500">
                      {formData.completion_percentage}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Budget Initialization Grid */}
          <div className="space-y-4 bg-slate-900/50 p-4 rounded-xl border border-slate-800/50">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              Budget Initialization
              <span className="text-[10px] bg-orange-500/10 text-orange-500 px-2 py-0.5 rounded border border-orange-500/20">
                Set category limits
              </span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
              {codes?.map((code) => (
                <div
                  key={code._id}
                  className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-slate-300 truncate pr-2">
                      {code.category_name}
                    </span>
                    <span className="text-[10px] text-slate-600 font-mono">
                      {code.code}
                    </span>
                  </div>
                  <div className="relative">
                    <DollarSign
                      size={12}
                      className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-600"
                    />
                    <input
                      type="number"
                      placeholder="0.00"
                      className="w-full bg-slate-900 border border-slate-800 rounded-md pl-7 pr-3 py-1.5 text-xs focus:border-orange-500/50 outline-none text-orange-400 font-mono"
                      value={budgets[code._id || ""] || ""}
                      onChange={(e) =>
                        handleBudgetChange(code._id || "", e.target.value)
                      }
                    />
                  </div>
                </div>
              ))}
              {(!codes || codes.length === 0) && (
                <div className="col-span-full py-8 text-center text-slate-600 border border-dashed border-slate-800 rounded-xl">
                  No budget categories found. Please add categories first.
                </div>
              )}
            </div>
          </div>

          <DialogFooter className="sticky bottom-0 bg-slate-950 py-4 border-t border-slate-800 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="bg-orange-600 hover:bg-orange-500 text-white px-6 py-2 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-orange-900/20"
            >
              {loading ? (
                <Loader2 className="animate-spin" size={18} />
              ) : (
                <Save size={18} />
              )}
              {project ? "Update Project" : "Create Project"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
