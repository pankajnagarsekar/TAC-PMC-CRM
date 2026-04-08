import logging
from app.core.time import now
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ExportService:

    """
    Sovereign Export Engine (Ported from Legacy Core).
    Handles Excel and PDF templates for construction reports.
    """

    REPORT_TEMPLATES = {
        "project_summary": {
            "description": "Project-level financial summary",
            "columns": [
                ("CODE", 10),
                ("Description", 30),
                ("Budget", 12),
                ("Committed", 12),
                ("Certified", 12),
                ("Remaining", 12),
                ("Status", 10),
            ],
            "template": "project_summary.html"
        },
        "work_order_tracker": {
            "description": "Work Order tracking report",
            "columns": [
                ("CODE", 10),
                ("WO Reference", 15),
                ("Vendor", 20),
                ("WO Value", 15),
                ("Retention", 15),
                ("Date", 12),
                ("Status", 13),
            ],
            "template": "work_order_tracker.html"
        },
        "payment_certificate_tracker": {
            "description": "PC tracking report",
            "columns": [
                ("CODE", 10),
                ("PC Reference", 15),
                ("Vendor", 20),
                ("Total Value", 15),
                ("Date", 12),
                ("Certified", 15),
                ("Status", 13),
            ],
            "template": "payment_certificate_tracker.html"
        },
        "petty_cash_tracker": {
            "description": "Petty Cash tracking report",
            "columns": [
                ("Date", 15),
                ("Ref", 20),
                ("Amount", 20),
                ("Description", 45),
            ],
            "template": "petty_cash_tracker.html"
        },
        "csa_report": {
            "description": "CSA Report",
            "columns": [
                ("CODE", 10),
                ("Ref", 15),
                ("Description", 40),
                ("Qty", 10),
                ("Date", 12),
            ],
            "template": "csa_report.html"
        },
        "attendance": {
            "description": "Attendance tracking",
            "columns": [
                ("Date", 12),
                ("Worker Name", 25),
                ("Category", 15),
                ("Check In", 12),
                ("Check Out", 12),
            ],
            "template": "attendance.html"
        },
        "dpr_report": {
            "description": "Daily Progress Report",
            "columns": [],
            "template": "dpr_report.html"
        },
        "weekly_progress": {
            "description": "Weekly Progress",
            "columns": [
                ("CODE", 10),
                ("Ref", 15),
                ("Vendor", 20),
                ("Progress (%)", 15),
                ("Status", 15),
            ],
            "template": "progress_report.html"
        },
        "15_days_progress": {
            "description": "15-Day Progress",
            "columns": [
                ("CODE", 10),
                ("Ref", 15),
                ("Vendor", 20),
                ("Progress (%)", 15),
                ("Status", 15),
            ],
            "template": "progress_report.html"
        },
        "monthly_progress": {
            "description": "Monthly Progress",
            "columns": [
                ("CODE", 10),
                ("Ref", 15),
                ("Vendor", 20),
                ("Progress (%)", 15),
                ("Status", 15),
            ],
            "template": "progress_report.html"
        },
        "scheduler_gantt": {
            "description": "High-fidelity Gantt Chart Export",
            "columns": [],
            "template": "scheduler_gantt.html"
        },
    }

    @staticmethod
    def format_currency(value: Any) -> str:
        if value is None:
            return "₹ 0.00"
        try:
            val = float(value)
            return f"₹ {val:,.2f}"
        except Exception:
            return str(value)

    @staticmethod
    def validate_report_type(rt: str) -> bool:
        return rt in ExportService.REPORT_TEMPLATES

    @staticmethod
    def export_to_excel(
        report_type: str,
        report_data: Dict[str, Any],
        company_info: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, Side

        wb = Workbook()
        ws = wb.active
        ws.title = "Report"

        config = ExportService.REPORT_TEMPLATES.get(report_type, {})
        columns = config.get("columns", [])

        # Header logic
        for col_idx, (col_name, width) in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = Font(bold=True)
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

        # Data logic
        rows = report_data.get("rows", [])
        for row_idx, row_data in enumerate(rows, 2):
            for col_idx, value in enumerate(row_data, 1):
                ws.cell(row=row_idx, column=col_idx, value=str(value))

        out = BytesIO()
        wb.save(out)
        return out.getvalue()

    @staticmethod
    def export_to_pdf_service(
        report_type: str,
        report_data: Dict[str, Any],
        company_info: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        import os
        try:
            import jinja2
        except ImportError:
            logger.error("Jinja2 package is not installed. Please install it using 'pip install jinja2'.")
            raise

        # Setup Jinja2 environment
        # Search for templates directory in multiple locations to support local dev and production
        search_paths = [
            os.path.join(os.getcwd(), "templates"),
            os.path.join(os.getcwd(), "apps", "api", "templates"),
            os.path.join(os.path.dirname(__file__), "..", "..", "templates"),
            os.path.join(os.path.dirname(__file__), "..", "templates"),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates"),
        ]
        
        template_dir = next((p for p in search_paths if os.path.exists(p)), search_paths[0])
        loader = jinja2.FileSystemLoader(template_dir)
        env = jinja2.Environment(loader=loader)
 
        config = ExportService.REPORT_TEMPLATES.get(report_type, {})
        template_name = config.get("template", "generic_report.html")
 
        try:
            template = env.get_template(template_name)
        except Exception as te:
            logger.warning(f"Template {template_name} not found in {template_dir}: {te}. Using string fallback.")
            template = env.from_string("""
                <html>
                <body>
                    <h1>{{ report_title }}</h1>
                    <table border="1">
                        <thead>
                            <tr>
                                {% for col in columns %}
                                <th>{{ col[0] }}</th>
                                {% endfor %}
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in rows %}
                            <tr>
                                {% for cell in row %}
                                <td>{{ cell }}</td>
                                {% endfor %}
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </body>
                </html>
            """)
 
        html_out = template.render(
            report_title=report_data.get("title", report_type.replace("_", " ").title()),
            rows=report_data.get("rows", []),
            columns=config.get("columns", []),
            totals=report_data.get("totals", {}),
            metadata=report_data.get("metadata", {}),
            company=company_info or {"name": "TAC PMC", "address": "Sovereign HQ"},
            now=now().strftime("%Y-%m-%d %H:%M:%S"),
            **report_data # Pass all other fields (tasks, months, etc.) for specialized templates
        )
 
        try:
            # Check if WeasyPrint is likely to work before attempting import
            # This avoids system-level DLL hangs on Windows if missing GTK
            from weasyprint import HTML
            pdf_bytes = HTML(string=html_out).write_pdf()
            return pdf_bytes
        except (ImportError, OSError, Exception) as e:
            # Fallback to ReportLab if WeasyPrint system dependencies are missing
            logger.error(f"WeasyPrint failed ({type(e).__name__}: {e}), falling back to ReportLab. HTML length: {len(html_out)}")
            try:
                return ExportService._generate_pdf_reportlab(report_data, config)
            except Exception as re:
                logger.error(f"ReportLab fallback also failed: {re}")
                raise RuntimeError("PDF generation failed: Both WeasyPrint and ReportLab engines are unavailable or encountered a terminal error.")

    @staticmethod
    def _generate_pdf_reportlab(report_data: Dict[str, Any], config: Dict[str, Any]) -> bytes:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title = report_data.get("title", "Report")
        elements.append(Paragraph(title, styles['Title']))
        elements.append(Spacer(1, 12))

        # Table Data
        headers = [col[0] for col in config.get("columns", [])]
        col_widths_raw = [col[1] for col in config.get("columns", [])]
        
        # Calculate absolute widths based on 500px content area
        total_relative = sum(col_widths_raw)
        if total_relative > 0:
            col_widths = [(w / total_relative) * 520 for w in col_widths_raw]
        else:
            # Fallback for empty columns
            col_widths = [100.0] * max(1, len(headers))

        rows = report_data.get("rows", [])
        if not rows and "tasks" in report_data:
            # Fallback for scheduler/Gantt reports in ReportLab (Point 118)
            rows = report_data["tasks"]
            if not config.get("columns"):
                 # Provide default columns for Gantt tasks if missing
                 config["columns"] = [
                     ("Task Name", 40),
                     ("Start", 15),
                     ("Finish", 15),
                     ("Duration", 10),
                     ("Predecessors", 20)
                 ]
                 headers = ["Task Name", "Start", "Finish", "Duration", "Predecessors"]
                 col_widths_raw = [40, 15, 15, 10, 20]
                 total_relative = sum(col_widths_raw)
                 col_widths = [(w / total_relative) * 520 for w in col_widths_raw]
        
        # Wrap data in Paragraphs to support multi-line text
        cell_style = styles["Normal"]
        cell_style.fontSize = 8
        
        if not headers and rows:
             # If no headers but we have rows, maybe they are dicts?
             # For 'exact' templates, rows (items) are often dicts.
             # ReportLab fallback is not great for dicts but let's try to show something.
             first_row = rows[0]
             if isinstance(first_row, dict):
                 headers = list(first_row.keys())
                 col_widths = [520 / len(headers)] * len(headers)

        data = [[Paragraph(str(h), styles["Normal"]) for h in headers]]
        for row in rows:
            if isinstance(row, dict):
                formatted_row = [Paragraph(str(row.get(h, "")), cell_style) for h in headers]
            else:
                formatted_row = [Paragraph(str(cell), cell_style) for cell in row]
            data.append(formatted_row)

        # Create Table
        t = Table(data, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))

        elements.append(t)
        doc.build(elements)
        return buffer.getvalue()


