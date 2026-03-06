import { Dispatch, SetStateAction } from "react";
import { AlertCircle } from "lucide-react";

interface VersionConflictModalProps {
  isOpen: boolean;
  setIsOpen: Dispatch<SetStateAction<boolean>>;
  onReload: () => void;
}

export default function VersionConflictModal({
  isOpen,
  setIsOpen,
  onReload,
}: VersionConflictModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 border border-slate-800 p-6 rounded-xl max-w-md w-full shadow-2xl">
        <div className="flex items-center gap-3 text-red-500 mb-4">
          <AlertCircle className="w-8 h-8" />
          <h2 className="text-xl font-semibold">Version Conflict</h2>
        </div>
        <p className="text-slate-300 mb-6">
          This record was modified in another session. To prevent overwriting their changes, your save was aborted. Please reload to view the latest changes.
        </p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => setIsOpen(false)}
            className="px-4 py-2 rounded-lg font-medium text-slate-300 hover:bg-slate-800 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => {
              setIsOpen(false);
              onReload();
            }}
            className="px-4 py-2 rounded-lg font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Reload Latest Data
          </button>
        </div>
      </div>
    </div>
  );
}
