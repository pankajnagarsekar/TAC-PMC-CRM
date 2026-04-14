"use client";

import React, { useState } from 'react';
import { GlassCard } from '@/components/ui/GlassCard';

interface CodeMaster {
  _id: string;
  label: string;
  description: string;
  default_percent: number;
}

interface MasterDataManagerProps {
  codes: CodeMaster[];
  onAdd?: (code: { label: string; description: string; default_percent: number }) => void;
  onUpdate?: (id: string, data: { label?: string; description?: string; default_percent?: number }) => void;
  onDelete?: (id: string) => void;
}

export default function MasterDataManager({
  codes,
  onAdd,
  onUpdate,
  onDelete,
}: MasterDataManagerProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formData, setFormData] = useState({
    label: '',
    description: '',
    default_percent: 0,
  });

  const filteredCodes = codes.filter((code) =>
    code.label.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleAddClick = () => {
    setFormData({ label: '', description: '', default_percent: 0 });
    setEditingId(null);
    setShowAddModal(true);
  };

  const handleEditClick = (code: CodeMaster) => {
    setFormData({
      label: code.label,
      description: code.description,
      default_percent: code.default_percent,
    });
    setEditingId(code._id);
    setShowAddModal(true);
  };

  const handleSave = () => {
    if (!formData.label.trim()) {
      alert('Label is required');
      return;
    }
    if (formData.default_percent < 0 || formData.default_percent > 100) {
      alert('Percentage must be between 0 and 100');
      return;
    }

    if (editingId) {
      onUpdate?.(editingId, formData);
    } else {
      onAdd?.(formData);
    }
    setShowAddModal(false);
  };

  const handleDeleteClick = (id: string) => {
    setDeletingId(id);
  };

  const handleConfirmDelete = (id: string) => {
    onDelete?.(id);
    setDeletingId(null);
  };

  return (
    <GlassCard className="p-6">
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white">Financial Codes</h2>
          <button
            onClick={handleAddClick}
            className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-semibold transition"
          >
            + Add Code
          </button>
        </div>

        {/* Search */}
        <div>
          <input
            type="text"
            placeholder="Search by label..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-teal-500"
          />
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 px-4 text-gray-300">Label</th>
                <th className="text-left py-3 px-4 text-gray-300">Description</th>
                <th className="text-center py-3 px-4 text-gray-300">Default %</th>
                <th className="text-center py-3 px-4 text-gray-300">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredCodes.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-gray-400">
                    No codes found
                  </td>
                </tr>
              ) : (
                filteredCodes.map((code) => (
                  <React.Fragment key={code._id}>
                    <tr className="border-b border-gray-800 hover:bg-gray-900 transition-colors">
                      <td className="py-4 px-4 font-semibold text-white">{code.label}</td>
                      <td className="py-4 px-4 text-gray-400">{code.description}</td>
                      <td className="py-4 px-4 text-center text-gray-400">
                        {code.default_percent}%
                      </td>
                      <td className="py-4 px-4 text-center space-x-2">
                        <button
                          onClick={() => handleEditClick(code)}
                          className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-semibold transition"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDeleteClick(code._id)}
                          className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-semibold transition"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                    {deletingId === code._id && (
                      <tr className="bg-red-900 bg-opacity-20 border-b border-gray-800">
                        <td colSpan={4} className="py-4 px-4">
                          <div className="flex items-center justify-between">
                            <p className="text-red-400 font-semibold">
                              Are you sure you want to delete &quot;{code.label}&quot;?
                            </p>
                            <div className="space-x-2">
                              <button
                                onClick={() => handleConfirmDelete(code._id)}
                                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-semibold transition"
                              >
                                Confirm Delete
                              </button>
                              <button
                                onClick={() => setDeletingId(null)}
                                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm font-semibold transition"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 rounded-lg">
          <GlassCard className="w-96 p-6 space-y-4">
            <h3 className="text-xl font-bold text-white">
              {editingId ? 'Edit Code' : 'Create New Code'}
            </h3>

            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-1">
                Label *
              </label>
              <input
                type="text"
                value={formData.label}
                onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                placeholder="e.g., LABOR"
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-1">
                Description
              </label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="e.g., Labor costs"
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-300 mb-1">
                Default % (0-100)
              </label>
              <input
                type="number"
                value={formData.default_percent}
                onChange={(e) => setFormData({ ...formData, default_percent: Number(e.target.value) })}
                min="0"
                max="100"
                className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-teal-500"
              />
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded font-semibold transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded font-semibold transition"
              >
                {editingId ? 'Update' : 'Create'}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </GlassCard>
  );
}
