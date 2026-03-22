"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  FolderOpen,
  FileText,
  CreditCard,
  Wallet,
  HardHat,
  BarChart2,
  Settings,
  LogOut,
  BarChart3,
  ChevronRight,
  Building2,
  Scan,
  Store,
  ShieldCheck,
  CalendarDays,
  ChevronLeft,
  ChevronsUpDown,
} from "lucide-react";
import { useProjectStore } from "@/store/projectStore";
import { useAuthStore } from "@/store/authStore";
import api from "@/lib/api";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { GlobalSettings } from "@/types/api";

interface NavItem {
  href: string;
  icon?: any;
  label: string;
  key: string;
  children?: NavItem[];
}

const NAV_ITEMS: NavItem[] = [
  {
    href: "/admin/dashboard",
    icon: LayoutDashboard,
    label: "Dashboard",
    key: "dashboard",
  },
  { href: "/admin/clients", icon: Users, label: "Clients", key: "clients" },
  {
    href: "/admin/projects",
    icon: FolderOpen,
    label: "Projects",
    key: "projects",
  },
  {
    href: "/admin/scheduler",
    icon: CalendarDays,
    label: "Project Scheduler",
    key: "scheduler",
  },
  {
    href: "/admin/categories",
    icon: LayoutDashboard,
    label: "Categories",
    key: "categories",
  },
  { href: "/admin/vendors", icon: Store, label: "Vendors", key: "vendors" },
  {
    href: "/admin/work-orders",
    icon: FileText,
    label: "Work Orders",
    key: "work_orders",
  },
  {
    href: "/admin/payment-certificates",
    icon: CreditCard,
    label: "Payment Certificate",
    key: "payment_certificates",
  },
  { href: "/admin/ocr", icon: Scan, label: "AI OCR Scanner", key: "ocr" },
  {
    href: "/admin/site-operations",
    icon: HardHat,
    label: "Site Operations",
    key: "site_operations",
    children: [
      { href: "/admin/site-operations?tab=dprs", label: "DPRs", key: "dprs" },
      {
        href: "/admin/site-operations?tab=attendance",
        label: "Attendance",
        key: "attendance",
      },
      {
        href: "/admin/site-operations?tab=voice-logs",
        label: "Voice Logs",
        key: "voice_logs",
      },
      {
        href: "/admin/site-operations?tab=funds",
        label: "Site Funds",
        key: "funds",
      },
    ],
  },
  { href: "/admin/reports", icon: BarChart2, label: "Reports", key: "reports" },
  {
    href: "/admin/audit-log",
    icon: ShieldCheck,
    label: "Audit Log",
    key: "audit_log",
  },
  {
    href: "/admin/settings",
    icon: Settings,
    label: "Settings",
    key: "settings",
  },
];

interface SidebarProps {
  onProjectSwitch?: () => void;
  isCollapsed?: boolean;
  onToggle?: () => void;
}

