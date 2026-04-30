"use client";

import { memo, useEffect, useState } from "react";

function clampNumber(value: string, min = 0, max = 100) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return min;
  return Math.min(max, Math.max(min, parsed));
}

type EditableCellProps = {
  value: string | number | null | undefined;
  type?: "text" | "number";
  onCommit: (value: string | number | null) => void;
  className?: string;
  readOnly?: boolean;
};

const EditableCell = memo(function EditableCell({
  value,
  type = "text",
  onCommit,
  className = "",
  readOnly = false,
}: EditableCellProps) {
  const [draft, setDraft] = useState(value ?? "");

  useEffect(() => {
    setDraft(value ?? "");
  }, [value]);

  if (readOnly) {
    return (
      <span className={`truncate font-semibold text-slate-900 dark:text-white ${className}`}>
        {value}
      </span>
    );
  }

  return (
    <input
      value={draft}
      type={type}
      onChange={(event) => setDraft(event.target.value)}
      onBlur={() => {
        const nextValue =
          type === "number"
            ? (draft === "" ? null : clampNumber(String(draft), 0, 999999))
            : (String(draft).trim() || null);

        if (nextValue === value) return;
        onCommit(nextValue);
      }}
      className={`w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-3 py-2 text-xs font-medium text-slate-900 dark:text-white outline-none transition focus:border-orange-400/40 focus:bg-slate-200 dark:focus:bg-white/[0.05] ${className}`}
    />
  );
});

EditableCell.displayName = "EditableCell";

export default EditableCell;
