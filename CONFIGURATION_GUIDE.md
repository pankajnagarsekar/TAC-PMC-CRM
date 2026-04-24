# Configuration Guide

This document outlines mandatory administrative configurations required for the full functionality of the TAC-PMC-CRM system.

## 1. Company Information (BUG-064)

To ensure that reports, PDF exports, and payment certificates are generated with the correct branding and contact details, an administrator must configure the company's global metadata.

### Configuration Location
Admin Settings > Global Configuration > Company Profile

### Required Fields
The following placeholders are used across the system and must be replaced with official company data:

| Field Name | Placeholder/Default | Usage |
|-----------|--------------------|-------|
| Company Name | `[Company Name]` | Report Headers, PC PDF |
| Head Office Address | `[Company Address Placeholder]` | PDF Footers, Contact Sections |
| Registration Number | `[Reg No]` | Financial Documents |
| Tax ID / GSTIN | `[Tax ID]` | Invoices, Certified Payments |
| Contact Email | `admin@company.com` | Notification Footers |

### Impact of Missing Configuration
If these fields are left as placeholders:
1. **PDF Exports**: Will display `[Company Address Placeholder]` instead of the actual office address.
2. **Payment Certificates**: May be legally invalid without the correct Registration and Tax IDs.
3. **AI OCR Scanner**: Verification forms will use default branding.

---

## 2. Temporal Settings

Ensure that the Time Zone and Fiscal Year start dates are correctly set to align site operations (DPRs) with financial reporting periods.

## 3. Worker Categories

Standardize worker categories (e.g., CARPENTER, HELPER, MASON) before starting site attendance logging to ensure accurate labor cost analytics.
