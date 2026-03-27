'use client';

import { useState, useRef } from 'react';
import { useProjectStore } from '@/store/projectStore';
import api from '@/lib/api';
import {
  Scan,
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  ArrowRight,
  IndianRupee,
  FileSearch,
  Calendar,
  User,
  Hash,
  Sparkles,
  RefreshCcw
} from 'lucide-react';
import { formatCurrency } from '@tac-pmc/ui';
import { useRouter } from 'next/navigation';

interface OCRResult {
  ocr_id: string;
  extracted_vendor_name?: string;
  extracted_amount?: number;
  extracted_date?: string;
  extracted_invoice_number?: string;
  confidence_score: number;
}

export default function OCRScannerPage() {
  const { activeProject } = useProjectStore();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  // Editable fields for verification
  const [verifiedData, setVerifiedData] = useState({
    vendor_name: '',
    invoice_number: '',
    date: '',
    amount: 0,
    gst_amount: 0,
  });

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/') && file.type !== 'application/pdf') {
      setError('Please upload an image or PDF file.');
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      setPreview(reader.result as string);
    };
    reader.readAsDataURL(file);

    processOCR(file);
  };

  const processOCR = async (file: File) => {
    setLoading(true);
    setError(null);
    setOcrResult(null);

    const formData = new FormData();
    formData.append('file', file);
    if (activeProject) {
      formData.append('project_id', activeProject.project_id);
    }

    try {
      const res = await api.post('/api/v1/ai/ocr', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const result = res.data;
      setOcrResult(result);
      setVerifiedData({
        vendor_name: result.extracted_vendor_name || '',
        invoice_number: result.extracted_invoice_number || '',
        date: result.extracted_date || new Date().toISOString().split('T')[0],
        amount: result.extracted_amount || 0,
        gst_amount: 0, // AI might not extract this separately yet
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'AI OCR processing failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCertificate = async () => {
    if (!activeProject) return;

    setLoading(true);
    try {
      await api.post('/api/payment-certificates', {
        project_id: activeProject.project_id,
        vendor_name: verifiedData.vendor_name,
        invoice_number: verifiedData.invoice_number,
        date: verifiedData.date,
        amount: verifiedData.amount,
        gst_amount: verifiedData.gst_amount,
        total_amount: verifiedData.amount + verifiedData.gst_amount,
        ocr_id: ocrResult?.ocr_id
      });

      setIsSuccess(true);
      setTimeout(() => {
        router.push('/admin/payment-certificates');
      }, 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create payment certificate.');
    } finally {
      setLoading(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="flex flex-col items-center justify-center h-[80vh] p-6 animate-in zoom-in-95 duration-500">
        <div className="w-20 h-20 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-500 mb-6 border border-emerald-500/20">
          <CheckCircle2 size={40} />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Payment Certificate Created!</h2>
        <p className="text-slate-400 text-center max-w-xs">The extracted data has been saved. Redirecting to Payment Register...</p>
      </div>
    );
  }

  const inputStyle = "w-full bg-slate-900/50 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors placeholder:text-slate-600";
  const labelStyle = "block text-[10px] font-bold text-slate-500 mb-1.5 uppercase tracking-widest flex items-center gap-2";

  return (
    <div className="p-6 space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Scan className="text-orange-500" size={28} />
            AI Document Scanner
          </h1>
          <p className="text-slate-500 text-sm mt-1">Upload an invoice or document to auto-extract details using GPT-4o Vision.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Upload / Preview */}
        <div className="space-y-4">
          {!preview ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-slate-800 rounded-3xl aspect-[3/4] flex flex-col items-center justify-center gap-4 cursor-pointer hover:border-orange-500/30 hover:bg-orange-500/5 transition-all group"
            >
              <div className="w-16 h-16 rounded-2xl bg-slate-900 flex items-center justify-center text-slate-500 group-hover:scale-110 group-hover:text-orange-500 transition-all duration-500 shadow-xl shadow-black/20">
                <Upload size={32} />
              </div>
              <div className="text-center">
                <p className="text-white font-semibold">Drop document here</p>
                <p className="text-slate-500 text-xs mt-1">PNG, JPG or PDF (Max 10MB)</p>
              </div>
              <button className="mt-2 bg-slate-800 hover:bg-slate-700 text-white px-6 py-2 rounded-xl text-sm font-medium transition-colors border border-slate-700/50">
                Select File
              </button>
            </div>
          ) : (
            <div className="relative rounded-3xl overflow-hidden aspect-[3/4] border border-slate-800 shadow-2xl group">
              <img src={preview} alt="Preview" className="w-full h-full object-cover opacity-80" />
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent flex flex-col justify-end p-6">
                <div className="flex items-center justify-between">
                  <button
                    onClick={() => { setPreview(null); setOcrResult(null); }}
                    className="bg-slate-900/90 hover:bg-red-500 text-white p-2.5 rounded-xl transition-all border border-slate-800"
                  >
                    <RefreshCcw size={18} />
                  </button>
                  <p className="text-white font-bold text-sm bg-slate-900/80 px-4 py-2 rounded-xl border border-slate-800 backdrop-blur-md">
                    Document Captured
                  </p>
                </div>
              </div>
            </div>
          )}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
            accept="image/*,application/pdf"
          />
        </div>

        {/* Right Column: AI Extraction & Verification */}
        <div className="space-y-6">
          {loading ? (
            <div className="bg-slate-900/30 border border-slate-800 rounded-3xl p-12 flex flex-col items-center justify-center text-center animate-pulse min-h-[400px]">
              <div className="relative mb-6">
                <FileSearch size={64} className="text-orange-500/20" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Loader2 className="w-10 h-10 text-orange-500 animate-spin" />
                </div>
              </div>
              <h3 className="text-white font-bold text-lg">AI is analyzing document...</h3>
              <p className="text-slate-500 text-sm mt-2 max-w-xs">Extracting vendor names, dates, amounts and invoice numbers.</p>
            </div>
          ) : ocrResult ? (
            <div className="bg-slate-900/30 border border-slate-800 rounded-3xl p-6 space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sparkles size={18} className="text-orange-500" />
                  <h3 className="text-white font-bold">AI Extraction Result</h3>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-[10px] font-bold uppercase tracking-wider">
                  {Math.round(ocrResult.confidence_score * 100)}% Confidence
                </div>
              </div>

              <div className="space-y-4">
                <div className="space-y-1">
                  <label className={labelStyle}><User size={12} /> Vendor / Beneficiary</label>
                  <input
                    className={inputStyle}
                    value={verifiedData.vendor_name}
                    onChange={e => setVerifiedData({ ...verifiedData, vendor_name: e.target.value })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className={labelStyle}><Hash size={12} /> Invoice Number</label>
                    <input
                      className={inputStyle}
                      value={verifiedData.invoice_number}
                      onChange={e => setVerifiedData({ ...verifiedData, invoice_number: e.target.value })}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className={labelStyle}><Calendar size={12} /> Document Date</label>
                    <input
                      type="date"
                      className={inputStyle}
                      value={verifiedData.date}
                      onChange={e => setVerifiedData({ ...verifiedData, date: e.target.value })}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className={labelStyle}><IndianRupee size={12} /> taxable amount</label>
                    <input
                      type="number"
                      className={inputStyle}
                      value={verifiedData.amount || ''}
                      onChange={e => setVerifiedData({ ...verifiedData, amount: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="space-y-1">
                    <label className={labelStyle}><IndianRupee size={12} /> GST Amount</label>
                    <input
                      type="number"
                      className={inputStyle}
                      value={verifiedData.gst_amount || ''}
                      onChange={e => setVerifiedData({ ...verifiedData, gst_amount: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                </div>

                <div className="bg-orange-500/10 border border-orange-500/20 rounded-2xl p-4 mt-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 font-medium">Final Payable Amount</span>
                    <span className="text-xl font-bold text-orange-500">{formatCurrency(verifiedData.amount + verifiedData.gst_amount)}</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 space-y-3">
                <button
                  onClick={handleCreateCertificate}
                  className="w-full bg-orange-600 hover:bg-orange-500 text-white font-bold py-3 rounded-2xl flex items-center justify-center gap-3 transition-all shadow-xl shadow-orange-901/20 active:scale-[0.98]"
                >
                  <FileText size={20} />
                  Create Payment Certificate
                  <ArrowRight size={18} />
                </button>
                <p className="text-[10px] text-slate-500 text-center uppercase tracking-widest font-bold">Verify data before saving</p>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900/30 border border-slate-800 border-dashed rounded-3xl p-12 flex flex-col items-center justify-center text-center text-slate-500 min-h-[400px]">
              <FileSearch size={48} className="mb-4 opacity-20" />
              <h3 className="text-slate-400 font-medium">Awaiting Document</h3>
              <p className="text-xs mt-2 max-w-[200px]">Once you upload a file, AI will automatically populate the data fields here.</p>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-2xl p-4 flex items-start gap-3 animate-in shake duration-500">
              <AlertTriangle className="text-red-500 flex-shrink-0" size={18} />
              <div>
                <h4 className="text-red-400 text-xs font-bold uppercase tracking-wider">Extraction Error</h4>
                <p className="text-red-400/80 text-[11px] mt-0.5">{error}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
