import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { v4 as uuidv4 } from "uuid";

// ──────────────────────────────────────────────────────────────────────────
// CLASS NAMES UTIL
// ──────────────────────────────────────────────────────────────────────────
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ──────────────────────────────────────────────────────────────────────────
// CURRENCY FORMATTING (STRICT — 2 DECIMAL PLACES, ₹, COMMA-SEPARATED)
// All numbers come from backend. Frontend only formats for display.
// ──────────────────────────────────────────────────────────────────────────
export function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) return "₹0.00";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "0.00";
  return new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

// ──────────────────────────────────────────────────────────────────────────
// IDEMPOTENCY KEY — UUID v4 for all financial writes
// ──────────────────────────────────────────────────────────────────────────
export function generateIdempotencyKey(): string {
  return uuidv4();
}

// ──────────────────────────────────────────────────────────────────────────
// DATE FORMATTING
// ──────────────────────────────────────────────────────────────────────────
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  try {
    return new Intl.DateTimeFormat("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(dateStr));
  } catch {
    return dateStr;
  }
}

// ──────────────────────────────────────────────────────────────────────────
// 15-DAY COUNTDOWN TIMER
// Returns: { days, color }
// ──────────────────────────────────────────────────────────────────────────
export function getCountdownInfo(lastPCClosedDate: string | null | undefined): {
  days: number;
  color: "green" | "amber" | "red";
  label: string;
} {
  if (!lastPCClosedDate) {
    return { days: 0, color: "green", label: "No PC yet" };
  }
  const last = new Date(lastPCClosedDate);
  const today = new Date();
  const diffMs = today.getTime() - last.getTime();
  const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  let color: "green" | "amber" | "red" = "green";
  if (days >= 15) color = "red";
  else if (days >= 11) color = "amber";

  return {
    days,
    color,
    label: `${days} day${days !== 1 ? "s" : ""} since last PC`,
  };
}

// ──────────────────────────────────────────────────────────────────────────
// STATUS BADGE COLORS
// ──────────────────────────────────────────────────────────────────────────
export function getStatusColor(status: string): string {
  const normalized = status?.toLowerCase();
  switch (normalized) {
    case "draft":
      return "bg-gray-100 text-gray-700";
    case "pending":
    case "pending_approval":
      return "bg-yellow-100 text-yellow-700";
    case "completed":
      return "bg-blue-100 text-blue-700";
    case "closed":
      return "bg-green-100 text-green-700";
    case "approved":
      return "bg-green-100 text-green-700";
    case "cancelled":
      return "bg-red-100 text-red-700";
    case "rejected":
      return "bg-red-100 text-red-700";
    case "submitted":
      return "bg-yellow-100 text-yellow-700";
    default:
      return "bg-gray-100 text-gray-600";
  }
}
