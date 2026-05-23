"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import { Coins, Loader2, Upload, AlertCircle, Info, Calendar, Sparkles, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { format, eachMonthOfInterval, isValid } from "date-fns";
import api from "@/lib/api";
import { Project } from "@/types/api";
import { formatCurrencySafe } from "@/lib/formatters";

interface MonthlyPlannedValue {
  month: string;
  planned_value: number;
  cumulative_value: number;
}

interface EVMBaselineModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  project: Project;
}

export default function EVMBaselineModal({
  isOpen,
  onClose,
  onSuccess,
  project,
}: EVMBaselineModalProps) {
  const [totalContractValue, setTotalContractValue] = useState<string>("");
  const [startDate, setStartDate] = useState<string>("");
  const [endDate, setEndDate] = useState<string>("");
  const [distributionType, setDistributionType] = useState<"linear" | "csv">("linear");
  const [csvType, setCsvType] = useState<"incremental" | "cumulative">("incremental");
  const [rawCSVData, setRawCSVData] = useState<{ month: string; value: number }[]>([]);
  const [monthlyValues, setMonthlyValues] = useState<MonthlyPlannedValue[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Initialize from project props on open
  useEffect(() => {
    if (project && isOpen) {
      setTotalContractValue(String(project.master_original_budget || 0));
      setStartDate(project.start_date ? project.start_date.substring(0, 10) : "");
      setEndDate(project.end_date ? project.end_date.substring(0, 10) : "");
      setDistributionType("linear");
      setRawCSVData([]);
      setMonthlyValues([]);
      setError(null);
    }
  }, [project, isOpen]);

  // Helper: List YYYY-MM intervals safely
  const getMonthsInterval = (startStr: string, endStr: string): string[] => {
    if (!startStr || !endStr) return [];
    const start = new Date(startStr);
    const end = new Date(endStr);
    if (!isValid(start) || !isValid(end) || start > end) return [];

    const startMonth = new Date(start.getFullYear(), start.getMonth(), 1);
    const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);

    try {
      const months = eachMonthOfInterval({ start: startMonth, end: endMonth });
      return months.map((m) => format(m, "yyyy-MM"));
    } catch (err) {
      console.error("[EVMBaselineModal] Interval calculation failed", err);
      return [];
    }
  };

  // Effect: Auto-calculate linear distribution
  useEffect(() => {
    if (distributionType === "linear" && totalContractValue && startDate && endDate) {
      const contractVal = parseFloat(totalContractValue) || 0;
      const months = getMonthsInterval(startDate, endDate);
      if (months.length > 0 && contractVal > 0) {
        const count = months.length;
        const baseValue = Number((contractVal / count).toFixed(2));
        const sumOfBase = Number((baseValue * count).toFixed(2));
        const diff = Number((contractVal - sumOfBase).toFixed(2));

        const generated = months.map((m, idx) => {
          const val = idx === count - 1 ? Number((baseValue + diff).toFixed(2)) : baseValue;
          return {
            month: m,
            planned_value: val,
            cumulative_value: 0,
          };
        });

        // Compute cumulative
        let runningSum = 0;
        const finalGenerated = generated.map((item) => {
          runningSum = Number((runningSum + item.planned_value).toFixed(2));
          return {
            ...item,
            cumulative_value: runningSum,
          };
        });

        setMonthlyValues(finalGenerated);
      } else {
        setMonthlyValues([]);
      }
    }
  }, [totalContractValue, startDate, endDate, distributionType]);

  // Effect: Process CSV Data when raw CSV or CSV parsing mode changes
  useEffect(() => {
    if (distributionType === "csv" && rawCSVData.length > 0) {
      let formatted: MonthlyPlannedValue[] = [];
      if (csvType === "cumulative") {
        // Cumulative CSV parsing: incremental value = cum[n] - cum[n-1]
        formatted = rawCSVData.map((item, idx) => {
          const prevVal = idx > 0 ? rawCSVData[idx - 1].value : 0;
          const planned = Number((item.value - prevVal).toFixed(2));
          return {
            month: item.month,
            planned_value: planned,
            cumulative_value: item.value,
          };
        });
      } else {
        // Incremental CSV parsing: cumulative = cumulative + inc[n]
        let runningSum = 0;
        formatted = rawCSVData.map((item) => {
          runningSum = Number((runningSum + item.value).toFixed(2));
          return {
            month: item.month,
            planned_value: item.value,
            cumulative_value: runningSum,
          };
        });
      }

      setMonthlyValues(formatted);

      if (formatted.length > 0) {
        const finalCum = formatted[formatted.length - 1].cumulative_value;
        setTotalContractValue(String(finalCum));
      }
    }
  }, [rawCSVData, csvType, distributionType]);

  // Manual interactive planned value change handler
  const handleMonthlyValueChange = (index: number, newValueStr: string) => {
    const val = parseFloat(newValueStr) || 0;
    const updated = [...monthlyValues];
    updated[index].planned_value = val;

    // Recalculate running sum
    let runningSum = 0;
    const finalUpdated = updated.map((item) => {
      runningSum = Number((runningSum + item.planned_value).toFixed(2));
      return {
        ...item,
        cumulative_value: runningSum,
      };
    });

    setMonthlyValues(finalUpdated);
    // Custom edit switches the classification of distribution
    if (distributionType === "linear") {
      setDistributionType("csv");
    }
  };

  // Recalculate metrics for warnings/validation
  const sumOfMonthlyValues = useMemo(() => {
    return Number(monthlyValues.reduce((sum, item) => sum + item.planned_value, 0).toFixed(2));
  }, [monthlyValues]);

  const valuesMatch = useMemo(() => {
    const totalVal = parseFloat(totalContractValue) || 0;
    return Math.abs(sumOfMonthlyValues - totalVal) < 0.05;
  }, [sumOfMonthlyValues, totalContractValue]);

  // Force re-distributing even values
  const handleRedistribute = () => {
    const contractVal = parseFloat(totalContractValue) || 0;
    if (contractVal <= 0 || monthlyValues.length === 0) return;
    const count = monthlyValues.length;
    const baseValue = Number((contractVal / count).toFixed(2));
    const sumOfBase = Number((baseValue * count).toFixed(2));
    const diff = Number((contractVal - sumOfBase).toFixed(2));

    let runningSum = 0;
    const updated = monthlyValues.map((item, idx) => {
      const val = idx === count - 1 ? Number((baseValue + diff).toFixed(2)) : baseValue;
      runningSum = Number((runningSum + val).toFixed(2));
      return {
        ...item,
        planned_value: val,
        cumulative_value: runningSum,
      };
    });
    setMonthlyValues(updated);
    toast.success("Values re-balanced evenly!");
  };

  // CSV parsing logic
  const handleCSVUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (!text) return;

      const lines = text.split(/\r?\n/);
      const parsedValues: { month: string; value: number }[] = [];

      lines.forEach((line) => {
        if (!line.trim()) return;
        // Skip header lines
        if (
          line.toLowerCase().includes("month") ||
          line.toLowerCase().includes("value") ||
          line.toLowerCase().includes("planned") ||
          line.toLowerCase().includes("cum")
        ) {
          return;
        }

        const parts = line.split(/[;,]/);
        if (parts.length >= 2) {
          const monthPart = parts[0].trim().replace(/['"]/g, "");
          const valuePart = parts[1].trim().replace(/['"]/g, "");

          // Match YYYY-MM
          const monthMatch = monthPart.match(/^(\d{4})-(\d{2})$/);
          const value = parseFloat(valuePart.replace(/,/g, ""));

          if (monthMatch && !isNaN(value)) {
            parsedValues.push({ month: monthPart, value });
          }
        }
      });

      if (parsedValues.length === 0) {
        toast.error("Could not parse any valid rows. Format should be YYYY-MM,Planned_Value (e.g. 2026-05,150000)");
        return;
      }

      parsedValues.sort((a, b) => a.month.localeCompare(b.month));

      const parsedStart = `${parsedValues[0].month}-01`;
      // End is last month
      const parsedEnd = `${parsedValues[parsedValues.length - 1].month}-28`;

      setStartDate(parsedStart);
      setEndDate(parsedEnd);
      setDistributionType("csv");
      setRawCSVData(parsedValues);
      toast.success(`Parsed ${parsedValues.length} months successfully!`);
    };

    reader.readAsText(file);
  };

  // Submit Baseline setup to database
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!startDate || !endDate || !totalContractValue) {
      toast.error("All project metrics must be fully defined.");
      return;
    }

    if (!valuesMatch) {
      toast.error("The monthly sum does not match the Total Contract Value.");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const payload = {
        total_contract_value: parseFloat(totalContractValue),
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        curve_type: distributionType === "linear" ? "linear" : "custom",
        monthly_planned_values: monthlyValues.map((v) => ({
          month: v.month,
          planned_value: v.planned_value,
          cumulative_value: v.cumulative_value,
        })),
      };

      await api.post(`/api/v1/projects/${project.project_id}/evm-baseline`, payload);
      toast.success("EVM Baseline initialized successfully!");
      onSuccess();
      onClose();
    } catch (err: any) {
      console.error("[EVMBaselineModal] Save failed", err);
      setError(err.response?.data?.detail || "Failed to initialize EVM baseline. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const inputStyle =
    "w-full bg-slate-900/60 dark:bg-slate-950/70 border border-slate-700/60 dark:border-slate-800 rounded-xl px-4 py-2.5 text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-amber-500/50 transition-colors text-sm font-mono";
  const labelStyle =
    "block text-[10px] font-bold text-zinc-400 dark:text-zinc-500 mb-1.5 uppercase tracking-wider";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-slate-950/95 border border-amber-500/20 text-zinc-100 max-w-4xl rounded-2xl p-0 overflow-hidden shadow-2xl backdrop-blur-xl">
        <DialogHeader className="p-6 border-b border-slate-800/80 bg-gradient-to-b from-slate-900/50 to-transparent">
          <DialogTitle className="text-xl font-bold flex items-center gap-3 text-white">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center border border-amber-500/20">
              <Coins className="text-amber-500 animate-pulse" size={20} />
            </div>
            <div>
              <span>EVM Baseline Setup</span>
              <p className="text-zinc-500 text-xs font-normal mt-0.5">
                Establish the S-curve Earned Value planned schedule for{" "}
                <strong className="text-zinc-300 font-semibold">
                  {project.project_name}
                </strong>
              </p>
            </div>
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col max-h-[80vh]">
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {error && (
              <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs flex gap-2.5 items-start">
                <AlertCircle className="shrink-0 mt-0.5" size={16} />
                <span>{error}</span>
              </div>
            )}

            {/* Inputs grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div>
                <label className={labelStyle}>
                  Total Contract Value (INR) <span className="text-amber-500">*</span>
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-2.5 text-zinc-400 font-mono text-sm">₹</span>
                  <input
                    type="number"
                    required
                    min="1"
                    step="0.01"
                    className={`${inputStyle} pl-8`}
                    placeholder="e.g. 5000000"
                    value={totalContractValue}
                    onChange={(e) => setTotalContractValue(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className={labelStyle}>
                  Start Date <span className="text-amber-500">*</span>
                </label>
                <input
                  type="date"
                  required
                  className={inputStyle}
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>

              <div>
                <label className={labelStyle}>
                  End Date <span className="text-amber-500">*</span>
                </label>
                <input
                  type="date"
                  required
                  className={inputStyle}
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>

            {/* Distribution mode tabs */}
            <div className="border-b border-slate-800/80">
              <div className="flex gap-6 -mb-px">
                <button
                  type="button"
                  onClick={() => setDistributionType("linear")}
                  className={`pb-3 text-xs font-black uppercase tracking-wider transition-colors border-b-2 flex items-center gap-1.5 ${
                    distributionType === "linear"
                      ? "border-amber-500 text-amber-500 font-extrabold"
                      : "border-transparent text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  <RefreshCw size={13} />
                  Linear Auto-Distribution
                </button>
                <button
                  type="button"
                  onClick={() => setDistributionType("csv")}
                  className={`pb-3 text-xs font-black uppercase tracking-wider transition-colors border-b-2 flex items-center gap-1.5 ${
                    distributionType === "csv"
                      ? "border-amber-500 text-amber-500 font-extrabold"
                      : "border-transparent text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  <Upload size={13} />
                  CSV Upload / Custom Distribution
                </button>
              </div>
            </div>

            {distributionType === "csv" && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {/* CSV Select Zone */}
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="border border-dashed border-slate-700 hover:border-amber-500/50 rounded-xl p-6 bg-slate-900/30 flex flex-col items-center justify-center cursor-pointer transition-colors group"
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      accept=".csv"
                      className="hidden"
                      onChange={handleCSVUpload}
                    />
                    <Upload className="text-zinc-500 group-hover:text-amber-500 mb-2 transition-colors" size={24} />
                    <span className="text-xs font-bold text-zinc-300">Click to upload planned S-curve CSV</span>
                    <span className="text-[10px] text-zinc-500 mt-1">Expected columns: YYYY-MM, Planned_Value</span>
                  </div>

                  {/* CSV Options */}
                  <div className="p-5 border border-slate-800 bg-slate-900/20 rounded-xl space-y-3">
                    <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block">CSV Value Semantics</span>
                    <div className="flex gap-5">
                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="csv_semantics"
                          checked={csvType === "incremental"}
                          onChange={() => setCsvType("incremental")}
                          className="accent-amber-500"
                        />
                        <div className="text-xs">
                          <p className="font-bold text-zinc-300">Incremental</p>
                          <p className="text-[10px] text-zinc-500">Each month lists value for that month</p>
                        </div>
                      </label>

                      <label className="flex items-center gap-2 cursor-pointer">
                        <input
                          type="radio"
                          name="csv_semantics"
                          checked={csvType === "cumulative"}
                          onChange={() => setCsvType("cumulative")}
                          className="accent-amber-500"
                        />
                        <div className="text-xs">
                          <p className="font-bold text-zinc-300">Cumulative</p>
                          <p className="text-[10px] text-zinc-500">Each month lists the total running sum</p>
                        </div>
                      </label>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Preview table & Interactive fields */}
            {monthlyValues.length > 0 ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="text-amber-500" size={14} />
                    <span className="text-xs font-bold uppercase tracking-wider text-zinc-300">S-Curve Slices Preview</span>
                  </div>

                  <div className="flex items-center gap-4">
                    {/* Live validation indicator */}
                    <div className="text-xs font-mono">
                      <span>Sum: </span>
                      <strong className={valuesMatch ? "text-emerald-500 font-extrabold" : "text-amber-500 font-extrabold"}>
                        {formatCurrencySafe(sumOfMonthlyValues)}
                      </strong>
                      <span className="text-zinc-500"> / </span>
                      <span className="text-zinc-400">{formatCurrencySafe(parseFloat(totalContractValue) || 0)}</span>
                    </div>

                    {!valuesMatch && (
                      <button
                        type="button"
                        onClick={handleRedistribute}
                        className="px-2.5 py-1 text-[10px] bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 border border-amber-500/20 rounded font-black uppercase tracking-wider transition-colors flex items-center gap-1"
                      >
                        <RefreshCw size={10} />
                        Balance
                      </button>
                    )}
                  </div>
                </div>

                {!valuesMatch && (
                  <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-amber-400 text-xs flex gap-2">
                    <AlertCircle className="shrink-0 mt-0.5" size={14} />
                    <div>
                      <span>
                        The sum of the S-curve distribution monthly slices (₹{sumOfMonthlyValues.toLocaleString("en-IN")}) does not match the Total Contract Value (₹{(parseFloat(totalContractValue) || 0).toLocaleString("en-IN")}).
                      </span>
                      <p className="text-[10px] text-amber-400/80 mt-0.5">
                        Please adjust individual months below or click "Balance" to auto-distribute.
                      </p>
                    </div>
                  </div>
                )}

                {/* Slices Table */}
                <div className="border border-slate-800 rounded-xl overflow-hidden max-h-[300px] overflow-y-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-900 text-zinc-400 sticky top-0 uppercase tracking-widest font-black text-[9px] border-b border-slate-800">
                      <tr>
                        <th className="p-3">Month</th>
                        <th className="p-3">Planned Value (Incremental)</th>
                        <th className="p-3 text-right">Cumulative S-Curve Value</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 bg-slate-950/40">
                      {monthlyValues.map((row, idx) => (
                        <tr key={row.month} className="hover:bg-slate-900/30 transition-colors">
                          <td className="p-3 font-mono font-bold text-zinc-300">{row.month}</td>
                          <td className="p-3">
                            <div className="relative w-44">
                              <span className="absolute left-2.5 top-1.5 text-zinc-500 font-mono text-[10px]">₹</span>
                              <input
                                type="number"
                                step="0.01"
                                className="w-full bg-slate-900 border border-slate-800 rounded px-6 py-1 text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-amber-500/50 transition-colors text-xs font-mono"
                                value={row.planned_value}
                                onChange={(e) => handleMonthlyValueChange(idx, e.target.value)}
                              />
                            </div>
                          </td>
                          <td className="p-3 text-right font-mono text-zinc-400 font-medium">
                            {formatCurrencySafe(row.cumulative_value)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="py-10 border border-dashed border-slate-800 rounded-xl flex flex-col items-center justify-center text-center p-6 bg-slate-900/10">
                <Info className="text-zinc-600 mb-2" size={24} />
                <span className="text-xs font-bold text-zinc-400">No active planned distribution.</span>
                <p className="text-[10px] text-zinc-600 max-w-sm mt-1 uppercase tracking-wider">
                  Fill in a valid Contract Value and Start/End Dates above to auto-generate S-curve.
                </p>
              </div>
            )}
          </div>

          <DialogFooter className="p-6 border-t border-slate-800/80 bg-slate-900/30">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 border border-slate-700 hover:bg-slate-900/60 text-zinc-400 hover:text-white rounded-xl text-xs font-bold uppercase tracking-wider transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !startDate || !endDate || !totalContractValue || !valuesMatch || monthlyValues.length === 0}
              className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white px-6 py-2.5 rounded-xl text-xs font-bold uppercase tracking-widest shadow-lg shadow-orange-500/10 hover:shadow-orange-500/20 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4.5 h-4.5 animate-spin" />}
              Save Baseline Snapshot
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
