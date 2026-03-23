import sys
import os
from datetime import datetime

# Add apps/api to path
sys.path.append(os.path.abspath("apps/api"))

# Mock logger to avoid import issues if any
import logging
logging.basicConfig(level=logging.INFO)

from core.pdf_service import pdf_generator

def test_wo_pdf():
    print("Testing Work Order PDF generation...")
    wo_data = {
        "wo_ref": "WO-TEST-001",
        "created_at": datetime.now(),
        "subtotal": 1000.0,
        "cgst": 90.0,
        "sgst": 90.0,
        "grand_total": 1180.0,
        "retention_amount": 59.0,
        "total_payable": 1121.0,
        "line_items": [
            {"description": "Test Item 1", "qty": 10, "rate": 50, "total": 500},
            {"description": "Test Item 2", "qty": 5, "rate": 100, "total": 500},
        ]
    }
    settings = {
        "name": "Test Company Ltd",
        "address": "123 Test Street, Goa",
        "gst_number": "30AAAAA0000A1Z5",
        "logo_base64": "" # Empty logo for now
    }
    vendor_data = {
        "name": "Test Vendor",
        "address": "456 Vendor Lane"
    }
    
    pdf_bytes = pdf_generator.generate_work_order_pdf(wo_data, settings, vendor_data)
    with open("test_wo.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"WO PDF generated: {len(pdf_bytes)} bytes")

def test_pc_pdf():
    print("Testing Payment Certificate PDF generation...")
    pc_data = {
        "pc_ref": "PC-TEST-001",
        "wo_ref": "WO-TEST-001",
        "created_at": datetime.now(),
        "subtotal": 5000.0,
        "retention_amount": 250.0,
        "total_after_retention": 4750.0,
        "cgst": 427.5,
        "sgst": 427.5,
        "grand_total": 5605.0,
        "line_items": [
            {"scope_of_work": "Civil Works", "rate": 1000, "qty": 2.5, "unit": "Sqm", "total": 2500},
            {"scope_of_work": "Plumbing", "rate": 500, "qty": 5, "unit": "Nos", "total": 2500},
        ]
    }
    settings = {
        "name": "Test Company Ltd",
    }
    vendor_data = {
        "name": "Test Vendor",
        "gstin": "30BBBBB1111B1Z5"
    }
    
    pdf_bytes = pdf_generator.generate_payment_certificate_pdf(pc_data, settings, vendor_data)
    with open("test_pc.pdf", "wb") as f:
        f.write(pdf_bytes)
    print(f"PC PDF generated: {len(pdf_bytes)} bytes")

if __name__ == "__main__":
    try:
        test_wo_pdf()
        test_pc_pdf()
        print("Success: PDF generation works!")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
