"use client";
import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useProjectStore } from '@/store/projectStore';
import Sidebar from '@/components/layout/Sidebar';
import ProjectSelectorModal from '@/components/layout/ProjectSelectorModal';
import ErrorBoundary from '@/components/ui/ErrorBoundary';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { ModeToggle } from '@/components/ui/mode-toggle';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';

// Register AG Grid modules globally
ModuleRegistry.registerModules([AllCommunityModule]);

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, accessToken, clearAuth, _hasHydrated } = useAuthStore();
    const { activeProject } = useProjectStore();
    const [showProjectModal, setShowProjectModal] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [mounted, setMounted] = useState(false);

    useEffect(() => {
        setMounted(true);
        if (typeof window !== 'undefined') {
            const savedState = localStorage.getItem('sidebar-collapsed');
            if (savedState === 'true') {
                setIsSidebarCollapsed(true);
            }
        }
    }, []);

    const handleToggleSidebar = () => {
        const newState = !isSidebarCollapsed;
        setIsSidebarCollapsed(newState);
        localStorage.setItem('sidebar-collapsed', String(newState));
    };

    // Auth guard
    useEffect(() => {
        if (!mounted || !_hasHydrated) return;

        if (!accessToken || !user) {
            router.replace('/login');
            return;
        }

        if (user.role !== 'Admin' && user.role !== 'Client') {
            clearAuth();
            router.replace('/login');
            return;
        }
    }, [accessToken, user, router, clearAuth, mounted, _hasHydrated]);

    // Derive breadcrumbs from pathname
    const breadcrumbItems = pathname
        .split('/')
        .filter(Boolean)
        .slice(1) // Skip 'admin'
        .map((segment) => ({
            label: segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' '),
            href: `/admin/${segment}`
        }));

    if (!mounted || !_hasHydrated) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-zinc-500 animate-pulse font-medium text-xs tracking-widest uppercase">
                    Authenticating...
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen overflow-hidden bg-background font-sans selection:bg-indigo-100 selection:text-indigo-900 dark:selection:bg-indigo-900 dark:selection:text-indigo-100">
            {/* Sidebar - Dark RuixenUI Style */}
            <Sidebar
                onProjectSwitch={() => setShowProjectModal(true)}
                isCollapsed={isSidebarCollapsed}
                onToggle={handleToggleSidebar}
            />

            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                {/* Top Header - Glass & Minimalist */}
                <header className="h-14 flex items-center justify-between px-6 bg-background/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800 z-40 shrink-0">
                    <div className="flex items-center gap-4">
                        <Breadcrumbs items={breadcrumbItems} />
                    </div>

                    <div className="flex items-center gap-4">
                        <ModeToggle />
                        <div className="h-5 w-[1px] bg-zinc-200 dark:bg-zinc-800" />

                        {/* User Session */}
                        <div className="flex items-center gap-3">
                            <div className="flex flex-col items-end">
                                <span className="text-foreground text-[11px] font-bold leading-none">{user.name}</span>
                                <span className="text-muted-foreground text-[9px] uppercase tracking-wider mt-0.5">{user.role}</span>
                            </div>
                            <div className="w-8 h-8 rounded-full bg-secondary border border-zinc-200 dark:border-zinc-800 flex items-center justify-center text-[10px] font-black text-indigo-500">
                                {user.name?.[0]?.toUpperCase()}
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Workspace - High Density Grid Background */}
                <main className="flex-1 overflow-y-auto high-density-grid p-6 relative custom-scrollbar bg-white dark:bg-zinc-950">
                    <div className="max-w-[1700px] mx-auto space-y-8">
                        <ErrorBoundary>
                            {children}
                        </ErrorBoundary>
                    </div>
                </main>
            </div>

            {/* Project Selector Overlay */}
            {showProjectModal && (
                <ProjectSelectorModal onClose={() => setShowProjectModal(false)} />
            )}
        </div>
    );
}
