'use client';

import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@tac-pmc/ui';
import api from '@/lib/api';
import { Loader2, Hash } from 'lucide-react';
import { CodeMaster } from '@/types/api';

interface CategoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  category?: CodeMaster;
}

const BUDGET_TYPES = [
  { value: 'commitment', label: 'Commitment-Based (WO deducts immediately)' },
  { value: 'fund_transfer', label: 'Fund-Transfer (PC close triggers deduction)' },
];

export default function CategoryModal({ isOpen, onClose, onSuccess, category }: CategoryModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    category_name: '',
    code: '',
    budget_type: 'commitment',
    description: '',
  });

  useEffect(() => {
    if (category) {
      setFormData({
        category_name: category.category_name,
        code: category.code,
        budget_type: (category as any).budget_type || 'commitment',
        description: (category as any).description || '',
      });
    } else {
      setFormData({ category_name: '', code: '', budget_type: 'commitment', description: '' });
    }
    setError(null);
  }, [category, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (category?.code_id) {
        await api.put(`/api/codes/${category.code_id}`, formData);
      } else {
        await api.post('/api/codes', formData);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save category.');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = "w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-white focus:outline-none focus:border-orange-500/50 transition-colors placeholder:text-slate-600";
  const labelStyle = "block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-md rounded-2xl p-0 overflow-hidden shadow-2xl">
        <DialogHeader className="p-6 border-b border-slate-900">
          <DialogTitle className="text-xl font-bold text-white flex items-center gap-2">
            <Hash className="text-orange-500" size={20} />
            {category ? 'Edit Category' : 'Add Category'}
          </DialogTitle>
          <p className="text-slate-500 text-sm mt-1">
            {category ? 'Update this budget category.' : 'Define a new budget category for all projects.'}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs">{error}</div>
          )}

          <div>
            <label className={labelStyle}>Category Name <span className="text-orange-500">*</span></label>
            <input
              required
              className={inputStyle}
              placeholder="e.g. Civil Works"
              value={formData.category_name}
              onChange={e => setFormData({ ...formData, category_name: e.target.value })}
            />
          </div>

          <div>
            <label className={labelStyle}>Short Code <span className="text-orange-500">*</span></label>
            <input
              required
              className={`${inputStyle} font-mono uppercase`}
              placeholder="e.g. CIVIL"
              value={formData.code}
              onChange={e => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
            />
            <p className="text-[10px] text-slate-600 mt-1 px-1">Used in WO/PC references. Cannot be changed after creation.</p>
          </div>

          <div>
            <label className={labelStyle}>Budget Model <span className="text-orange-500">*</span></label>
            <select
              className={inputStyle}
              value={formData.budget_type}
              onChange={e => setFormData({ ...formData, budget_type: e.target.value })}
            >
              {BUDGET_TYPES.map(bt => (
                <option key={bt.value} value={bt.value}>{bt.label}</option>
              ))}
            </select>
            <p className="text-[10px] text-slate-600 mt-1 px-1">
              {formData.budget_type === 'fund_transfer'
                ? 'Use for Petty Cash & OVH: deduction happens only when funds are received via PC.'
                : 'Use for Civil, Electrical, CSA: WO creation deducts from remaining budget immediately.'}
            </p>
          </div>

          <DialogFooter className="pt-4 flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border border-slate-800 text-slate-400 hover:bg-slate-900 px-4 py-2 rounded-xl text-sm font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-orange-600 hover:bg-orange-500 text-white px-4 py-2 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {category ? 'Update Category' : 'Create Category'}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
