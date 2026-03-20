'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@tac-pmc/ui';
import { Client, ClientCreate, ClientUpdate } from '@/types/api';
import api from '@/lib/api';
import { Loader2 } from 'lucide-react';

// Reusing generic button styles to match project aesthetic
const buttonBase = "px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2";

interface ClientModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  client?: Client; // If provided, we are in edit mode
}

export default function ClientModal({ isOpen, onClose, onSuccess, client }: ClientModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<Partial<ClientCreate>>({
    client_name: '',
    client_email: '',
    client_phone: '',
    client_address: '',
    gst_number: '',
  });

  useEffect(() => {
    if (client) {
      setFormData({
        client_name: client.client_name,
        client_email: client.client_email || '',
        client_phone: client.client_phone || '',
        client_address: client.client_address || '',
        gst_number: client.gst_number || '',
      });
    } else {
      setFormData({
        client_name: '',
        client_email: '',
        client_phone: '',
        client_address: '',
        gst_number: '',
      });
    }
  }, [client, isOpen]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (client?._id) {
        await api.put(`/api/clients/${client._id}`, formData);
      } else {
        await api.post('/api/clients', formData);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      console.error('Client submission error:', err);
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const inputStyle = "w-full bg-white dark:bg-slate-900 border border-zinc-200 dark:border-slate-800 rounded-xl px-4 py-3 text-zinc-900 dark:text-white text-sm focus:outline-none focus:border-orange-500/50 transition-colors placeholder:text-zinc-400 dark:placeholder:text-slate-600";
  const labelStyle = "block text-xs font-semibold text-zinc-500 dark:text-slate-400 mb-1.5 uppercase tracking-wider px-1";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-white dark:bg-slate-950 border border-zinc-200 dark:border-slate-900 text-zinc-900 dark:text-white max-w-lg rounded-2xl p-0 overflow-hidden shadow-2xl">
        <DialogHeader className="p-6 border-b border-zinc-100 dark:border-slate-900 bg-zinc-50/50 dark:bg-slate-950/50">
          <DialogTitle className="text-xl font-bold bg-gradient-to-r from-zinc-900 to-zinc-500 dark:from-white dark:to-slate-400 bg-clip-text text-transparent">
            {client ? 'Edit Client Details' : 'Onboard New Client'}
          </DialogTitle>
          <p className="text-zinc-500 dark:text-slate-500 text-sm mt-1">
            {client ? 'Update existing client profile and business information.' : 'Enter client details to initialize their account in the CRM.'}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-xs font-medium">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div>
              <label className={labelStyle}>Business Name <span className="text-orange-500">*</span></label>
              <input
                required
                className={inputStyle}
                placeholder="e.g. Acme Constructions Pvt Ltd"
                value={formData.client_name}
                onChange={e => setFormData({ ...formData, client_name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelStyle}>Email Address</label>
                <input
                  type="email"
                  className={inputStyle}
                  placeholder="contact@client.com"
                  value={formData.client_email}
                  onChange={e => setFormData({ ...formData, client_email: e.target.value })}
                />
              </div>
              <div>
                <label className={labelStyle}>Phone Number</label>
                <input
                  className={inputStyle}
                  placeholder="+91 XXXXX XXXXX"
                  value={formData.client_phone}
                  onChange={e => setFormData({ ...formData, client_phone: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className={labelStyle}>GST Number</label>
              <input
                className={inputStyle}
                placeholder="27AAAAA0000A1Z5"
                value={formData.gst_number}
                onChange={e => setFormData({ ...formData, gst_number: e.target.value })}
              />
            </div>

            <div>
              <label className={labelStyle}>Registered Office Address</label>
              <textarea
                className={`${inputStyle} min-h-[100px] py-3 resize-none`}
                placeholder="Full business address..."
                value={formData.client_address}
                onChange={e => setFormData({ ...formData, client_address: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter className="pt-4 flex gap-3 sm:gap-0">
            <button
              type="button"
              onClick={onClose}
              className={`${buttonBase} flex-1 sm:flex-none border border-zinc-200 dark:border-slate-800 text-zinc-500 dark:text-slate-400 hover:bg-zinc-100 dark:hover:bg-slate-900`}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className={`${buttonBase} flex-1 sm:flex-none bg-orange-600 text-white hover:bg-orange-500 shadow-lg shadow-orange-900/20 disabled:opacity-50`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {client ? 'Update Client' : 'Add Client'}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
