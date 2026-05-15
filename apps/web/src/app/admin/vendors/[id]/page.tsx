"use client";

import React, { useState, useMemo } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Briefcase,
  CreditCard,
  FileText,
  BadgeCheck,
  Building2,
  Phone,
  UserCircle,
  IndianRupee
} from "lucide-react";
import FinancialGrid from "@/components/ui/FinancialGrid";
import KPICard from "@/components/ui/KPICard";
import { GlassCard } from "@/components/ui/GlassCard";
import type { ColDef } from "ag-grid-community";

export default function VendorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const vendorId = params.id as string;

  const [activeTab, setActiveTab] = useState<"wos" | "pcs" | "ledger">("wos");

  // Fetch Vendor Profile
  const { data: vendor, isLoading: isVendorLoading } = useSWR(
    `/api/v1/vendors/${vendorId}`,
    fetcher
  );

  // Fetch Vendor Stats
  const { data: stats } = useSWR(
    `/api/v1/contracting/vendors/${vendorId}/stats`,
    fetcher
  );

  // Fetch Linked WOs
  const { data: wos = [] } = useSWR(
    `/api/v1/contracting/work-orders?vendor_id=${vendorId}`,
    fetcher
  );

  // Fetch Payment History
  const { data: pcs = [] } = useSWR(
    `/api/v1/financial/payments/all/history/vendor/${vendorId}`,
    fetcher
  );

  // Fetch Ledger
  const { data: ledger = [] } = useSWR(
    `/api/v1/contracting/vendors/${vendorId}/ledger`,
    fetcher
  );

  const formatCurrency = (val: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(val || 0);

  // Column Definitions
  const woColumnDefs = useMemo<ColDef[]>(
    () => [
      { field: "project_id", headerName: "Project", flex: 1 },
      { field: "wo_ref", headerName: "WO Ref", flex: 1 },
      { field: "title", headerName: "Title", flex: 2 },
      { field: "status", headerName: "Status", flex: 1 },
      { 
        field: "grand_total", 
        headerName: "Value", 
        flex: 1,
        valueFormatter: (params) => formatCurrency(params.value)
      },
    ],
    []
  );

  const pcColumnDefs = useMemo<ColDef[]>(
    () => [
      { field: "pc_ref", headerName: "PC Ref", flex: 1 },
      { field: "project_id", headerName: "Project", flex: 1 },
      { field: "status", headerName: "Status", flex: 1 },
      { 
        field: "grand_total", 
        headerName: "Amount Certified", 
        flex: 1,
        valueFormatter: (params) => formatCurrency(params.value)
      },
      { 
        field: "payment_status", 
        headerName: "Payment Status", 
        flex: 1 
      },
      { 
        field: "paid_amount", 
        headerName: "Amount Paid", 
        flex: 1,
        valueFormatter: (params) => formatCurrency(params.value)
      },
    ],
    []
  );

  const ledgerColumnDefs = useMemo<ColDef[]>(
    () => [
      { field: "created_at", headerName: "Date", flex: 1, valueFormatter: (params) => params.value ? new Date(params.value).toLocaleDateString() : "—" },
      { field: "project_id", headerName: "Project", flex: 1 },
      { field: "entry_type", headerName: "Type", flex: 1 },
      { 
        field: "flow_direction", 
        headerName: "Direction", 
        flex: 0.8,
        cellRenderer: (params: any) => {
          const val = params.value || "UNKNOWN";
          const isOut = val === "OUTFLOW";
          return (
            <span className={`font-bold text-[10px] uppercase tracking-widest ${isOut ? "text-rose-500" : "text-emerald-500"}`}>
              {val}
            </span>
          );
        }
      },
      { 
        field: "amount", 
        headerName: "Amount", 
        flex: 1,
        valueFormatter: (params) => formatCurrency(params.value)
      },
    ],
    []
  );

  if (isVendorLoading) {
    return <div className="p-6 text-slate-400">Loading vendor details...</div>;
  }

  if (!vendor) {
    return <div className="p-6 text-rose-500">Vendor not found</div>;
  }

  return (
    <div className="p-6 space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-700">
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.push("/admin/vendors")}
          className="p-2 bg-white/5 hover:bg-white/10 rounded-xl text-slate-400 hover:text-white transition-all"
        >
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-3xl font-black text-white tracking-tight flex items-center gap-4">
          <div className="p-2 bg-orange-500/10 border border-orange-500/20 rounded-2xl shadow-inner">
            <Building2 size={24} className="text-orange-500" />
          </div>
          {vendor.name}
        </h1>
        {vendor.gstin && (
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
            <BadgeCheck size={14} className="text-emerald-500" />
            <span className="text-[10px] font-bold text-emerald-500 tracking-widest uppercase">
              Verified GSTIN
            </span>
          </div>
        )}
      </div>

      {/* Header Card */}
      <GlassCard className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">GSTIN</p>
          <p className="text-white font-medium">{vendor.gstin || "—"}</p>
        </div>
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1 flex items-center gap-2">
            <UserCircle size={14} /> Contact Person
          </p>
          <p className="text-white font-medium">{vendor.contact_person || "—"}</p>
        </div>
        <div>
          <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1 flex items-center gap-2">
            <Phone size={14} /> Phone
          </p>
          <p className="text-white font-medium">{vendor.phone || "—"}</p>
        </div>
      </GlassCard>

      {/* Financial Summary Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          label="Total Work Orders"
          value={wos.length}
          icon={<Briefcase size={20} />}
          status="neutral"
        />
        <KPICard
          label="Total Certified"
          value={formatCurrency(stats?.total_certified || 0)}
          icon={<BadgeCheck size={20} />}
          status="positive"
        />
        <KPICard
          label="Total Paid"
          value={formatCurrency(stats?.total_paid || 0)}
          icon={<CreditCard size={20} />}
          status="positive"
        />
        <KPICard
          label="Retention Held"
          value={formatCurrency(stats?.total_retention || 0)}
          icon={<IndianRupee size={20} />}
          status="warning"
        />
      </div>

      {/* Tabbed Content */}
      <div className="bg-slate-900/40 border border-white/5 rounded-[2.5rem] p-6 shadow-2xl backdrop-blur-sm">
        <div className="flex gap-4 mb-6 border-b border-white/10 pb-4">
          <button
            onClick={() => setActiveTab("wos")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all ${
              activeTab === "wos"
                ? "bg-orange-500/10 text-orange-500 border border-orange-500/20"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Briefcase size={16} /> Work Orders
          </button>
          <button
            onClick={() => setActiveTab("pcs")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all ${
              activeTab === "pcs"
                ? "bg-orange-500/10 text-orange-500 border border-orange-500/20"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <FileText size={16} /> Payment History
          </button>
          <button
            onClick={() => setActiveTab("ledger")}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all ${
              activeTab === "ledger"
                ? "bg-orange-500/10 text-orange-500 border border-orange-500/20"
                : "text-slate-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <IndianRupee size={16} /> Ledger
          </button>
        </div>

        <div>
          {activeTab === "wos" && (
            <FinancialGrid
              rowData={wos}
              columnDefs={woColumnDefs}
              height="400px"
              editable={false}
            />
          )}
          {activeTab === "pcs" && (
            <FinancialGrid
              rowData={pcs}
              columnDefs={pcColumnDefs}
              height="400px"
              editable={false}
            />
          )}
          {activeTab === "ledger" && (
            <FinancialGrid
              rowData={ledger}
              columnDefs={ledgerColumnDefs}
              height="400px"
              editable={false}
            />
          )}
        </div>
      </div>
    </div>
  );
}
