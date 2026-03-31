"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  ShieldCheck,
  AlertTriangle,
  Users,
  Store,
} from "lucide-react";
import api from "@/lib/api";
import { Vendor } from "@tac-pmc/types";
import FinancialGrid from "@/components/ui/FinancialGrid";
import VendorModal from "@/components/vendors/VendorModal";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import type { ColDef } from "ag-grid-community";

export default function VendorsPage() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedVendor, setSelectedVendor] = useState<Vendor | undefined>(
    undefined,
  );
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [vendorToDelete, setVendorToDelete] = useState<Vendor | null>(null);
  const { toast } = useToast();

  const fetchVendors = async () => {
    setIsLoading(true);
    try {
      const response = await api.get("/api/v1/vendors/");
      setVendors(response.data);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch vendors",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchVendors();
  }, []);

  const filteredVendors = useMemo(() => {
    if (!searchTerm) return vendors;
    const term = searchTerm.toLowerCase();
    return vendors.filter(
      (v) =>
        v.name.toLowerCase().includes(term) ||
        v.gstin?.toLowerCase().includes(term) ||
        v.contact_person?.toLowerCase().includes(term),
    );
  }, [vendors, searchTerm]);

  const handleCreate = () => {
    setSelectedVendor(undefined);
    setIsModalOpen(true);
  };

  const handleEdit = (vendor: Vendor) => {
    setSelectedVendor(vendor);
    setIsModalOpen(true);
  };

  const handleDeleteClick = (vendor: Vendor) => {
    setVendorToDelete(vendor);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!vendorToDelete) return;

    const vendorId = vendorToDelete._id || (vendorToDelete as any).id;

    try {
      await api.delete(`/api/v1/vendors/${vendorId}`);
      toast({ title: "Success", description: "Vendor deleted successfully" });
      fetchVendors();
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || "Failed to delete vendor";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setDeleteDialogOpen(false);
      setVendorToDelete(null);
    }
  };

  const columnDefs: ColDef<Vendor>[] = [
    {
      field: "name",
      headerName: "Vendor Profile",
      flex: 2,
      minWidth: 200,
      cellRenderer: (params: any) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500 border border-orange-500/20 font-bold text-[10px]">
            {params.value.substring(0, 2).toUpperCase()}
          </div>
          <span className="text-white font-bold">{params.value}</span>
        </div>
      )
    },
    { field: "gstin", headerName: "Tax Identifier", flex: 1, minWidth: 150 },
    {
      field: "contact_person",
      headerName: "Primary Contact",
      flex: 1.2,
      minWidth: 150,
      cellRenderer: (params: any) => (
        <span className="text-slate-400 font-medium">{params.value || "—"}</span>
      )
    },
    { field: "phone", headerName: "Contact Number", flex: 1, minWidth: 120 },
    {
      headerName: "Control",
      width: 120,
      pinned: "right",
      cellClass: "admin-only",
      cellRenderer: (params: { data: Vendor }) => (
        <div className="flex items-center justify-end gap-1 h-full px-2">
          <button
            onClick={() => handleEdit(params.data)}
            className="p-2 hover:bg-white/5 rounded-lg text-slate-400 hover:text-orange-500 transition-all active:scale-90"
          >
            <Edit2 size={15} />
          </button>
          <button
            onClick={() => handleDeleteClick(params.data)}
            className="p-2 hover:bg-rose-500/10 rounded-lg text-slate-500 hover:text-rose-500 transition-all active:scale-90"
          >
            <Trash2 size={15} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-700">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="space-y-1">
          <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
            <div className="p-2 bg-orange-500/10 border border-orange-500/20 rounded-2xl shadow-inner">
              <ShieldCheck size={24} className="text-orange-500" />
            </div>
            Vendor Registry
          </h1>
          <p className="text-slate-500 text-sm font-medium pl-14">
            Verified materials supply chain and resource management.
          </p>
        </div>

        <button
          onClick={handleCreate}
          className="admin-only bg-orange-600 hover:bg-orange-500 text-white px-6 py-3 rounded-[1.2rem] font-black text-xs uppercase tracking-[0.15em] flex items-center justify-center gap-3 transition-all shadow-xl shadow-orange-900/20 active:scale-95 border border-white/10"
        >
          <Plus size={18} strokeWidth={3} />
          Onboard Vendor
        </button>
      </div>

      <div className="bg-slate-900/40 border border-white/5 rounded-[2.5rem] p-6 space-y-6 shadow-2xl backdrop-blur-sm overflow-hidden">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="relative w-full md:w-96 group">
            <Search
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-orange-500 transition-colors"
              size={18}
            />
            <input
              type="text"
              placeholder="Search partner network..."
              className="w-full bg-slate-950/80 border border-white/5 rounded-2xl pl-12 pr-4 py-3 text-sm text-white focus:outline-none focus:border-orange-500/40 transition-all placeholder:text-slate-700"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div className="hidden lg:flex items-center gap-3 px-4 py-2 bg-orange-500/5 border border-orange-500/10 rounded-xl">
            <Users className="text-orange-500/50" size={14} />
            <span className="text-[10px] font-black text-orange-500/80 uppercase tracking-widest leading-none">
              {vendors.length} Total Partners Attached
            </span>
          </div>
        </div>

        {!isLoading && filteredVendors.length === 0 ? (
          <div className="empty-state-luxury min-h-[300px]">
            <div className="empty-state-luxury-icon">
              <Store size={32} />
            </div>
            <h3 className="empty-state-luxury-title">No Partners Identified</h3>
            <p className="empty-state-luxury-desc">Your verified supply chain is currently empty. Onboard your first partner to continue.</p>
          </div>
        ) : (
          <FinancialGrid
            rowData={filteredVendors}
            columnDefs={columnDefs}
            height="calc(100vh - 380px)"
            editable={false}
            quickFilterText={searchTerm}
          />
        )}
      </div>

      <VendorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={fetchVendors}
        vendor={selectedVendor}
      />

      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="bg-slate-950 border border-white/10 text-white max-w-md rounded-[2.5rem] shadow-2xl backdrop-blur-2xl">
          <DialogHeader className="p-6">
            <DialogTitle className="flex items-center gap-4 text-2xl font-black tracking-tight">
              <div className="p-2 bg-rose-500/10 rounded-xl">
                <AlertTriangle className="text-rose-500" size={24} />
              </div>
              Offboard Vendor
            </DialogTitle>
          </DialogHeader>
          <div className="px-8 py-4">
            <p className="text-slate-400 leading-relaxed font-medium">
              You are about to revoke system access for <strong className="text-white font-bold">{vendorToDelete?.name}</strong>. This action is logged for security auditing.
            </p>
            <div className="mt-6 p-4 bg-amber-500/[0.03] border border-amber-500/10 rounded-2xl">
              <p className="text-amber-500 text-xs font-bold uppercase tracking-widest text-center">
                Financial Dependency Check Required
              </p>
            </div>
          </div>
          <DialogFooter className="p-8 pt-4 flex gap-4">
            <button
              onClick={() => setDeleteDialogOpen(false)}
              className="flex-1 px-6 py-4 bg-white/5 border border-white/5 text-slate-400 font-bold rounded-2xl hover:bg-white/10 transition-all uppercase text-[10px] tracking-widest"
            >
              Cancel
            </button>
            <button
              onClick={confirmDelete}
              className="flex-1 px-6 py-4 bg-rose-600 hover:bg-rose-500 text-white font-black rounded-2xl transition-all shadow-lg shadow-rose-900/20 uppercase text-[10px] tracking-widest border border-white/10"
            >
              Confirm Offboarding
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
