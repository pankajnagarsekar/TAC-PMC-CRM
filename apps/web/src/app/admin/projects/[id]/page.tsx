"use client";

import { useState, useMemo, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { AgGridReact } from "ag-grid-react";
import { ColDef } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import {
  ArrowLeft,
  TrendingUp,
  Wallet,
  FileText,
  AlertTriangle,
  Loader2,
  Save,
  CheckCircle2,
  ExternalLink,
  MapPin,
  Building2,
} from "lucide-react";
import api, { fetcher } from "@/lib/api";
import { Project, DerivedFinancialState } from "@/types/api";
import { formatCurrency, formatDate } from "@tac-pmc/ui";
import { useProjectStore } from "@/store/projectStore";
import VersionConflictModal from "@/components/ui/VersionConflictModal";
import LinkedCertificates from "@/components/work-orders/LinkedCertificates";
import KPICard from "@/components/ui/KPICard";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const { setActiveProject } = useProjectStore();

  const { data: project, mutate: mutateProject } = useSWR<Project>(
    `/api/projects/${projectId}`,
    fetcher,
  );
  const {
    data: financials,
    mutate: mutateFinancials,
    isLoading: financialsLoading,
  } = useSWR<DerivedFinancialState[]>(
    `/api/v2/projects/${projectId}/financials`,
    fetcher,
  );

  const [savingId, setSavingId] = useState<string | null>(null);
  const [isConflictModalOpen, setIsConflictModalOpen] = useState(false);

  // Sync project context for dashboard compatibility
  useEffect(() => {
    if (project) {
      setActiveProject(project);
    }
  }, [project, setActiveProject]);

  const columnDefs: ColDef<DerivedFinancialState>[] = useMemo(
    () => [
      {
        headerName: "Category/Code",
        field: "category_id",
        flex: 1.5,
        cellRenderer: (params: any) => (
          <div className="flex flex-col justify-center py-1">
            <span className="font-semibold text-white">{params.value}</span>
            {params.data.over_commit_flag && (
              <span className="text-[9px] text-red-500 font-bold uppercase tracking-tighter">
                Budget Overrun
              </span>
            )}
          </div>
        ),
      },
      {
        headerName: "Approved Budget",
        field: "original_budget",
        flex: 1.2,
        editable: true,
        cellEditor: "agNumberCellEditor",
        cellEditorParams: {
          min: 0,
          precision: 2,
        },
        cellClass: "bg-orange-500/5 font-mono text-orange-400",
        valueFormatter: (params: any) => formatCurrency(params.value),
        onCellValueChanged: async (params: any) => {
          const { _id, original_budget, version } = params.data;
          if (!_id) return;

          setSavingId(_id);
          try {
            // Note: In our current schema, _id in DerivedFinancialState refers to the ProjectBudget ID
            await api.put(`/api/v2/budgets/${_id}`, {
              original_budget: parseFloat(original_budget),
              version: version,
            });
            mutateFinancials();
          } catch (err: any) {
            if (err.response?.status === 409) {
              setIsConflictModalOpen(true);
            } else {
              alert("Failed to update budget. Please check permissions.");
            }
            params.node.setDataValue("original_budget", params.oldValue);
          } finally {
            setSavingId(null);
          }
        },
      },
      {
        headerName: "Committed (WOs)",
        field: "committed_value",
        flex: 1.2,
        cellClass: "text-slate-300 font-mono",
        valueFormatter: (params: any) => formatCurrency(params.value),
      },
      {
        headerName: "Certified (PCs)",
        field: "certified_value",
        flex: 1.2,
        cellClass: "text-slate-400 font-mono",
        valueFormatter: (params: any) => formatCurrency(params.value),
      },
      {
        headerName: "Remaining",
        field: "balance_budget_remaining",
        flex: 1.2,
        cellRenderer: (params: any) => {
          const isNegative = params.value < 0;
          return (
            <span
              className={`font-mono font-bold ${isNegative ? "text-red-500" : "text-emerald-500"}`}
            >
              {formatCurrency(params.value)}
            </span>
          );
        },
      },
    ],
    [mutateFinancials],
  );

  if (!project || financialsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-orange-500 animate-spin" />
      </div>
    );
  }

  // Aggregate Totals
  const totalBudget =
    financials?.reduce((sum, f) => sum + (f.original_budget || 0), 0) ?? 0;
  const totalCommitted =
    financials?.reduce((sum, f) => sum + (f.committed_value || 0), 0) ?? 0;
  const totalCertified =
    financials?.reduce((sum, f) => sum + (f.certified_value || 0), 0) ?? 0;
  const totalRemaining =
    financials?.reduce(
      (sum, f) => sum + (f.balance_budget_remaining || 0),
      0,
    ) ?? 0;

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <button
          onClick={() => router.push("/admin/projects")}
          className="flex items-center gap-2 text-slate-500 hover:text-white transition-colors text-sm w-fit"
        >
          <ArrowLeft size={16} /> Back to Projects
        </button>

        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold text-white flex items-center gap-3">
              {project.project_name}
              <span className="text-xs bg-slate-800 px-2 py-0.5 rounded font-mono text-slate-400 uppercase">
                {project.project_code}
              </span>
            </h1>
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <MapPin size={12} /> {project.address || "No address set"}
              </span>
              <span className="flex items-center gap-1">
                <Building2 size={12} />{" "}
                {project.client_name || "Direct Project"}
              </span>
            </div>
          </div>

          <div className="flex flex-col items-end gap-2">
            <div className="bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-full text-[10px] font-bold text-emerald-500 uppercase">
              {project.status}
            </div>
            {financials && financials.length === 0 && (
              <button
                onClick={async () => {
                  try {
                    await api.post(
                      `/api/v2/projects/${project._id || project.project_id}/initialize-budgets`,
                      {},
                    );
                    mutateFinancials();
                    // also refresh project to get new master budgets
                    mutateProject();
                  } catch (err) {
                    alert("Failed to initialize budgets.");
                  }
                }}
                className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-colors mt-2"
              >
                <Save size={16} /> Initialize Budgets
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
        />
        <KPICard
          label="Total Committed"
          value={formatCurrency(totalCommitted)}
          status="warning"
        />
        <KPICard
          label="Total Certified"
          value={formatCurrency(totalCertified)}
          status="positive"
        />
        <KPICard
          label="Budget Balance"
          value={formatCurrency(totalRemaining)}
          status={totalRemaining < 0 ? "negative" : "neutral"}
          subtitle={totalRemaining < 0 ? "Potential Overrun" : "Safe Margin"}
        />
      </div>

      {/* Grid Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">
            Category-wise Financials
          </h2>
          <div className="text-[10px] text-slate-500 uppercase font-bold tracking-widest bg-slate-900 px-3 py-1 rounded-lg border border-slate-800">
            Double-click budget to edit
          </div>
        </div>

        <div className="ag-theme-alpine-dark w-full h-[600px] border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative">
          {savingId && (
            <div className="absolute inset-0 z-10 bg-slate-950/20 backdrop-blur-[1px] flex items-center justify-center">
              <Loader2 className="w-6 h-6 text-orange-500 animate-spin" />
            </div>
          )}
          <AgGridReact
            rowData={financials}
            columnDefs={columnDefs}
            defaultColDef={{
              sortable: true,
              filter: true,
              resizable: true,
            }}
            onGridReady={(params) => params.api.sizeColumnsToFit()}
          />
        </div>
      </div>

      {/* Linked Certificates section */}
      <LinkedCertificates projectId={projectId} />

      {/* Version Conflict Modal */}
      <VersionConflictModal
        isOpen={isConflictModalOpen}
        setIsOpen={setIsConflictModalOpen}
        onReload={() => {
          mutateFinancials();
          mutateProject();
        }}
      />

      <style jsx global>{`
        .ag-theme-alpine-dark {
          --ag-background-color: #020617;
          --ag-header-background-color: #0f172a;
          --ag-border-color: #1e293b;
          --ag-secondary-border-color: #1e293b;
          --ag-header-foreground-color: #94a3b8;
          --ag-data-color: #f8fafc;
          --ag-odd-row-background-color: #020617;
          --ag-row-hover-color: rgba(249, 115, 22, 0.05);
          --ag-selected-row-background-color: rgba(249, 115, 22, 0.1);
        }
        .ag-header-cell-label {
          justify-content: start;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-size: 11px;
        }
      `}</style>
    </div>
  );
}