export default function Sidebar({
  onProjectSwitch,
  isCollapsed = false,
  onToggle,
}: SidebarProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const { activeProject } = useProjectStore();
  const { data: settings } = useSWR<GlobalSettings>(
    "/api/settings",
    fetcher
  );

  async function handleLogout() {
    try {
      await api.post("/api/auth/logout");
    } catch {
      // Ignore logout API errors
    }
    clearAuth();
    document.cookie = "crm_token=; path=/; max-age=0";
    router.replace("/login");
  }

  const filteredNavItems = NAV_ITEMS.filter((item) => {
    if (user?.role === "Client") {
      const perms = settings?.client_permissions;
      if (!perms) {
        return ["Dashboard", "Projects"].includes(item.label);
      }

      const mapping: Record<string, boolean | undefined> = {
        Dashboard: true,
        Projects: true,
        "Site Operations": perms.can_view_dpr,
        Reports: perms.can_view_reports,
      };

      return !!mapping[item.label];
    }
    return true;
  });

  return (
    <div className={`${isCollapsed ? "w-24" : "w-64"} h-screen p-3 flex flex-col transition-all duration-300 z-50`}>
      <aside className="h-full flex flex-col bg-[var(--glass-background)] backdrop-blur-[var(--glass-blur)] border border-[var(--glass-border)] shadow-[var(--glass-shadow)] rounded-[var(--radius)] overflow-hidden">
        {/* Brand & Project Switcher */}
        <div className="flex flex-col border-b border-sidebar-border/50">
          <div className={`h-14 flex items-center px-4 shrink-0 ${isCollapsed ? 'justify-center px-0' : ''}`}>
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-sidebar-active flex items-center justify-center shrink-0">
                <BarChart3 size={18} className="text-sidebar-active-foreground" />
              </div>
              {!isCollapsed && (
                <h1 className="text-sm font-bold tracking-tight text-sidebar-foreground uppercase">TAC CRM</h1>
              )}
            </div>

            <button
              onClick={onToggle}
              className={`absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-sidebar border border-sidebar-border flex items-center justify-center text-sidebar-foreground/60 hover:text-sidebar-foreground transition-all shadow-md ${isCollapsed ? 'rotate-180' : ''}`}
            >
              <ChevronLeft size={14} />
            </button>
          </div>

          {/* Project Switcher Trigger */}
          {!isCollapsed && (
            <div className="px-3 pb-4">
              <button
                onClick={onProjectSwitch}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-md bg-sidebar-accent/50 border border-sidebar-border hover:bg-sidebar-accent transition-all text-left group"
              >
                <div className="w-5 h-5 rounded bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                  <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400">
                    {activeProject?.project_code?.[0] || 'P'}
                  </span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-medium text-sidebar-foreground truncate">
                    {activeProject?.project_name || 'Select Project'}
                  </p>
                  {activeProject && (
                    <p className="text-[9px] text-sidebar-foreground/60 font-mono tracking-tighter truncate">
                      {activeProject.project_code}
                    </p>
                  )}
                </div>
                <ChevronsUpDown size={12} className="text-sidebar-foreground/40 group-hover:text-sidebar-foreground/60" />
              </button>
            </div>
          )}
        </div>

        {/* Navigation - RuixenUI Style */}
        <nav className="flex-1 overflow-y-auto pt-2 px-3 space-y-0.5 custom-scrollbar">
          {filteredNavItems.map((item) => {
            const isActive = pathname === item.href || (item.children && item.children.some(c => pathname === c.href));
            return (
              <div key={item.key} className="space-y-0.5">
                <Link
                  href={item.href}
                  title={isCollapsed ? item.label : undefined}
                  className={`flex items-center gap-3 px-3 py-2 rounded-md transition-all duration-200 group relative ${isActive
                    ? 'bg-sidebar-active text-sidebar-active-foreground font-medium'
                    : 'text-sidebar-foreground/60 hover:bg-sidebar-accent/40 hover:text-sidebar-foreground'
                    } ${isCollapsed ? 'justify-center px-0' : ''}`}
                >
                  {isActive && (
                    <div className="absolute left-0 w-[2px] h-4 bg-sidebar-active-foreground rounded-r-full" />
                  )}
                  <span className={`shrink-0 transition-colors ${isActive ? 'text-sidebar-active-foreground' : 'group-hover:text-sidebar-foreground'}`}>
                    {item.icon && <item.icon size={16} strokeWidth={isActive ? 2.5 : 2} />}
                  </span>
                  {!isCollapsed && (
                    <span className="text-[13px] tracking-normal truncate">{item.label}</span>
                  )}
                </Link>

                {item.children && isActive && !isCollapsed && (
                  <div className="ml-7 my-1 border-l border-sidebar-border space-y-0.5">
                    {item.children.map(child => {
                      const childPath = child.href.split('?')[0];
                      const childTab = new URLSearchParams(child.href.split('?')[1]).get('tab');
                      const isSideChildActive = pathname === childPath && (childTab ? searchParams.get('tab') === childTab : true);

                      return (
                        <Link
                          key={child.key}
                          href={child.href}
                          className={`block py-1.5 px-4 text-[12px] transition-all duration-200 ${isSideChildActive
                            ? 'text-sidebar-active font-bold border-l-2 border-sidebar-active -ml-[1px] pl-[15px] bg-sidebar-active/5'
                            : 'text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent/30'
                            }`}
                        >
                          {child.label}
                        </Link>
                      )
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>

        {/* Footer Area - Refined Session */}
        <div className="p-3 border-t border-sidebar-border">
          <div className={`p-2 rounded-lg bg-sidebar-accent/30 border border-sidebar-border ${isCollapsed ? 'flex justify-center' : ''}`}>
            {!isCollapsed && (
              <div className="flex items-center gap-3 mb-2 px-1">
                <div className="w-7 h-7 rounded-full bg-sidebar-accent border border-sidebar-border flex items-center justify-center text-[10px] font-bold text-sidebar-active shrink-0">
                  {user?.name?.[0]?.toUpperCase() || 'A'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-bold text-sidebar-foreground truncate">{user?.name || 'Admin'}</p>
                  <p className="text-[9px] text-sidebar-foreground/60 truncate">{user?.email}</p>
                </div>
              </div>
            )}
            <button
              onClick={handleLogout}
              className={`w-full py-1.5 rounded-md hover:bg-red-500/10 text-sidebar-foreground/60 hover:text-red-400 text-[11px] font-medium transition-all flex items-center justify-center gap-2 ${isCollapsed ? 'w-8 h-8 p-0 rounded-full' : ''}`}
            >
              <LogOut size={13} />
              {!isCollapsed && <span>Sign Out</span>}
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
