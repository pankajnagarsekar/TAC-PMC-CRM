"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import FinancialGrid from "@/components/ui/FinancialGrid";
import {
  Plus,
  Search,
  Edit2,
  Hash,
  CheckCircle2,
  XCircle,
  Tag,
  Loader2,
  Save,
  AlertCircle,
  Trash2,
} from "lucide-react";
import { fetcher } from "@/lib/api";
import axios from "@/lib/api";
import { CodeMaster } from "@/types/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";

export default function CategoriesPage() {
  const {
    data: codes,
    mutate,
    isLoading,
  } = useSWR<CodeMaster[]>("/api/codes", fetcher);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCode, setSelectedCode] = useState<CodeMaster | undefined>(
    undefined,
  );
  const [deleteCode, setDeleteCode] = useState<CodeMaster | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [formData, setFormData] = useState({
    code: "",
    category_name: "",
    description: "",
  });

  const columnDefs: any[] = useMemo(
    () => [
      {
        headerName: "Code",
        field: "code",
        width: 120,
        cellRenderer: (params: any) => (
          <code className="text-[11px] bg-orange-500/10 px-2 py-0.5 rounded border border-orange-500/20 text-orange-500 font-mono font-bold">
            {params.value}
          </code>
        ),
      },
      {
        headerName: "Category Name",
        field: "category_name",
        flex: 2,
        cellRenderer: (params: any) => (
          <span className="font-semibold text-zinc-900 dark:text-white">{params.value}</span>
        ),
      },
      {
        headerName: "Description",
        field: "description",
        flex: 3,
        cellRenderer: (params: any) => (
          <span className="text-slate-400 text-xs truncate">
            {params.value || "No description"}
          </span>
        ),
      },
      {
        headerName: "Status",
        field: "active_status",
        width: 120,
        cellRenderer: (params: any) => (
          <div className="flex items-center h-full">
            <span
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider ${params.value
                ? "bg-emerald-500/10 text-emerald-500 border border-emerald-500/20"
                : "bg-slate-500/10 text-slate-500 border border-slate-500/20"
                }`}
            >
              {params.value ? (
                <CheckCircle2 size={10} />
              ) : (
                <XCircle size={10} />
              )}
              {params.value ? "Active" : "Inactive"}
            </span>
          </div>
        ),
      },
      {
        headerName: "",
        field: "_id",
        width: 120,
        cellRenderer: (params: any) => (
          <div className="flex items-center justify-end h-full px-2 gap-1 admin-only">
            <button
              onClick={() => handleEdit(params.data)}
              className="p-2 hover:bg-zinc-100 dark:hover:bg-slate-800 rounded-lg text-zinc-500 dark:text-slate-400 hover:text-zinc-900 dark:hover:text-white transition-colors"
              title="Edit Category"
            >
              <Edit2 size={16} />
            </button>
            <button
              onClick={() => handleDelete(params.data)}
              className="p-2 hover:bg-red-50 dark:hover:bg-red-800 rounded-lg text-zinc-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              title="Delete Category"
            >
              <Trash2 size={16} />
            </button>
          </div>
        ),
      },
    ],
    [],
  );

  function handleEdit(code: CodeMaster) {
    setSelectedCode(code);
    setFormData({
      code: code.code,
      category_name: code.category_name,
      description: code.description || "",
    });
    setError("");
    setIsModalOpen(true);
  }

  function handleDelete(code: CodeMaster) {
    setDeleteCode(code);
  }

  function handleAddNew() {
    setSelectedCode(undefined);
    setFormData({ code: "", category_name: "", description: "" });
    setError("");
    setIsModalOpen(true);
  }

  async function confirmDelete() {
    if (!deleteCode) return;
    try {
      await axios.delete(`/api/codes/${deleteCode._id}`);
      mutate();
      setDeleteCode(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete category");
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (selectedCode) {
        await axios.put(`/api/codes/${selectedCode._id}`, formData);
      } else {
        await axios.post("/api/codes", formData);
      }
      mutate();
      setIsModalOpen(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to save category");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white flex items-center gap-3">
            <Tag className="text-orange-500" />
            Budget Categories
          </h1>
          <p className="text-zinc-500 dark:text-slate-500 text-sm mt-1">
            Define cost heads and categories for project budgeting.
          </p>
        </div>

        <button
          onClick={handleAddNew}
          className="admin-only bg-orange-600 hover:bg-orange-500 text-white px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all shadow-lg shadow-orange-900/20 active:scale-95"
        >
          <Plus size={18} />
          Add Category
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-white dark:bg-slate-900/50 p-4 rounded-2xl border border-zinc-200 dark:border-slate-800/50 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-slate-500"
            size={18}
          />
          <input
            type="text"
            placeholder="Search categories..."
            className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            value={searchTerm}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSearchTerm(e.target.value)
            }
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
          <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
          {codes?.length || 0} Categories Defined
        </div>
      </div>

      {/* Grid */}
      <FinancialGrid
        rowData={codes ?? []}
        columnDefs={columnDefs}
        loading={isLoading}
        quickFilterText={searchTerm}
        height="600px"
        showSrNo={true}
      />

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 text-zinc-900 dark:text-white">
          <DialogHeader>
            <DialogTitle className="text-xl flex items-center gap-2">
              <Tag className="text-orange-600 dark:text-orange-500" />
              {selectedCode ? "Edit Category" : "Add New Category"}
            </DialogTitle>
          </DialogHeader>

          <form onSubmit={handleSubmit} className="space-y-4 py-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-3 rounded-lg text-sm flex items-center gap-2">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            <div className="space-y-2">
              <label className="text-xs text-slate-500">
                Code (Short Name)
              </label>
              <div className="relative">
                <Hash
                  size={14}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600"
                />
                <input
                  required
                  className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 text-zinc-900 dark:text-white rounded-lg pl-9 pr-4 py-2 text-sm focus:border-orange-500/50 outline-none"
                  value={formData.code}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      code: e.target.value.toUpperCase(),
                    })
                  }
                  placeholder="e.g. CIV"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs text-slate-500">Category Name</label>
              <input
                required
                className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-100 dark:border-slate-800 text-zinc-900 dark:text-white rounded-lg px-3 py-2 text-sm focus:border-orange-500/50 outline-none"
                value={formData.category_name}
                onChange={(e) =>
                  setFormData({ ...formData, category_name: e.target.value })
                }
                placeholder="e.g. Civil Works"
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs text-slate-500">Description</label>
              <textarea
                className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-lg px-3 py-2 text-sm text-zinc-900 dark:text-white focus:border-orange-500/50 outline-none min-h-[100px]"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Optional description"
              />
            </div>

            <DialogFooter className="mt-6">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="bg-orange-600 hover:bg-orange-500 text-white px-6 py-2 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all disabled:opacity-50 shadow-lg shadow-orange-900/20"
              >
                {loading ? (
                  <Loader2 className="animate-spin" size={18} />
                ) : (
                  <Save size={18} />
                )}
                {selectedCode ? "Update" : "Create"}
              </button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      {deleteCode && (
        <Dialog open={!!deleteCode} onOpenChange={() => setDeleteCode(null)}>
          <DialogContent className="max-w-md bg-slate-950 border-slate-800 text-white">
            <DialogHeader>
              <DialogTitle className="text-lg flex items-center gap-2">
                <Trash2 className="text-red-500" />
                Delete Category
              </DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <p className="text-slate-300">
                Are you sure you want to delete{" "}
                <strong>{deleteCode.category_name}</strong> ({deleteCode.code})?
                This action cannot be undone and will deactivate the category.
              </p>
            </div>
            <DialogFooter>
              <button
                onClick={() => setDeleteCode(null)}
                className="px-4 py-2 text-sm font-medium text-slate-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="bg-red-600 hover:bg-red-500 text-white px-4 py-2 rounded-lg font-semibold text-sm transition-all"
              >
                Delete
              </button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
