"use client";

import React, { useState, useEffect } from "react";
import { Users, Plus, Shield, Search, UserCheck, UserX, Pencil } from "lucide-react";
import api from "@/lib/api";
import { UserResponse } from "@tac-pmc/types";
import FinancialGrid from "@/components/ui/FinancialGrid";
import { useToast } from "@/hooks/use-toast";
import { ColDef } from "ag-grid-community";
import { CreateUserModal } from "@/components/users/CreateUserModal";
import { EditUserModal } from "@/components/users/EditUserModal";

export default function TeamPage() {
    const [users, setUsers] = useState<UserResponse[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [createOpen, setCreateOpen] = useState(false);
    const [editUser, setEditUser] = useState<UserResponse | null>(null);
    const [deactivatingId, setDeactivatingId] = useState<string | null>(null);
    const { toast } = useToast();

    const fetchUsers = async () => {
        try {
            setLoading(true);
            const response = await api.get("/api/v1/users/");
            setUsers(response.data);
        } catch (error) {
            console.error("Failed to fetch users:", error);
            toast({
                title: "Error",
                description: "Failed to load team members",
                variant: "destructive",
            });
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleDeactivate = async (userId: string) => {
        setDeactivatingId(userId);
        try {
            await api.delete(`/api/v1/users/${userId}`);
            toast({
                title: "Success",
                description: "User deactivated successfully",
                variant: "default"
            });
            fetchUsers();
        } catch (error) {
            console.error("Failed to deactivate user:", error);
            toast({
                title: "Error",
                description: "Failed to deactivate user",
                variant: "destructive"
            });
        } finally {
            setDeactivatingId(null);
        }
    };

    const columnDefs: ColDef[] = [
        {
            field: "name",
            headerName: "Member Name",
            flex: 2,
            cellRenderer: (params: any) => (
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-orange-500/10 flex items-center justify-center text-orange-500 font-bold text-xs">
                        {params.value.charAt(0)}
                    </div>
                    <span className="text-white font-medium">{params.value}</span>
                </div>
            )
        },
        { field: "email", headerName: "Email Address", flex: 2 },
        {
            field: "role",
            headerName: "Role",
            flex: 1,
            cellRenderer: (params: any) => (
                <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border ${params.value === 'Admin'
                    ? 'bg-rose-500/10 text-rose-500 border-rose-500/20'
                    : params.value === 'Client'
                        ? 'bg-orange-500/10 text-orange-500 border-orange-500/20'
                        : 'bg-blue-500/10 text-blue-500 border-blue-500/20'
                    }`}>
                    {params.value}
                </span>
            )
        },
        {
            field: "active_status",
            headerName: "Status",
            flex: 1,
            cellRenderer: (params: any) => (
                <div className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${params.value ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-700'}`} />
                    <span className={params.value ? 'text-emerald-500' : 'text-slate-500'}>
                        {params.value ? 'Active' : 'Inactive'}
                    </span>
                </div>
            )
        },
        {
            headerName: "Actions",
            flex: 1,
            cellRenderer: (params: any) => (
                <div className="flex gap-2 items-center h-full">
                    <button
                        onClick={() => setEditUser(params.data)}
                        className="admin-only p-1 rounded-lg text-slate-400 hover:text-orange-400 transition-colors"
                        title="Edit user"
                    >
                        <Pencil size={14} />
                    </button>
                    <button
                        onClick={() => handleDeactivate(params.data.user_id)}
                        disabled={!params.data.active_status || deactivatingId === params.data.user_id}
                        className="admin-only p-1 rounded-lg text-slate-400 hover:text-rose-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        title="Deactivate user"
                    >
                        <UserX size={14} />
                    </button>
                </div>
            )
        }
    ];

    return (
        <div className="p-6 space-y-6 animate-in fade-in duration-500">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-3">
                        <Users className="text-orange-500" />
                        Team Management
                    </h1>
                    <p className="text-slate-500 text-sm mt-1">Manage user roles, permissions, and system access.</p>
                </div>

                <button
                    onClick={() => setCreateOpen(true)}
                    className="px-5 py-2.5 bg-orange-600 hover:bg-orange-500 text-white rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-lg shadow-orange-500/20 active:scale-95"
                >
                    <Plus size={18} /> Invite Member
                </button>
            </div>

            <div className="bg-slate-900/40 border border-white/5 rounded-[2rem] p-6 space-y-6">
                <div className="relative max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                    <input
                        type="text"
                        placeholder="Search by name or email..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors"
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />
                </div>

                <FinancialGrid
                    columnDefs={columnDefs}
                    rowData={users}
                    loading={loading}
                    height="calc(100vh - 350px)"
                    quickFilterText={searchTerm}
                />
            </div>

            <CreateUserModal
                open={createOpen}
                onClose={() => setCreateOpen(false)}
                onCreated={fetchUsers}
            />

            <EditUserModal
                user={editUser}
                onClose={() => setEditUser(null)}
                onUpdated={fetchUsers}
            />
        </div>
    );
}
