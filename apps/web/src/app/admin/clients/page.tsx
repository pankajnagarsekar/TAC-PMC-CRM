"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import FinancialGrid from "@/components/ui/FinancialGrid";
import {
  Users,
  Plus,
  Search,
  Edit2,
  MoreHorizontal,
  Mail,
  Phone,
  Building2,
  CheckCircle2,
  XCircle,
  Trash2,
} from "lucide-react";
import { fetcher } from "@/lib/api";
import api from "@/lib/api";
import { Client } from "@/types/api";
import ClientModal from "@/components/clients/ClientModal";
import { formatDate } from "@tac-pmc/ui";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";

export default function ClientsPage() {
  const {
    data: clients,
    mutate,
    isLoading,
  } = useSWR<Client[]>("/api/clients", fetcher);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Client | undefined>(
    undefined,
  );
  const [deleteClient, setDeleteClient] = useState<Client | null>(null);
  const { toast } = useToast();

  const columnDefs: any[] = useMemo(
    () => [
      {
        headerName: "Client Name",
        field: "client_name",
        flex: 2,
        cellRenderer: (params: any) => (
          <div className="flex items-center gap-3 py-2">
            <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-600 dark:text-orange-500">
              <Building2 size={16} />
            </div>
            <span className="font-semibold text-zinc-900 dark:text-white">{(params.data as any).name || (params.data as any).client_name}</span>
          </div>
        ),
      },
      {
        headerName: "Contact Details",
        field: "client_email",
        flex: 2,
        cellRenderer: (params: any) => (
          <div className="flex flex-col justify-center py-1">
            <div className="flex items-center gap-2 text-slate-300 text-xs">
              <Mail size={12} className="text-slate-500" />
              {(params.data as any).email || (params.data as any).client_email || "No email"}
            </div>
            <div className="flex items-center gap-2 text-slate-500 text-xs mt-1">
              <Phone size={12} />
              {(params.data as any).phone || (params.data as any).client_phone || "No phone"}
            </div>
          </div>
        ),
      },
      {
        headerName: "GST Number",
        field: "gst_number",
        flex: 1,
        cellRenderer: (params: any) => (
          <code className="text-[11px] bg-zinc-100 dark:bg-slate-900 px-2 py-0.5 rounded border border-zinc-200 dark:border-slate-800 text-zinc-600 dark:text-slate-400">
            {(params.data as any).gstin || (params.data as any).gst_number || "N/A"}
          </code>
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
        headerName: "Created",
        field: "created_at",
        width: 130,
        valueFormatter: (params: any) => formatDate(params.value),
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
              title="Edit Client"
            >
              <Edit2 size={16} />
            </button>
            <button
              onClick={() => handleDelete(params.data)}
              className="p-2 hover:bg-red-50 dark:hover:bg-red-800 rounded-lg text-zinc-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              title="Delete Client"
            >
              <Trash2 size={16} />
            </button>
          </div>
        ),
      },
    ],
    [],
  );

  function handleEdit(client: Client) {
    setSelectedClient(client);
    setIsModalOpen(true);
  }

  function handleDelete(client: Client) {
    setDeleteClient(client);
  }

  function handleAddNew() {
    setSelectedClient(undefined);
    setIsModalOpen(true);
  }

  async function confirmDelete() {
    if (!deleteClient) return;
    try {
      await api.delete(`/api/clients/${deleteClient._id}`);
      mutate();
      setDeleteClient(null);
      toast({ title: "Success", description: "Client deleted successfully" });
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.response?.data?.detail || "Failed to delete client",
        variant: "destructive",
      });
    }
  }

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white flex items-center gap-3">
            <Users className="text-orange-500" />
            Client Management
          </h1>
          <p className="text-zinc-500 dark:text-slate-500 text-sm mt-1">
            Manage construction clients, billing info and project associations.
          </p>
        </div>

        <button
          onClick={handleAddNew}
          className="admin-only bg-orange-600 hover:bg-orange-500 text-white px-4 py-2.5 rounded-xl font-semibold text-sm flex items-center gap-2 transition-all shadow-lg shadow-orange-900/20 active:scale-95"
        >
          <Plus size={18} />
          Add New Client
        </button>
      </div>

      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-4 items-center justify-between bg-white dark:bg-slate-900/50 p-4 rounded-2xl border border-zinc-200 dark:border-slate-800/50">
        <div className="relative w-full sm:w-80">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-slate-500"
            size={18}
          />
          <input
            type="text"
            placeholder="Search by name, email or GST..."
            className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500/50 transition-colors"
            value={searchTerm}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSearchTerm(e.target.value)
            }
          />
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
          <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
          {clients?.length || 0} Clients Found
        </div>
      </div>

      {/* Grid */}
      <div className="relative">
        {!isLoading && (!clients || clients.length === 0) ? (
          <div className="empty-state-luxury min-h-[400px]">
            <div className="empty-state-luxury-icon">
              <Users size={32} />
            </div>
            <h3 className="empty-state-luxury-title">No Clients Logged</h3>
            <p className="empty-state-luxury-desc">Your strategic stakeholder database is empty. Add a client to link with project assets.</p>
          </div>
        ) : (
          <FinancialGrid
            rowData={clients || []}
            columnDefs={columnDefs}
            quickFilterText={searchTerm}
            loading={isLoading}
            height="500px"
          />
        )}
      </div>

      <ClientModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={() => mutate()}
        client={selectedClient}
      />

      {/* Delete Confirmation Dialog */}
      {deleteClient && (
        <Dialog
          open={!!deleteClient}
          onOpenChange={() => setDeleteClient(null)}
        >
          <DialogContent className="max-w-md bg-slate-950 border-slate-800 text-white">
            <DialogHeader>
              <DialogTitle className="text-lg flex items-center gap-2">
                <Trash2 className="text-red-500" />
                Delete Client
              </DialogTitle>
            </DialogHeader>
            <div className="py-4">
              <p className="text-slate-300">
                Are you sure you want to delete{" "}
                <strong>{deleteClient.client_name}</strong>? This action cannot
                be undone and will deactivate the client.
              </p>
            </div>
            <DialogFooter>
              <button
                onClick={() => setDeleteClient(null)}
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
