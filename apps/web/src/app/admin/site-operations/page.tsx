"use client";

import React, { useState } from "react";
import DPRTab from "@/components/site-operations/DPRTab";
import AttendanceTab from "@/components/site-operations/AttendanceTab";
import VoiceLogsTab from "@/components/site-operations/VoiceLogsTab";
import FundsTab from "@/components/site-operations/FundsTab";
import { HardHat, FileText, Users, Mic, Wallet } from "lucide-react";
import { useSearchParams } from "next/navigation";

export default function SiteOperationsPage() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") || "dprs";
  const [activeTab, setActiveTab] = useState(initialTab);

  // Sync activeTab when searchParams change (sidebar click)
  React.useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab) {
      setActiveTab(tab);
    }
  }, [searchParams]);

  const tabs = [
    { id: "dprs", label: "DPR Review", icon: FileText },
    { id: "attendance", label: "Worker Attendance", icon: Users },
    { id: "voice-logs", label: "Voice Logs", icon: Mic },
    { id: "funds", label: "Site Funds", icon: Wallet },
  ];

  return (
    <div className="p-6 space-y-6 animate-in fade-in duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <HardHat className="text-orange-500" />
            Site Operations
          </h1>
          <p className="text-slate-500 text-sm mt-1">Review daily reports, verify attendance, and monitor site liquidity.</p>
        </div>
      </div>

      <div className="flex border-b border-slate-800 gap-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 pb-4 text-sm font-medium transition-all relative ${activeTab === tab.id ? "text-orange-500" : "text-slate-500 hover:text-slate-300"
              }`}
          >
            <tab.icon size={16} />
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 bg-orange-500 rounded-full" />
            )}
          </button>
        ))}
      </div>

      <div className="mt-6">
        {activeTab === "dprs" && <DPRTab />}
        {activeTab === "attendance" && <AttendanceTab />}
        {activeTab === "voice-logs" && <VoiceLogsTab />}
        {activeTab === "funds" && <FundsTab />}
      </div>
    </div>
  );
}
