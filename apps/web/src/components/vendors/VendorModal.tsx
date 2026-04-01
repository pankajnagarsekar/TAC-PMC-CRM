"use client";

import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@tac-pmc/ui";
import api from "@/lib/api";
import {
  Loader2,
  Mail,
  Phone,
  User,
  Landmark,
  MapPin,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Vendor } from "@tac-pmc/types";

interface VendorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  vendor?: Vendor;
}

export default function VendorModal({
  isOpen,
  onClose,
  onSuccess,
  vendor,
}: VendorModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { toast } = useToast();
  const [formData, setFormData] = useState({
    name: "",
    gstin: "",
    contact_person: "",
    phone: "",
    email: "",
    address: "",
  });
  const [gstinError, setGstinError] = useState("");

  // GSTIN validation: exactly 15 characters, alphanumeric uppercase
  const validateGSTIN = (gstin: string): boolean => {
    if (!gstin) return true; // Optional field
    const gstinRegex = /^[0-9A-Z]{15}$/;
    return gstinRegex.test(gstin);
  };

  useEffect(() => {
    if (vendor) {
      setFormData({
        name: vendor.name || "",
        gstin: vendor.gstin || "",
        contact_person: vendor.contact_person || "",
        phone: vendor.phone || "",
        email: vendor.email || "",
        address: vendor.address || "",
      });
    } else {
      setFormData({
        name: "",
        gstin: "",
        contact_person: "",
        phone: "",
        email: "",
        address: "",
      });
    }
  }, [vendor, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) {
      toast({
        title: "Error",
        description: "Vendor name is required",
        variant: "destructive",
      });
      return;
    }

    // Validate GSTIN format if provided
    if (formData.gstin && !validateGSTIN(formData.gstin)) {
      setGstinError("GSTIN must be exactly 15 alphanumeric characters");
      return;
    }
    setGstinError("");

    setIsSubmitting(true);
    try {
      if (vendor) {
        await api.put(
          `/api/v1/vendors/${vendor._id || (vendor as { _id?: string; id?: string }).id}`,
          formData,
        );
        toast({ title: "Success", description: "Vendor updated successfully" });
      } else {
        await api.post("/api/v1/vendors/", formData);
        toast({ title: "Success", description: "Vendor created successfully" });
      }
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save vendor",
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputStyle =
    "w-full bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-orange-500/50 transition-colors placeholder:text-slate-600";
  const labelStyle =
    "block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wider px-1";
  const buttonBase =
    "px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center justify-center gap-2";

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="bg-slate-950 border-slate-900 text-white max-w-lg rounded-2xl p-0 overflow-hidden shadow-2xl">
        <DialogHeader className="p-6 border-b border-slate-900 bg-slate-950/50">
          <DialogTitle className="text-xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
            {vendor ? "Edit Vendor" : "Add New Vendor"}
          </DialogTitle>
          <p className="text-slate-500 text-sm mt-1">
            {vendor
              ? "Update existing vendor profile and business information."
              : "Enter vendor details to initialize their account."}
          </p>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="space-y-4">
            <div>
              <label className={labelStyle}>
                Vendor / Business Name{" "}
                <span className="text-orange-500">*</span>
              </label>
              <div className="relative">
                <Landmark
                  className="absolute left-3 top-3 text-slate-500"
                  size={16}
                />
                <input
                  required
                  className={`${inputStyle} pl-10`}
                  placeholder="ABC Construction Ltd"
                  value={formData.name}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelStyle}>GSTIN</label>
                <input
                  className={`${inputStyle} ${gstinError ? "border-red-500 focus:border-red-500" : ""}`}
                  placeholder="27AAAAA0000A1Z5"
                  value={formData.gstin}
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                    setFormData({
                      ...formData,
                      gstin: e.target.value.toUpperCase(),
                    });
                    setGstinError("");
                  }}
                  maxLength={15}
                />
                {gstinError && (
                  <p className="text-red-500 text-xs mt-1">{gstinError}</p>
                )}
              </div>
              <div>
                <label className={labelStyle}>Contact Person</label>
                <div className="relative">
                  <User
                    className="absolute left-3 top-3 text-slate-500"
                    size={16}
                  />
                  <input
                    className={`${inputStyle} pl-10`}
                    placeholder="John Doe"
                    value={formData.contact_person}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setFormData({
                        ...formData,
                        contact_person: e.target.value,
                      })
                    }
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelStyle}>Phone Number</label>
                <div className="relative">
                  <Phone
                    className="absolute left-3 top-3 text-slate-500"
                    size={16}
                  />
                  <input
                    className={`${inputStyle} pl-10`}
                    placeholder="+91 98765 43210"
                    value={formData.phone}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setFormData({ ...formData, phone: e.target.value })
                    }
                  />
                </div>
              </div>
              <div>
                <label className={labelStyle}>Email Address</label>
                <div className="relative">
                  <Mail
                    className="absolute left-3 top-3 text-slate-500"
                    size={16}
                  />
                  <input
                    type="email"
                    className={`${inputStyle} pl-10`}
                    placeholder="contact@vendor.com"
                    value={formData.email}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setFormData({ ...formData, email: e.target.value })
                    }
                  />
                </div>
              </div>
            </div>

            <div>
              <label className={labelStyle}>Office Address</label>
              <div className="relative">
                <MapPin
                  className="absolute left-3 top-3 text-slate-500"
                  size={16}
                />
                <textarea
                  className={`${inputStyle} pl-10 min-h-[80px] py-3 resize-none`}
                  placeholder="Street address, City, Pincode"
                  value={formData.address}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                    setFormData({ ...formData, address: e.target.value })
                  }
                />
              </div>
            </div>
          </div>

          <DialogFooter className="pt-4 flex gap-3 sm:gap-0">
            <button
              type="button"
              onClick={onClose}
              className={`${buttonBase} flex-1 sm:flex-none border border-slate-800 text-slate-400 hover:bg-slate-900`}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className={`${buttonBase} flex-1 sm:flex-none bg-orange-600 text-white hover:bg-orange-500 shadow-lg shadow-orange-900/20 disabled:opacity-50`}
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              {vendor ? "Update Vendor" : "Create Vendor"}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
