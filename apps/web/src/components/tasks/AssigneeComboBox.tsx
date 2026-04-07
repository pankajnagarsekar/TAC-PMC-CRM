import { Loader2 } from "lucide-react";
import useSWR from "swr";
import { fetcher } from "@/lib/api";
import { UserResponse } from "@/types/api";

interface AssigneeComboBoxProps {
  value: string;
  onChange: (userId: string, userName: string, userType: string) => void;
  disabled?: boolean;
}

export default function AssigneeComboBox({
  value,
  onChange,
  disabled = false,
}: AssigneeComboBoxProps) {
  const { data: users, isLoading } = useSWR<UserResponse[]>(
    "/api/v1/users/",
    fetcher
  );

  return (
    <div className="relative w-full">
      {isLoading ? (
        <div className="w-full flex items-center justify-between bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-400">
          <span className="flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin" /> Loading...
          </span>
        </div>
      ) : (
        <select
          value={value}
          onChange={(e) => {
            const selectedStr = e.target.value;
            if (selectedStr) {
              const selectedUser = users?.find(u => u.user_id === selectedStr);
              if (selectedUser) {
                onChange(selectedUser.user_id, selectedUser.name, selectedUser.role);
              }
            } else {
              onChange("", "", "");
            }
          }}
          disabled={disabled}
          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white hover:border-slate-500 transition-colors focus:border-blue-500 focus:outline-none disabled:opacity-50 appearance-none"
        >
          <option value="">Select assignee...</option>
          {users?.map((user) => (
            <option key={user.user_id} value={user.user_id}>
              {user.name} ({user.role})
            </option>
          ))}
        </select>
      )}
      {/* Custom arrow for appearance-none select */}
      {!isLoading && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      )}
    </div>
  );
}
