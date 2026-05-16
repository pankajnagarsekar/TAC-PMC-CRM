"use client";

import { useState, useMemo, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { z } from "zod";
import useSWR from "swr";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { ColDef } from "ag-grid-community";
import {
  ArrowLeft,
  AlertTriangle,
  Loader2,
  Save,
  MapPin,
  Building2,
  Layout,
  FileText,
  CheckSquare,
  Wallet,
} from "lucide-react";
import api, { fetcher } from "@/lib/api";
import { Project, DerivedFinancialState } from "@/types/api";
import { formatCurrency } from "@tac-pmc/ui";
import { useProjectStore } from "@/store/projectStore";
import { useToast } from "@/hooks/use-toast";
import VersionConflictModal from "@/components/ui/VersionConflictModal";
import LinkedCertificates from "@/components/work-orders/LinkedCertificates";
import LinkedWorkOrders from "@/components/work-orders/LinkedWorkOrders";
import KPICard from "@/components/ui/KPICard";
import type { ICellRendererParams, NewValueParams } from "ag-grid-community";
import { NumericCellEditor } from "@/components/financial/BudgetComponents";

const budgetSchema = z.number().min(0, "Budget cannot be negative").max(1000000000, "Budget exceeds limit");

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const { setActiveProject, activeProject: storeActiveProject } = useProjectStore();
  const { toast } = useToast();

  const { data: project, error: projectError, mutate: mutateProject, isLoading: projectLoading } = useSWR<Project>(
    `/api/v1/projects/${projectId}`,
    fetcher,
  );
  const {
    data: financials,
    error: financialsError,
    mutate: mutateFinancials,
    isLoading: financialsLoading,
  } = useSWR<DerivedFinancialState[]>(
    `/api/v1/projects/${projectId}/financials`,
    fetcher,
  );

  const [savingId, setSavingId] = useState<string | null>(null);
  const [isConflictModalOpen, setIsConflictModalOpen] = useState(false);

  // Sync project context for dashboard compatibility
  useEffect(() => {
    if (project && (!storeActiveProject || storeActiveProject.project_id !== project.project_id)) {
      setActiveProject(project);
    }
  }, [project, storeActiveProject, setActiveProject]);

  const columnDefs: ColDef<DerivedFinancialState>[] = useMemo(
    () => [
      {
        headerName: "Category/Code",
        field: "category_name",
        flex: 1.5,
        cellRenderer: (params: ICellRendererParams<DerivedFinancialState>) => {
          if (!params.data) return null;
          const isSaving = savingId === params.data._id;
          return (
            <div className="flex flex-col justify-center py-1 relative">
              {isSaving && (
                <div className="absolute right-0 top-1/2 -translate-y-1/2">
                  <Loader2 className="w-3 h-3 animate-spin text-orange-500" />
                </div>
              )}
              <span className="font-semibold text-foreground">
                {params.value || params.data.category_id}
              </span>
              <span className="text-[10px] text-zinc-400 font-mono">
                {params.data.category_code}
              </span>
              {params.data.over_commit_flag && (
                <span className="text-[9px] text-red-500 font-bold uppercase tracking-tighter">
                  Budget Overrun
                </span>
              )}
            </div>
          );
        },
      },
      {
        headerName: "Approved Budget",
        field: "original_budget",
        flex: 1.2,
        editable: true,
        cellEditor: NumericCellEditor,
        cellClass: (params) => params.value > 0
          ? "font-mono text-foreground"
          : "font-mono text-slate-400 dark:text-slate-500",
        minWidth: 160,
        valueFormatter: (params) => formatCurrency(params.value),
        onCellValueChanged: async (params: NewValueParams<DerivedFinancialState>) => {
          const { _id, project_id, category_id, original_budget, version } = params.data;
          if (!project_id || !category_id) return;

          // BUG-003: Strict UI Validation
          const parsed = parseFloat(String(original_budget));
          const validation = budgetSchema.safeParse(parsed);

          if (!validation.success || isNaN(parsed)) {
            const errorMsg = !validation.success ? validation.error.issues[0].message : "Invalid numeric value for budget.";
            toast({
              title: "Validation Error",
              description: errorMsg,
              variant: "destructive",
            });
            params.node?.setDataValue("original_budget", params.oldValue);
            return;
          }

          setSavingId(_id || category_id);
          try {
            await api.patch(`/api/v1/budgets/project/${project_id}/category/${category_id}`, {
              original_budget: parsed,
              expected_version: version || 1,
            });
            await mutateFinancials();
            await mutateProject(); // Refresh master totals
          } catch (error: unknown) {
            const err = error as { response?: { status?: number; data?: { error?: { message?: string } } } };
            if (err.response?.status === 409) {
              setIsConflictModalOpen(true);
            } else if (err.response?.status === 422) {
              const msg = err.response.data?.error?.message || "Budget cannot be below committed amount.";
              toast({
                title: "Budget Restriction",
                description: msg,
                variant: "destructive",
              });
            } else {
              toast({
                title: "Update Failed",
                description: "Failed to update budget. Please check permissions.",
                variant: "destructive",
              });
            }
            // Restore old value on failure
            params.node?.setDataValue("original_budget", params.oldValue);
          } finally {
            setSavingId(null);
          }
        },
      },
      {
        headerName: "Committed (WOs)",
        field: "committed_value",
        flex: 1.2,
        cellClass: "text-zinc-600 dark:text-slate-300 font-mono",
        valueFormatter: (params) => formatCurrency(params.value),
        minWidth: 160,
      },
      {
        headerName: "Certified (PCs)",
        field: "certified_value",
        flex: 1.2,
        cellClass: "text-zinc-400 dark:text-slate-400 font-mono",
        valueFormatter: (params) => formatCurrency(params.value),
        minWidth: 160,
      },
      {
        headerName: "Remaining",
        field: "balance_budget_remaining",
        flex: 1.2,
        cellRenderer: (params: ICellRendererParams<DerivedFinancialState>) => {
          const isNegative = (params.value || 0) < 0;
          return (
            <span
              className={`font-mono font-bold ${isNegative ? "text-rose-600 dark:text-rose-500" : "text-emerald-600 dark:text-emerald-500"}`}
            >
              {formatCurrency(params.value)}
            </span>
          );
        },
        minWidth: 160,
      },
    ],
    [mutateFinancials, mutateProject, savingId],
  );

  if (projectError || financialsError) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] space-y-4">
        <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-2xl">
          <AlertTriangle className="w-8 h-8 text-rose-600 dark:text-rose-500" />
        </div>
        <div className="text-center">
          <h3 className="text-zinc-900 dark:text-white font-bold">Failed to load project details</h3>
          <p className="text-zinc-500 dark:text-slate-500 text-sm">The intelligence module could not retrieve data for this reference.</p>
        </div>
        <button
          onClick={() => router.push("/admin/projects")}
          className="px-4 py-2 bg-zinc-100 dark:bg-slate-800 hover:bg-zinc-200 dark:hover:bg-slate-700 text-zinc-900 dark:text-white rounded-xl text-sm font-bold transition-all border border-zinc-200 dark:border-transparent"
        >
          Return to Registry
        </button>
      </div>
    );
  }

  if (projectLoading || financialsLoading || !project) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 text-orange-600 dark:text-orange-500 animate-spin" />
      </div>
    );
  }

  // Aggregate Totals
  const totalBudget =
    financials?.reduce((sum, f) => sum + Number(f.original_budget || 0), 0) ?? 0;
  const totalCommitted =
    financials?.reduce((sum, f) => sum + Number(f.committed_value || 0), 0) ?? 0;
  const totalCertified =
    financials?.reduce((sum, f) => sum + Number(f.certified_value || 0), 0) ?? 0;
  const totalRemaining =
    financials?.reduce(
      (sum, f) => sum + Number(f.balance_budget_remaining || 0),
      0,
    ) ?? 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <button
          onClick={() => router.push("/admin/projects")}
          className="flex items-center gap-2 text-zinc-500 dark:text-slate-500 hover:text-zinc-900 dark:hover:text-white transition-colors text-sm w-fit font-medium"
        >
          <ArrowLeft size={16} /> Back to Projects
        </button>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-white flex items-center gap-3">
              {project.project_name}
              <span className="text-[10px] bg-zinc-100 dark:bg-slate-800 px-2 py-0.5 rounded font-mono text-zinc-500 dark:text-slate-400 uppercase tracking-widest border border-zinc-200 dark:border-transparent">
                {project.project_code}
              </span>
            </h1>
            <div className="flex items-center gap-4 text-[10px] uppercase font-black tracking-widest text-zinc-400 dark:text-slate-500">
              <span className="flex items-center gap-1">
                <MapPin size={12} className="text-orange-600 dark:text-orange-500" />
                {project.address || "No address set"}
                {project.city && `, ${project.city}`}
                {project.state && `, ${project.state}`}
              </span>
              <span className="flex items-center gap-1">
                <Building2 size={12} className="text-orange-600 dark:text-orange-500" />{" "}
                {project.client_name || "Direct Project"}
              </span>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className="bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full text-[10px] font-bold text-emerald-600 dark:text-emerald-500 uppercase tracking-widest">
              {project.status}
            </div>
            {financials && financials.length === 0 && (
              <button
                onClick={async () => {
                  try {
                    await api.post(
                      `/api/v1/projects/${project._id || project.project_id}/initialize-budgets`,
                      {},
                    );
                    mutateFinancials();
                    // also refresh project to get new master budgets
                    mutateProject();
                    toast({
                      title: "Baseline Synchronized",
                      description: "Budgetary baseline has been successfully initialized.",
                    });
                  } catch {
                    toast({
                      title: "Sync Failed",
                      description: "Failed to synchronize budget baseline.",
                      variant: "destructive",
                    });
                  }
                }}
                className="admin-only bg-orange-600 dark:bg-orange-500 hover:bg-orange-700 dark:hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-orange-500/20"
              >
                <Save size={16} /> Synchronize Budgetary Baseline
              </button>
            )}
          </div>
        </div>
      </div>

      {/* KPI Section */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Total Budget"
          value={formatCurrency(totalBudget)}
          status="neutral"
          icon={<Layout size={20} />}
          tooltip="The aggregate approved project budget across all cost categories."
        />
        <KPICard
          label="Committed"
          value={formatCurrency(totalCommitted)}
          status="warning"
          icon={<FileText size={20} />}
          tooltip="Total value of all approved Work Orders issued to vendors."
        />
        <KPICard
          label="Certified"
          value={formatCurrency(totalCertified)}
          status="positive"
          icon={<CheckSquare size={20} />}
          tooltip="Total value of work verified and approved via Payment Certificates."
        />
        <KPICard
          label="Balance"
          value={formatCurrency(totalRemaining)}
          status={totalRemaining < 0 ? "negative" : "neutral"}
          icon={<Wallet size={20} />}
          tooltip="The remaining budget available for allocation (Total Budget - Certified)."
          subtitle={totalRemaining < 0 ? "Potential Overrun" : "Safe Margin"}
        />
      </div>

      {/* Grid Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-white">
            Category-wise Financials
          </h2>
          <div className="text-[9px] text-zinc-500 dark:text-slate-500 uppercase font-black tracking-[0.2em] bg-zinc-50 dark:bg-slate-900 px-3 py-1.5 rounded-lg border border-zinc-200 dark:border-slate-800 shadow-sm transition-colors">
            Inline Modification Enabled
          </div>
        </div>

        <div className="bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm">
          <FinancialGrid
            rowData={financials || []}
            columnDefs={columnDefs}
            loading={financialsLoading}
            height="600px"
            editable={true}
            onCellValueChanged={columnDefs[1].onCellValueChanged}
          />
        </div>
      </div>

      {/* Financial Records */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <LinkedWorkOrders projectId={projectId} />
        <LinkedCertificates projectId={projectId} />
      </div>

      {/* Version Conflict Modal */}
      <VersionConflictModal
        isOpen={isConflictModalOpen}
        setIsOpen={setIsConflictModalOpen}
        onReload={() => {
          mutateFinancials();
          mutateProject();
        }}
      />
    </div>
  );
}
