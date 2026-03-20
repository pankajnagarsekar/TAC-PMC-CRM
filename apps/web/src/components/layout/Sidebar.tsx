"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
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
} from "lucide-react";
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
    href: "/admin/petty-cash",
    icon: Wallet,
    label: "Petty Cash",
    key: "petty_cash",
  },
  {
    href: "/admin/site-overheads",
    icon: Building2,
    label: "Site Overheads",
    key: "site_overheads",
  },
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
  onProjectSwitch: _onProjectSwitch,
  isCollapsed = false,
  onToggle,
}: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
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
    <aside className={`${isCollapsed ? "w-20" : "w-64"} glass-panel-luxury border-r border-white/5 h-screen flex flex-col transition-all duration-300`}>
      {/* Logo Area */}
      <div className={`p-6 border-b border-white/5 bg-gradient-to-br from-white/[0.02] to-transparent relative ${isCollapsed ? 'flex justify-center' : ''}`}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center shadow-lg shadow-orange-500/20 glow-primary shrink-0">
            <BarChart3 size={20} className="text-white" />
          </div>
          {!isCollapsed && (
            <div className="animate-in fade-in duration-300">
              <h1 className="text-lg font-bold tracking-tight text-white leading-none">TAC PMC</h1>
              <p className="text-[10px] text-slate-500 font-medium uppercase tracking-[0.2em] mt-1">Financial Suite</p>
            </div>
          )}
        </div>

        <button
          onClick={onToggle}
          className={`absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full bg-slate-800 border border-white/10 flex items-center justify-center text-slate-400 hover:text-accent transition-all z-50 shadow-xl ${isCollapsed ? 'rotate-180' : ''}`}
        >
          <ChevronLeft size={14} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
        {filteredNavItems.map((item) => {
          const isActive = pathname === item.href || (item.children && item.children.some(c => pathname === c.href));
          return (
            <div key={item.key} className="space-y-1">
              <Link
                href={item.href}
                title={isCollapsed ? item.label : undefined}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group relative ${isActive
                  ? 'bg-accent/10 text-accent font-semibold shadow-inner'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'
                  } ${isCollapsed ? 'justify-center px-0' : ''}`}
              >
                {isActive && !isCollapsed && (
                  <div className="absolute left-0 w-1 h-6 bg-accent rounded-r-full shadow-[0_0_10px_rgba(249,115,22,0.5)]" />
                )}
                <span className={`transition-transform duration-300 ${isActive ? 'scale-110' : 'group-hover:scale-110 group-hover:text-accent'} shrink-0`}>
                  {item.icon && <item.icon size={18} />}
                </span>
                {!isCollapsed && <span className="text-sm tracking-wide truncate animate-in fade-in slide-in-from-left-2 duration-300">{item.label}</span>}
                {item.children && !isCollapsed && (
                  <ChevronRight size={14} className={`ml-auto transition-transform ${isActive ? 'rotate-90 text-accent' : 'opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0'}`} />
                )}
              </Link>

              {item.children && isActive && !isCollapsed && (
                <div className="ml-9 space-y-1">
                  {item.children.map(child => {
                    const isChildActive = pathname === child.href;
                    return (
                      <Link
                        key={child.key}
                        href={child.href}
                        className={`block py-2 px-3 text-xs rounded-lg transition-colors ${isChildActive ? 'text-accent font-medium bg-accent/5' : 'text-slate-500 hover:text-slate-300'
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

      {/* User Session */}
      <div className={`p-4 border-t border-white/5 ${isCollapsed ? 'flex justify-center' : ''}`}>
        <div className={`bg-white/5 rounded-2xl p-4 border border-white/5 glass-panel-luxury mb-3 group transition-all hover:bg-white/[0.08] ${isCollapsed ? 'p-2 rounded-xl' : ''}`}>
          <div className={`flex items-center gap-3 ${isCollapsed ? 'justify-center border-b border-white/5 pb-2 mb-2' : 'mb-3'}`}>
            <div className="w-9 h-9 rounded-xl bg-slate-800 border border-white/10 flex items-center justify-center text-sm font-bold text-orange-500 shadow-inner shrink-0">
              {user?.name?.[0]?.toUpperCase() || 'A'}
            </div>
            {!isCollapsed && (
              <div className="flex-1 min-w-0 animate-in fade-in duration-300">
                <p className="text-xs font-bold text-white truncate leading-tight">{user?.name || 'Admin User'}</p>
                <p className="text-[10px] text-slate-400 truncate">{user?.email || 'admin@tacpmc.in'}</p>
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            title={isCollapsed ? "Sign Out" : undefined}
            className={`w-full py-2 px-4 rounded-xl bg-slate-800/50 hover:bg-red-500/10 text-slate-400 hover:text-red-400 text-[11px] font-semibold transition-all border border-white/5 flex items-center justify-center gap-2 ${isCollapsed ? 'px-0 border-none bg-transparent hover:bg-transparent' : ''}`}
          >
            <LogOut size={14} />
            {!isCollapsed && <span>Sign Out</span>}
          </button>
        </div>
      </div>
    </aside>
  );
}
