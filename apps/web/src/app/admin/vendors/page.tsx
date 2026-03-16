"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Plus,
  Search,
  Edit2,
  Trash2,
  ShieldCheck,
  AlertTriangle,
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
      const response = await api.get("/api/vendors");
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
      await api.delete(`/api/vendors/${vendorId}`);
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

  const handleDelete = async (vendorId: string) => {
    // Find the vendor object
    const vendor = vendors.find((v) => (v._id || (v as any).id) === vendorId);
    if (vendor) {
      handleDeleteClick(vendor);
    }
  };

  const columnDefs: ColDef<Vendor>[] = [
    { field: "name", headerName: "Vendor Name", flex: 2, minWidth: 200 },
    { field: "gstin", headerName: "GSTIN", flex: 1, minWidth: 150 },
    {
      field: "contact_person",
      headerName: "Contact Person",
      flex: 1.2,
      minWidth: 150,
    },
    { field: "phone", headerName: "Phone", flex: 1, minWidth: 120 },
    {
      headerName: "Actions",
      width: 100,
      pinned: "right",
      cellRenderer: (params: { data: Vendor }) => (
        <div className="flex items-center gap-2 h-full admin-only">
          <button
            onClick={() => handleEdit(params.data)}
            className="p-1 hover:text-orange-500 transition-colors"
          >
            <Edit2 size={14} />
          </button>
          <button
            onClick={() => handleDeleteClick(params.data)}
            className="p-1 hover:text-red-500 transition-colors"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-500">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="text-orange-500" />
            Vendor Management
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Manage all construction vendors and material suppliers
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="admin-only flex items-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-medium transition-all shadow-lg shadow-orange-500/20 active:scale-95"
        >
          <Plus size={18} />
          Add Vendor
        </button>
      </div>

      <div className="bg-[#1e293b]/50 border border-slate-800 rounded-2xl p-4">
        <div className="relative mb-6">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
            size={18}
          />
          <input
            type="text"
            placeholder="Search vendors by name, GSTIN, or contact..."
            className="w-full bg-[#0f172a] border border-slate-700 rounded-xl py-2.5 pl-10 pr-4 text-white focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all"
            value={searchTerm}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              setSearchTerm(e.target.value)
            }
          />
        </div>

        <FinancialGrid
          rowData={filteredVendors}
          columnDefs={columnDefs}
          height="calc(100vh - 280px)"
          editable={false}
          className="rounded-xl overflow-hidden border border-slate-700"
        />
      </div>

      <VendorModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={fetchVendors}
        vendor={selectedVendor}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-md rounded-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3 text-xl font-bold">
              <AlertTriangle className="text-red-500" size={24} />
              Delete Vendor
            </DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-slate-300">
              Are you sure you want to delete{" "}
              <strong className="text-white">{vendorToDelete?.name}</strong>?
            </p>
            <div className="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl">
              <p className="text-amber-500 text-sm">
                This vendor will be deactivated. If they have linked Work
                Orders, deletion will be blocked.
              </p>
            </div>
          </div>
          <DialogFooter className="flex gap-3">
            <button
              onClick={() => setDeleteDialogOpen(false)}
              className="flex-1 px-4 py-2 border border-slate-700 text-slate-300 rounded-xl hover:bg-slate-900 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={confirmDelete}
              className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-xl font-medium transition-colors"
            >
              Delete Vendor
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
