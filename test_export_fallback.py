import sys
import os
# Add apps/api to path
sys.path.append(os.path.join(os.getcwd(), "apps", "api"))

from app.core.export_service import ExportService
from decimal import Decimal

report_data = {
    "title": "Test Fallback Report",
    "rows": [
        ["C01", "Test Item 1", "₹ 1,000.00", "₹ 500.00", "₹ 200.00", "₹ 800.00", "Active"],
        ["C02", "Test Item 2 with long description that should wrap in the table cell to prevent overflow in the PDF document", "₹ 2,000.00", "₹ 1,500.00", "₹ 1,200.00", "₹ 800.00", "Active"]
    ],
    "totals": {"total_budget": "3000.00"}
}

try:
    print("Attempting to generate PDF...")
    # This should now fallback to ReportLab since we know WeasyPrint is broken on this environment
    pdf_bytes = ExportService.export_to_pdf_service("project_summary", report_data)
    
    with open("test_fallback.pdf", "wb") as f:
        f.write(pdf_bytes)
    
    print(f"SUCCESS: Generated PDF ({len(pdf_bytes)} bytes)")
    print("Check test_fallback.pdf in the root directory.")
except Exception as e:
    import traceback
    print(f"FAILURE: {str(e)}")
    print(traceback.format_exc())
