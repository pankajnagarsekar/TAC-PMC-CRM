"use client";

import { useState, useEffect, useRef } from "react";
import { z } from "zod";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import api from "@/lib/api";
import { sanitizeText } from "@/lib/sanitize";
import {
  Save,
  Settings,
  Hash,
  Loader2,
  Plus,
  Edit2,
  Building2,
  Upload,
  X,
  Globe,
  LayoutGrid,
  RefreshCcw,
  RotateCcw,
} from "lucide-react";
import Link from "next/link";
import NextImage from "next/image";
import { CodeMaster, GlobalSettings } from "@/types/api";
import CategoryModal from "@/components/categories/CategoryModal";
import { useToast } from "@/hooks/use-toast";
import { useUnsavedChanges } from "@/hooks/use-unsaved-changes";

const settingsSchema = z.object({
  cgst_percentage: z.number().min(0).max(100),
  sgst_percentage: z.number().min(0).max(100),
  retention_percentage: z.number().min(0).max(100),
  email: z.string().email().optional().or(z.literal("")),
});

export default function SettingsPage() {
  const { data: codes, error: codesError, mutate: mutateCodes } = useSWR<CodeMaster[]>(
    "/api/v1/settings/codes",
    fetcher,
  );
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<
    CodeMaster | undefined
  >(undefined);

  const [loading, setLoading] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [globalSettings, setGlobalSettings] = useState<GlobalSettings>({
    organisation_id: "",
    name: "TAC PMC",
    address: "",
    email: "",
    phone: "",
    gst_number: "",
    pan_number: "",
    cgst_percentage: 9.0,
    sgst_percentage: 9.0,
    retention_percentage: 5.0,
    wo_prefix: "WO",
    pc_prefix: "PC",
    invoice_prefix: "INV",
    currency: "INR",
    currency_symbol: "₹",
    terms_and_conditions: "1. All work must be performed in accordance with the project specifications and standard safety protocols.\n2. Payment terms: Net 30 days from the date of approved certification.\n3. Variations must be pre-approved via official Change Order.\n4. Retention of 5% will be held until final completion and handover.",
    logo_base64: null,
    client_permissions: {
      can_view_dpr: true,
      can_view_financials: false,
      can_view_reports: true,
      can_view_scheduler: false,
    },
  });

  const [savingSettings, setSavingSettings] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // Guard against unsaved changes
  useUnsavedChanges(isDirty);

  const handleClearCache = async () => {
    try {
      await api.post("/api/v1/settings/clear-cache");
      toast({ title: "System cache purged successfully" });
    } catch {
      toast({ title: "Failed to purge cache", variant: "destructive" });
    }
  };

  const handleResetDashboard = () => {
    if (confirm("This will reset all dashboard layouts to default. Proceed?")) {
      Object.keys(localStorage).forEach(key => {
        if (key.startsWith('dashboard_')) {
          localStorage.removeItem(key);
        }
      });
      toast({ title: "Dashboard configuration reset" });
      window.location.reload();
    }
  };

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const settingsRes = await api.get("/api/v1/settings/");

        if (settingsRes.data) {
          setGlobalSettings((prev) => ({
            ...prev,
            ...settingsRes.data,
          }));
          // Reset dirty state after fetch
          setIsDirty(false);
        }
      } catch (err) {
        console.error("Settings not initialized yet or endpoint missing:", err);
        toast({
          title: "System Error",
          description: "Could not fetch global settings from the server. Using local defaults.",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, [toast]);

  useEffect(() => {
    if (codesError) {
      toast({
        title: "Category Fetch Error",
        description: "Failed to fetch master categories. Please check your network connection.",
        variant: "destructive",
      });
    }
  }, [codesError, toast]);

  const handleSaveSettings = async () => {
    // BUG-004: Strict validation
    const validation = settingsSchema.safeParse({
      cgst_percentage: globalSettings.cgst_percentage,
      sgst_percentage: globalSettings.sgst_percentage,
      retention_percentage: globalSettings.retention_percentage,
      email: globalSettings.email,
    });

    if (!validation.success) {
      toast({
        title: "Validation Error",
        description: "Please check your inputs: percentages must be 0-100 and email must be valid.",
        variant: "destructive",
      });
      return;
    }

    setSavingSettings(true);
    try {
      const payload = prepareSettingsPayload();
      await api.put("/api/v1/settings/", payload);
      setIsDirty(false); // Reset dirty state
      toast({
        title: "Success",
        description: "Global settings synchronized successfully across all modules.",
      });
    } catch (err: unknown) {
      console.error(err);
      const error = err as { response?: { data?: { detail?: string | { message?: string } } } };
      const errData = error.response?.data;
      const detail = (errData as { detail?: string; message?: string })?.detail || (errData as { detail?: string; message?: string })?.message || "Encountered a server error while attempting to sync settings.";
      toast({
        title: "Update Failed",
        description: Array.isArray(detail) ? JSON.stringify(detail) : detail,
        variant: "destructive",
      });
    } finally {
      setSavingSettings(false);
    }
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setGlobalSettings({ ...globalSettings, logo_base64: reader.result as string });
      };
      reader.readAsDataURL(file);
    }
  };

  // Flatten settings for API (move logo handling to top-level)
  const prepareSettingsPayload = () => {
    const { client_permissions, logo_base64, ...baseSettings } = globalSettings;
    return {
      ...baseSettings,
      name: sanitizeText(baseSettings.name),
      address: sanitizeText(baseSettings.address),
      email: sanitizeText(baseSettings.email),
      phone: sanitizeText(baseSettings.phone),
      gst_number: sanitizeText(baseSettings.gst_number),
      pan_number: sanitizeText(baseSettings.pan_number),
      wo_prefix: sanitizeText(baseSettings.wo_prefix),
      pc_prefix: sanitizeText(baseSettings.pc_prefix),
      invoice_prefix: sanitizeText(baseSettings.invoice_prefix),
      currency: sanitizeText(baseSettings.currency),
      currency_symbol: sanitizeText(baseSettings.currency_symbol),
      terms_and_conditions: sanitizeText(baseSettings.terms_and_conditions),
      client_permissions,
      logo_base64,
      expected_version: globalSettings.version || 1,
    };
  };

  const handleNumericChange = (key: keyof GlobalSettings, rawValue: string) => {
    // If empty string, keep it as 0 but allow user to clear the field.
    // Fixed BUG-004: Don't silently convert 'abc' to 0. 
    // If it's not a number, don't update state or use old value.
    setIsDirty(true);
    if (rawValue === "") {
      setGlobalSettings(prev => ({ ...prev, [key]: 0 }));
      return;
    }
    const parsed = parseFloat(rawValue);
    if (!isNaN(parsed)) {
      let clamped = parsed;
      if (key === 'cgst_percentage' || key === 'sgst_percentage' || key === 'retention_percentage') {
        clamped = Math.max(0, Math.min(100, parsed));
      } else {
        clamped = Math.max(0, parsed);
      }
      setGlobalSettings(prev => ({ ...prev, [key]: clamped }));
    }
  };

  if (loading)
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    );

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-500">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-white flex items-center gap-3">
            <Settings className="text-orange-500" />
            Global Settings
          </h1>
          <div className="flex items-center gap-4 mt-1">
            <p className="text-zinc-500 dark:text-slate-500 text-sm">
              Manage company identity and system-wide financial taxonomies.
            </p>
            <span className="w-1 h-1 rounded-full bg-zinc-300 dark:bg-zinc-700" />
            <Link
              href="/admin/settings/projects"
              className="text-xs font-bold text-orange-500 hover:text-orange-400 flex items-center gap-1.5 transition-colors uppercase tracking-wider"
            >
              <LayoutGrid size={14} />
              Access Project Registry
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="admin-only flex items-center gap-2 px-3 py-1.5 bg-slate-100 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl mr-4">
            <span className="text-[10px] font-black text-zinc-400 dark:text-slate-500 uppercase tracking-widest mr-2">Maintenance</span>
            <button
              onClick={handleClearCache}
              className="p-2 text-zinc-500 hover:text-orange-500 transition-all"
              title="Purge Application Cache"
            >
              <RefreshCcw size={16} />
            </button>
            <button
              onClick={async () => {
                if (confirm("This will recalculate master budgets for all projects. This might take a moment. Proceed?")) {
                  try {
                    await api.post("/api/v1/settings/recalculate-financials");
                    toast({ title: "Financial reconciliation complete" });
                  } catch {
                    toast({ title: "Recalculation failed", variant: "destructive" });
                  }
                }
              }}
              className="p-2 text-zinc-500 hover:text-indigo-500 transition-all border-l border-zinc-200 dark:border-slate-800 ml-1 pl-3"
              title="Force Financial Recalculation"
            >
              <div className="flex items-center gap-2">
                <Settings size={16} />
                <span className="text-[9px] font-bold uppercase tracking-tight">Financials</span>
              </div>
            </button>
            <button
              onClick={handleResetDashboard}
              className="p-2 text-zinc-500 hover:text-orange-500 transition-all"
              title="Reset Dashboard Configuration"
            >
              <RotateCcw size={16} />
            </button>
          </div>

          <button
            onClick={handleSaveSettings}
            disabled={savingSettings}
            className="admin-only bg-orange-600 hover:bg-orange-500 text-white px-6 py-2.5 rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-orange-900/20 disabled:opacity-50"
          >
            {savingSettings ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Commit System Configuration
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Company Profile & Logo */}
        <div className="lg:col-span-1 space-y-6">
          {/* Logo Section */}
          <div className="bg-white dark:bg-slate-900/50 border border-zinc-200 dark:border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
            <h3 className="text-sm font-semibold text-zinc-800 dark:text-white uppercase tracking-wider flex items-center gap-2">
              <Globe size={16} className="text-orange-500" />
              Company Branding
            </h3>

            <div className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-zinc-200 dark:border-slate-800 rounded-xl bg-zinc-50/50 dark:bg-slate-950/50 group hover:border-orange-500/50 transition-colors">
              {globalSettings.logo_base64 ? (
                <div className="relative group/img">
                  <div className="relative h-24 w-24">
                    <NextImage
                      src={globalSettings.logo_base64}
                      alt="Company Logo"
                      fill
                      className="rounded-lg object-contain"
                      unoptimized
                    />
                  </div>
                  <button
                    onClick={() =>
                      setGlobalSettings({
                        ...globalSettings,
                        logo_base64: null,
                      })
                    }
                    className="absolute -top-2 -right-2 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover/img:opacity-100 transition-opacity"
                  >
                    <X size={12} />
                  </button>
                </div>
              ) : (
                <div
                  className="flex flex-col items-center gap-2 cursor-pointer"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <div className="w-12 h-12 rounded-full bg-zinc-100 dark:bg-slate-900 flex items-center justify-center text-zinc-400 dark:text-slate-500 group-hover:text-orange-500 transition-colors border border-zinc-200 dark:border-slate-800">
                    <Upload size={20} />
                  </div>
                  <span className="text-xs text-zinc-500 dark:text-slate-500 font-medium">
                    Upload Company Logo
                  </span>
                </div>
              )}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleLogoUpload}
                accept="image/*"
                className="hidden"
              />
            </div>
          </div>

          {/* Profile Fields */}
          <div className="bg-white dark:bg-slate-900/50 border border-zinc-200 dark:border-slate-800 rounded-2xl p-6 space-y-4 shadow-sm">
            <h3 className="text-sm font-semibold text-zinc-800 dark:text-white uppercase tracking-wider flex items-center gap-2">
              <Building2 size={16} className="text-orange-500" />
              Company Profile
            </h3>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-zinc-400 dark:text-slate-500 uppercase">
                  Registered Name
                </label>
                <input
                  type="text"
                  value={globalSettings.name}
                  onChange={(e) => {
                    setIsDirty(true);
                    setGlobalSettings({
                      ...globalSettings,
                      name: e.target.value,
                    });
                  }}
                  className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl px-4 py-2.5 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500"
                  placeholder="e.g. TAC Project Management Consultants"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-zinc-400 dark:text-slate-500 uppercase">
                  Office Address
                </label>
                <textarea
                  rows={3}
                  value={globalSettings.address}
                  onChange={(e) => {
                    setIsDirty(true);
                    setGlobalSettings({
                      ...globalSettings,
                      address: e.target.value,
                    });
                  }}
                  className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl px-4 py-2.5 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500 resize-none"
                  placeholder="Enter full physical address..."
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 uppercase">
                    Email
                  </label>
                  <input
                    type="email"
                    value={globalSettings.email}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        email: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                    placeholder="company@email.com"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 uppercase">
                    Phone
                  </label>
                  <input
                    type="text"
                    value={globalSettings.phone}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        phone: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                    placeholder="+91 98765 43210"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 uppercase">
                    GST Number
                  </label>
                  <input
                    type="text"
                    value={globalSettings.gst_number}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        gst_number: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                    placeholder="27AAAPL1234C1Z5"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-slate-500 uppercase">
                    PAN Number
                  </label>
                  <input
                    type="text"
                    value={globalSettings.pan_number}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        pan_number: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                    placeholder="AAAPL1234C"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Middle Column: Financial Defaults, Prefixes & Permissions */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl h-full">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
              <Hash size={16} className="text-orange-500" />
              Financial Controls
            </h2>

            {/* Tax Rates */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-tighter">
                  CGST (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={globalSettings.cgst_percentage}
                  onChange={(e) => handleNumericChange('cgst_percentage', e.target.value)}
                  className={`w-full bg-slate-950 border ${globalSettings.cgst_percentage > 100 || globalSettings.cgst_percentage < 0 ? 'border-red-500' : 'border-slate-800'} rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 text-center font-mono`}
                  min={0}
                  max={100}
                />
                {(globalSettings.cgst_percentage > 100 || globalSettings.cgst_percentage < 0) && (
                  <p className="text-[10px] text-red-500 mt-1 uppercase font-bold text-center">Invalid Range</p>
                )}
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-tighter">
                  SGST (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={globalSettings.sgst_percentage}
                  onChange={(e) => handleNumericChange('sgst_percentage', e.target.value)}
                  className={`w-full bg-slate-950 border ${globalSettings.sgst_percentage > 100 || globalSettings.sgst_percentage < 0 ? 'border-red-500' : 'border-slate-800'} rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 text-center font-mono`}
                  min={0}
                  max={100}
                />
                {(globalSettings.sgst_percentage > 100 || globalSettings.sgst_percentage < 0) && (
                  <p className="text-[10px] text-red-500 mt-1 uppercase font-bold text-center">Invalid Range</p>
                )}
              </div>
              <div className="space-y-2 col-span-2">
                <label className="text-xs font-medium text-slate-400 uppercase">
                  Retention Hold (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={globalSettings.retention_percentage}
                  onChange={(e) => handleNumericChange('retention_percentage', e.target.value)}
                  className={`w-full bg-slate-950 border ${globalSettings.retention_percentage > 100 || globalSettings.retention_percentage < 0 ? 'border-red-500' : 'border-slate-800'} rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 font-mono`}
                  min={0}
                  max={100}
                />
                {(globalSettings.retention_percentage > 100 || globalSettings.retention_percentage < 0) && (
                  <p className="text-[10px] text-red-500 mt-1 uppercase font-bold">Invalid Range (0-100%)</p>
                )}
              </div>
            </div>

            {/* Document Prefixes */}
            <div className="border-t border-slate-800 pt-6 space-y-4">
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Document Prefixes
              </h3>
              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-2">
                  <label className="text-[10px] font-medium text-slate-500 uppercase">
                    WO Prefix
                  </label>
                  <input
                    type="text"
                    value={globalSettings.wo_prefix}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        wo_prefix: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500 text-center font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-medium text-slate-500 uppercase">
                    PC Prefix
                  </label>
                  <input
                    type="text"
                    value={globalSettings.pc_prefix}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        pc_prefix: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500 text-center font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-medium text-slate-500 uppercase">
                    Invoice Prefix
                  </label>
                  <input
                    type="text"
                    value={globalSettings.invoice_prefix}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        invoice_prefix: e.target.value,
                      });
                    }}
                    className="w-full bg-zinc-50 dark:bg-slate-950 border border-zinc-200 dark:border-slate-800 rounded-xl px-3 py-2 text-sm text-zinc-900 dark:text-white focus:outline-none focus:border-orange-500 text-center font-mono"
                  />
                </div>
              </div>
            </div>

            {/* Currency */}
            <div className="border-t border-slate-800 pt-6 space-y-4">
              <h3 className="text-xs font-semibold text-white uppercase tracking-wider">
                Currency
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <label className="text-[10px] font-medium text-slate-500 uppercase">
                    Currency
                  </label>
                  <input
                    type="text"
                    value={globalSettings.currency}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        currency: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500"
                    placeholder="INR"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-medium text-slate-500 uppercase">
                    Symbol
                  </label>
                  <input
                    type="text"
                    value={globalSettings.currency_symbol}
                    onChange={(e) => {
                      setIsDirty(true);
                      setGlobalSettings({
                        ...globalSettings,
                        currency_symbol: e.target.value,
                      });
                    }}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500 text-center font-mono"
                    placeholder="₹"
                  />
                </div>
              </div>
            </div>

            <div className="border-t border-slate-800 pt-6 space-y-4">
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                Client View Access
              </h2>
              <div className="grid grid-cols-1 gap-2">
                {Object.entries(globalSettings.client_permissions || {}).map(
                  ([key, val]) => (
                    <label
                      key={key}
                      className="flex items-center justify-between p-3 bg-slate-950/50 border border-slate-800 rounded-xl cursor-pointer hover:border-slate-700 transition-colors group"
                    >
                      <span className="text-xs text-slate-400 font-medium group-hover:text-white transition-colors capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <input
                        type="checkbox"
                        checked={!!val}
                        onChange={(e) => {
                          setIsDirty(true);
                          setGlobalSettings({
                            ...globalSettings,
                            client_permissions: {
                              ...globalSettings.client_permissions,
                              [key]: e.target.checked,
                            },
                          });
                        }}
                        className="w-4 h-4 accent-orange-500"
                      />
                    </label>
                  ),
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Terms & Category Taxonomy */}
        <div className="lg:col-span-1 space-y-6">
          {/* Terms & Conditions */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
              Terms & Conditions
            </h2>
            <textarea
              rows={6}
              value={globalSettings.terms_and_conditions}
              onChange={(e) =>
                setGlobalSettings({
                  ...globalSettings,
                  terms_and_conditions: e.target.value,
                })
              }
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-orange-500 resize-none"
              placeholder="Enter standard terms and conditions..."
            />
          </div>

          {/* Category Master */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl h-full flex flex-col">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white uppercase tracking-wider">
                Category Master
              </h2>
              <button
                onClick={() => {
                  setSelectedCategory(undefined);
                  setIsCategoryModalOpen(true);
                }}
                className="text-orange-500 hover:text-orange-400 text-xs font-bold flex items-center gap-1 transition-colors"
              >
                <Plus size={14} />
                NEW
              </button>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto pr-1">
              {codesError && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-center">
                  <p className="text-xs font-semibold text-red-500">Failed to load categories</p>
                  <p className="text-[10px] text-red-400 mt-1">Please try again later</p>
                </div>
              )}
              {!codes && !codesError && (
                <div className="p-4 text-center text-xs text-zinc-500 dark:text-slate-500">
                  Loading categories...
                </div>
              )}
              {codes?.map((code) => (
                <div
                  key={code._id}
                  className="group flex items-center justify-between p-3 bg-slate-950/50 border border-slate-800 hover:border-slate-600 rounded-xl transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center text-slate-500 group-hover:bg-orange-500/10 group-hover:text-orange-500 transition-colors">
                      <Hash size={14} />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white uppercase tracking-tight">
                        {code.category_name}
                      </h4>
                      <p className="text-[9px] text-slate-600 font-mono">
                        {code.code}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedCategory(code);
                      setIsCategoryModalOpen(true);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-500 hover:text-white transition-all bg-slate-900 rounded-md"
                  >
                    <Edit2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <CategoryModal
        isOpen={isCategoryModalOpen}
        onClose={() => setIsCategoryModalOpen(false)}
        onSuccess={() => mutateCodes()}
        category={selectedCategory}
      />
    </div>
  );
}
