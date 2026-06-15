"use client";

import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { ColumnType } from "@/hooks/useColumnConfig";

function clampNumber(value: string, min = 0, max = 999999) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return min;
  return Math.min(max, Math.max(min, parsed));
}

type EditableCellProps = {
  value: string | number | null | undefined;
  type?: ColumnType;
  onCommit: (value: string | number | null) => void;
  className?: string;
  readOnly?: boolean;
  /** Options for select-type cells */
  options?: { value: string; label: string }[];
  /** Called when keyboard navigation should move to the next cell */
  onNavigate?: (direction: "up" | "down" | "left" | "right") => void;
  /** Compact mode for task sheet cells (smaller padding) */
  compact?: boolean;
};

const EditableCell = memo(function EditableCell({
  value,
  type = "text",
  onCommit,
  className = "",
  readOnly = false,
  options,
  onNavigate,
  compact = false,
}: EditableCellProps) {
  const [draft, setDraft] = useState(value ?? "");
  const inputRef = useRef<HTMLInputElement | HTMLSelectElement>(null);

  useEffect(() => {
    setDraft(value ?? "");
  }, [value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        (e.target as HTMLElement).blur();
        onNavigate?.("down");
      } else if (e.key === "Escape") {
        e.preventDefault();
        setDraft(value ?? "");
        (e.target as HTMLElement).blur();
      } else if (e.key === "Tab") {
        // Let default Tab work, but also signal navigation
        onNavigate?.(e.shiftKey ? "left" : "right");
      } else if (e.key === "ArrowUp" && type !== "text") {
        e.preventDefault();
        onNavigate?.("up");
      } else if (e.key === "ArrowDown" && type !== "text") {
        e.preventDefault();
        onNavigate?.("down");
      }
    },
    [onNavigate, value, type]
  );

  const commitValue = useCallback(() => {
    let nextValue: string | number | null;

    if (type === "number" || type === "percent") {
      const max = type === "percent" ? 100 : 999999;
      nextValue = draft === "" ? null : clampNumber(String(draft), 0, max);
    } else if (type === "date") {
      nextValue = String(draft).trim() || null;
    } else {
      nextValue = String(draft).trim() || null;
    }

    if (nextValue === value) return;
    onCommit(nextValue);
  }, [draft, type, value, onCommit]);

  // Read-only or indicator — just display
  if (readOnly || type === "readonly" || type === "indicator" || type === "rownum") {
    return (
      <span
        className={`truncate text-xs font-semibold text-slate-900 dark:text-white ${className}`}
        title={String(value ?? "")}
      >
        {value ?? "—"}
      </span>
    );
  }

  const baseClass = compact
    ? "w-full bg-transparent border-none px-1.5 py-0.5 text-[11px] font-medium text-slate-900 dark:text-white outline-none transition focus:bg-slate-100 dark:focus:bg-white/[0.05] rounded"
    : "w-full rounded-xl border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/[0.03] px-3 py-2 text-xs font-medium text-slate-900 dark:text-white outline-none transition focus:border-orange-400/40 focus:bg-slate-200 dark:focus:bg-white/[0.05]";

  // Select type
  if (type === "select" && options) {
    return (
      <select
        ref={inputRef as React.RefObject<HTMLSelectElement>}
        value={String(draft)}
        onChange={(e) => {
          setDraft(e.target.value);
          onCommit(e.target.value);
        }}
        onKeyDown={handleKeyDown}
        className={`${baseClass} cursor-pointer ${className}`}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    );
  }

  // Date type
  if (type === "date") {
    const dateValue = draft ? String(draft).split("T")[0] : "";
    return (
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        type="date"
        value={dateValue}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commitValue}
        onKeyDown={handleKeyDown}
        className={`${baseClass} ${className}`}
      />
    );
  }

  // Percent type (with visual bar)
  if (type === "percent") {
    return (
      <div className="relative flex items-center gap-1">
        <input
          ref={inputRef as React.RefObject<HTMLInputElement>}
          type="number"
          min={0}
          max={100}
          step={1}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitValue}
          onKeyDown={handleKeyDown}
          className={`${baseClass} w-14 text-right pr-1 ${className}`}
        />
        {compact && (
          <div className="flex-1 h-1.5 rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
            <div
              className="h-full rounded-full bg-sky-500 transition-all duration-300"
              style={{ width: `${clampNumber(String(draft), 0, 100)}%` }}
            />
          </div>
        )}
      </div>
    );
  }

  // Number type
  if (type === "number") {
    return (
      <input
        ref={inputRef as React.RefObject<HTMLInputElement>}
        type="number"
        min={0}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commitValue}
        onKeyDown={handleKeyDown}
        className={`${baseClass} ${className}`}
      />
    );
  }

  // Default text type
  return (
    <input
      ref={inputRef as React.RefObject<HTMLInputElement>}
      value={draft}
      type="text"
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commitValue}
      onKeyDown={handleKeyDown}
      className={`${baseClass} ${className}`}
    />
  );
});

EditableCell.displayName = "EditableCell";

export default EditableCell;
