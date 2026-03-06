'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useRouter } from 'next/navigation';
import {
  LayoutDashboard, FolderOpen, Users, FileText,
  CreditCard, Wallet, HardHat, BarChart2,
  Settings, LogOut, BarChart3, ChevronRight, Building2, Scan, Store, ShieldCheck
} from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import useSWR from 'swr';
import { fetcher } from '@/lib/api';
import { GlobalSettings } from '@/types/api';

const NAV_ITEMS = [
  { href: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard', key: 'dashboard' },
  { href: '/admin/clients', icon: Users, label: 'Clients', key: 'clients' },
  { href: '/admin/projects', icon: FolderOpen, label: 'Projects', key: 'projects' },
  { href: '/admin/categories', icon: LayoutDashboard, label: 'Categories', key: 'categories' },
  { href: '/admin/vendors', icon: Store, label: 'Vendors', key: 'vendors' },
  { href: '/admin/work-orders', icon: FileText, label: 'Work Orders', key: 'work_orders' },
  { href: '/admin/payment-certificates', icon: CreditCard, label: 'Payment Certificate', key: 'payment_certificates' },
  { href: '/admin/ocr', icon: Scan, label: 'AI OCR Scanner', key: 'ocr' },
  { href: '/admin/petty-cash', icon: Wallet, label: 'Petty Cash', key: 'petty_cash' },
  { href: '/admin/site-overheads', icon: Building2, label: 'Site Overheads', key: 'site_overheads' },
  { href: '/admin/site-operations', icon: HardHat, label: 'Site Operations', key: 'site_operations' },
  { href: '/admin/reports', icon: BarChart2, label: 'Reports', key: 'reports' },
  { href: '/admin/audit-log', icon: ShieldCheck, label: 'Audit Log', key: 'audit_log' },
  { href: '/admin/settings', icon: Settings, label: 'Settings', key: 'settings' },
];

interface SidebarProps {
  onProjectSwitch: () => void;
}

export default function Sidebar({ onProjectSwitch: _onProjectSwitch }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const { data: settings, error: settingsError } = useSWR<GlobalSettings>('/api/settings', fetcher);

  console.log('Sidebar: rendering...', { role: user?.role, hasSettings: !!settings, settingsError });

  async function handleLogout() {
    try {
      await api.post('/api/auth/logout');
    } catch {
      // Ignore logout API errors
    }
    clearAuth();
    document.cookie = 'crm_token=; path=/; max-age=0';
    router.replace('/login');
  }

  const filteredNavItems = NAV_ITEMS.filter(item => {
    if (user?.role === 'Client') {
      const perms = settings?.client_permissions;
      if (!perms) {
        // Fallback defaults if settings not loaded
        return ['Dashboard', 'Projects'].includes(item.label);
      }
      
      const mapping: Record<string, boolean | undefined> = {
        'Dashboard': true,
        'Projects': true,
        'Site Operations': perms.can_view_dpr,
        'Reports': perms.can_view_reports,
      };
      
      return !!mapping[item.label];
    }
    return true; // Admins see everything
  });

  return (
    <aside className="w-60 flex flex-col flex-shrink-0 h-full"
      style={{ background: '#0f172a', borderRight: '1px solid #1e293b' }}>
      {/* Logo */}
      <div className="h-14 flex items-center px-5 gap-3 border-b" style={{ borderColor: '#1e293b' }}>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: '#F97316' }}>
          <BarChart3 size={16} className="text-white" />
        </div>
        <div>
          <p className="text-white font-bold text-sm leading-none">TAC-PMC</p>
          <p className="text-slate-600 text-xs mt-0.5">CRM v2.0</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {filteredNavItems.map(({ href, icon: Icon, label }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group relative"
              style={{
                background: isActive ? 'rgba(249, 115, 22, 0.12)' : 'transparent',
                color: isActive ? '#F97316' : '#94a3b8',
              }}
              onMouseEnter={(e) => {
                if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.04)';
              }}
              onMouseLeave={(e) => {
                if (!isActive) e.currentTarget.style.background = 'transparent';
              }}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 rounded-r-full"
                  style={{ background: '#F97316' }} />
              )}
              <Icon size={17} />
              <span>{label}</span>
              {isActive && <ChevronRight size={14} className="ml-auto" />}
            </Link>
          );
        })}
      </nav>

      {/* User & Logout */}
      <div className="p-3 border-t" style={{ borderColor: '#1e293b' }}>
        <div className="flex items-center gap-3 px-3 py-2 rounded-xl mb-1"
          style={{ background: 'rgba(255,255,255,0.03)' }}>
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{ background: '#1E3A5F', color: '#F97316' }}>
            {user?.name?.[0]?.toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="text-white text-xs font-medium truncate">{user?.name}</p>
            <p className="text-slate-600 text-xs truncate">{user?.email}</p>
          </div>
        </div>
        <button
          id="logout-btn"
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all"
          style={{ color: '#64748b' }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(239,68,68,0.08)';
            e.currentTarget.style.color = '#ef4444';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = '#64748b';
          }}
        >
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
