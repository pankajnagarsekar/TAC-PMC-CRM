"use client";
import { useEffect, useState, Suspense } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { useProjectStore } from '@/store/projectStore';
import Sidebar from '@/components/layout/Sidebar';
import ProjectSelectorModal from '@/components/layout/ProjectSelectorModal';
import ErrorBoundary from '@/components/ui/ErrorBoundary';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { ModeToggle } from '@/components/ui/mode-toggle';
import { Breadcrumbs } from '@/components/ui/breadcrumbs';
import { cn } from '@/lib/utils';

// Register AG Grid modules globally
ModuleRegistry.registerModules([AllCommunityModule]);

export default function AdminLayout({ children }: { children: React.ReactNode }) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, accessToken, clearAuth, _hasHydrated, isClient } = useAuthStore();
    const { activeProject } = useProjectStore();
    const [showProjectModal, setShowProjectModal] = useState(false);
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    const [mounted, setMounted] = useState(false);

    // Auto-show project selector if navigating to project-scoped pages without activeProject
    useEffect(() => {
        if (!mounted || !_hasHydrated) return;

        const projectScopedRoutes = [
            '/admin/work-orders',
            '/admin/payment-certificates',
            '/admin/petty-cash',
            '/admin/site-operations',
            '/admin/site-overheads',
        ];

        const isProjectScoped = projectScopedRoutes.some(route => pathname.startsWith(route));
        const isDetailPage = /\/admin\/\w+\/[a-f0-9]{24}/.test(pathname); // MongoDB IDs

        if (isProjectScoped && !isDetailPage && !activeProject) {
            setShowProjectModal(true);
        }
    }, [pathname, activeProject, mounted, _hasHydrated]);

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
        .map((segment) => {
            let label = segment.charAt(0).toUpperCase() + segment.slice(1).replace(/-/g, ' ');

            // If segment is a MongoDB ID and matches active project, use its name
            if (activeProject && (segment === activeProject.project_id || segment === activeProject._id)) {
                label = activeProject.project_name;
            } else if (segment.match(/^[0-9a-fA-F]{24}$/)) {
                label = "Loading Project...";
            }

            return {
                label,
                href: `/admin/${segment}`
            };
        });

    if (!mounted) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-muted-foreground animate-pulse font-medium text-xs tracking-widest uppercase">
                    Initializing...
                </div>
            </div>
        );
    }

    if (!_hasHydrated) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="text-muted-foreground animate-pulse font-medium text-xs tracking-widest uppercase">
                    Authenticating...
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-screen overflow-hidden bg-background font-sans selection:bg-indigo-100 selection:text-indigo-900 dark:selection:bg-indigo-900 dark:selection:text-indigo-100">
            {/* Sidebar - Dark RuixenUI Style */}
            <Suspense fallback={<div className="w-64 h-screen bg-background animate-pulse" />}>
                <Sidebar
                    onProjectSwitch={() => setShowProjectModal(true)}
                    isCollapsed={isSidebarCollapsed}
                    onToggle={handleToggleSidebar}
                />
            </Suspense>

            <div className="flex-1 flex flex-col min-w-0 overflow-hidden py-4 pr-4">
                {/* Top Header - Floating Glass */}
                <header className="h-16 flex items-center justify-between px-8 bg-[var(--glass-background)] backdrop-blur-[var(--glass-blur)] border border-[var(--glass-border)] rounded-[var(--radius)] shadow-[var(--glass-shadow)] z-40 shrink-0 mb-4 transition-all duration-300">
                    <div className="flex items-center gap-4">
                        <Breadcrumbs items={breadcrumbItems} />
                    </div>

                    <div className="flex items-center gap-6">
                        <ModeToggle />
                        <div className="h-6 w-[1px] bg-border/50" />

                        {/* User Session */}
                        <div className="flex items-center gap-4">
                            <div className="flex flex-col items-end">
                                <span className="text-foreground text-[12px] font-bold leading-none">{user?.name}</span>
                                <span className="text-muted-foreground text-[10px] uppercase tracking-wider mt-1">{user?.role}</span>
                            </div>
                            <div className="w-10 h-10 rounded-full bg-[var(--sidebar-active)] border border-[var(--glass-border)] flex items-center justify-center text-[12px] font-black text-white shadow-lg">
                                {user?.name?.[0]?.toUpperCase()}
                            </div>
                        </div>
                    </div>
                </header>

                {/* Main Workspace - Floating Grid Area */}
                <main className={cn(
                    "flex-1 overflow-y-auto high-density-grid p-8 relative custom-scrollbar",
                    "bg-[var(--glass-background)] backdrop-blur-[var(--glass-blur)] border border-[var(--glass-border)]",
                    "rounded-[var(--radius)] shadow-[var(--glass-shadow)] transition-all duration-300",
                    isClient() && 'client-readonly'
                )}>
                    <div className="max-w-[1600px] mx-auto space-y-10">
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
