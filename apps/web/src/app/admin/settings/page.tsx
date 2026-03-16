"use client";

import { useState, useEffect, useRef } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import api from "@/lib/api";
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
} from "lucide-react";
import { CodeMaster } from "@/types/api";
import CategoryModal from "@/components/categories/CategoryModal";

export default function SettingsPage() {
  const { data: codes, mutate: mutateCodes } = useSWR<CodeMaster[]>(
    "/api/codes",
    fetcher,
  );
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<
    CodeMaster | undefined
  >(undefined);

  const [loading, setLoading] = useState(true);
  const [globalSettings, setGlobalSettings] = useState<any>({
    cgst_percentage: 9.0,
    sgst_percentage: 9.0,
    retention_percentage: 5.0,
    currency: "INR",
    currency_symbol: "₹",
    terms_and_conditions: "Standard terms and conditions apply...",
    company_profile: {
      name: "TAC PMC",
      address: "",
      registration_no: "",
      contact_email: "",
    },
    logo_base64: null,
    client_permissions: {
      can_view_dpr: true,
      can_view_financials: false,
      can_view_reports: true,
    },
  });

  const [savingSettings, setSavingSettings] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const [settingsRes, permsRes] = await Promise.all([
          api.get("/api/settings"),
          api.get("/api/settings/client-permissions"),
        ]);

        if (settingsRes.data) {
          setGlobalSettings({
            ...settingsRes.data,
            client_permissions:
              permsRes.data || settingsRes.data.client_permissions,
          });
        }
      } catch (err) {
        console.log("Settings not initialized yet or endpoint missing.");
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  const handleSaveSettings = async () => {
    setSavingSettings(true);
    try {
      const { client_permissions, ...baseSettings } = globalSettings;
      await Promise.all([
        api.put("/api/settings", baseSettings),
        api.patch("/api/settings/client-permissions", client_permissions || {}),
      ]);
      alert("Global settings saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to save settings.");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleLogoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setGlobalSettings({ ...globalSettings, logo_base64: reader.result });
      };
      reader.readAsDataURL(file);
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
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="text-orange-500" />
            Global Settings
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Manage company identity and system-wide financial taxonomies.
          </p>
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
          Apply Global Changes
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Company Profile & Logo */}
        <div className="lg:col-span-1 space-y-6">
          {/* Logo Section */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
              <Globe size={16} className="text-orange-500" />
              Company Branding
            </h3>

            <div className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-slate-800 rounded-xl bg-slate-950/50 group hover:border-orange-500/50 transition-colors">
              {globalSettings.logo_base64 ? (
                <div className="relative group/img">
                  <img
                    src={globalSettings.logo_base64}
                    alt="Company Logo"
                    className="max-h-24 rounded-lg object-contain"
                  />
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
                  <div className="w-12 h-12 rounded-full bg-slate-900 flex items-center justify-center text-slate-500 group-hover:text-orange-500 transition-colors border border-slate-800">
                    <Upload size={20} />
                  </div>
                  <span className="text-xs text-slate-500 font-medium">
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
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-4">
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
              <Building2 size={16} className="text-orange-500" />
              Company Profile
            </h3>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 uppercase">
                  Registered Name
                </label>
                <input
                  type="text"
                  value={globalSettings.company_profile?.name}
                  onChange={(e) =>
                    setGlobalSettings({
                      ...globalSettings,
                      company_profile: {
                        ...globalSettings.company_profile,
                        name: e.target.value,
                      },
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                  placeholder="e.g. TAC Project Management Consultants"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 uppercase">
                  Office Address
                </label>
                <textarea
                  rows={3}
                  value={globalSettings.company_profile?.address}
                  onChange={(e) =>
                    setGlobalSettings({
                      ...globalSettings,
                      company_profile: {
                        ...globalSettings.company_profile,
                        address: e.target.value,
                      },
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 resize-none"
                  placeholder="Enter full physical address..."
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-500 uppercase">
                  Registration No / GST
                </label>
                <input
                  type="text"
                  value={globalSettings.company_profile?.registration_no}
                  onChange={(e) =>
                    setGlobalSettings({
                      ...globalSettings,
                      company_profile: {
                        ...globalSettings.company_profile,
                        registration_no: e.target.value,
                      },
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500"
                  placeholder="e.g. CIN/GSTIN Number"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Middle Column: Financial Defaults & Permissions */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 space-y-6 shadow-xl h-full">
            <h2 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
              <Hash size={16} className="text-orange-500" />
              Financial Controls
            </h2>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-tighter">
                  CGST (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={globalSettings.cgst_percentage}
                  onChange={(e) =>
                    setGlobalSettings({
                      ...globalSettings,
                      cgst_percentage: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 text-center font-mono"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-slate-400 uppercase tracking-tighter">
                  SGST (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={globalSettings.sgst_percentage}
                  onChange={(e) =>
                    setGlobalSettings({
                      ...globalSettings,
                      sgst_percentage: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 text-center font-mono"
                />
              </div>
              <div className="space-y-2 col-span-2">
                <label className="text-xs font-medium text-slate-400 uppercase">
                  Retention Hold (%)
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={globalSettings.retention_percentage}
                  onChange={(e) =>
                    setGlobalSettings({
                      ...globalSettings,
                      retention_percentage: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500 font-mono"
                />
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
                        onChange={(e) =>
                          setGlobalSettings({
                            ...globalSettings,
                            client_permissions: {
                              ...globalSettings.client_permissions,
                              [key]: e.target.checked,
                            },
                          })
                        }
                        className="w-4 h-4 accent-orange-500"
                      />
                    </label>
                  ),
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Category Taxonomy */}
        <div className="lg:col-span-1">
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
