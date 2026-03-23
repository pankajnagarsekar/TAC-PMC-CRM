"""
DPR PDF Generation Service

Generates professional PDF reports with:
- Page 1: Project details, Voice summary, Worker attendance
- Page 2+: One image per page with caption

Filename format: "ProjectCode - MMM DD, YYYY.pdf"
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from datetime import datetime
from typing import Dict, List, Any, Optional
from io import BytesIO
import base64
import logging

logger = logging.getLogger(__name__)

def format_indian_currency(number: float) -> str:
    """Format number with Indian comma system (Lakhs, Crores)"""
    try:
        s = f"{float(number):.2f}"
        if '.' in s:
            main, decimal = s.split('.')
        else:
            main, decimal = s, "00"
            
        l = len(main)
        if l <= 3:
            return f"{main}.{decimal}"
        
        # Last 3 digits
        res = main[-3:]
        main = main[:-3]
        
        # Pairs of digits
        while len(main) > 0:
            if len(main) > 1:
                res = main[-2:] + "," + res
                main = main[:-2]
            else:
                res = main + "," + res
                main = ""
        return f"{res}.{decimal}"
    except (ValueError, TypeError):
        return "0.00"

class DPRPDFGenerator:
    """Generate professional PDF reports"""

    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 0.75 * inch
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='DPRTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=TA_CENTER,
            spaceAfter=20,
            textColor=colors.HexColor('#1a365d'),
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='DPRSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=30,
            textColor=colors.HexColor('#4a5568')
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#2d3748'),
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='DPRBodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            leading=14,
            textColor=colors.HexColor('#2d3748')
        ))

        self.styles.add(ParagraphStyle(
            name='DPRBodyTextJustify',
            parent=self.styles['DPRBodyText'],
            alignment=TA_JUSTIFY
        ))

        self.styles.add(ParagraphStyle(
            name='Caption',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceBefore=10,
            spaceAfter=10,
            textColor=colors.HexColor('#4a5568')
        ))

        self.styles.add(ParagraphStyle(
            name='DocHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12,
            textColor=colors.HexColor('#4a5568')
        ))

        self.styles.add(ParagraphStyle(
            name='DocHeaderBold',
            parent=self.styles['DocHeader'],
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='DocTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=24,
            textColor=colors.HexColor('#2d3748'),
            fontName='Helvetica-Bold'
        ))

    def _get_logo_image(self, logo_base64: Optional[str], width=1.5*inch):
        """Helper to convert base64 logo to ReportLab Image"""
        if not logo_base64:
            return None
        try:
            if logo_base64.startswith('data:'):
                logo_base64 = logo_base64.split(',')[1]
            img_data = base64.b64decode(logo_base64)
            img_buffer = BytesIO(img_data)
            img = RLImage(img_buffer)
            # Maintain aspect ratio
            aspect = img.imageHeight / img.imageWidth
            img.drawHeight = width * aspect
            img.drawWidth = width
            return img
        except Exception as e:
            logger.error(f"Failed to process logo: {e}")
            return None

    def generate_pdf(
        self,
        project_data: Dict[str, Any],
        dpr_data: Dict[str, Any],
        worker_log: Optional[Dict[str, Any]],
        images: List[Dict[str, Any]]
    ) -> bytes:
        """
        Generate complete DPR PDF

        Args:
            project_data: Project info (name, code, etc.)
            dpr_data: DPR details (date, summary, weather, etc.)
            worker_log: Worker attendance data
            images: List of images with captions

        Returns:
            PDF bytes
        """
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        story = []

        # Page 1: Project Details, Summary, Worker Attendance
        story.extend(self._build_page_one(project_data, dpr_data, worker_log))

        # Page 2+: One image per page with caption
        for idx, image in enumerate(images):
            story.append(PageBreak())
            story.extend(
                self._build_image_page(
                    image,
                    idx + 1,
                    len(images),
                    project_data))

        # Build PDF
        doc.build(story)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def generate_work_order_pdf(self, wo_data: Dict[str, Any], settings: Dict[str, Any], vendor_data: Optional[Dict[str, Any]] = None) -> bytes:
        """Generate professional Work Order PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        story = []

        # 1. Header with Logo and Company Info
        logo = self._get_logo_image(settings.get('logo_base64'))
        company_name = str(settings.get('name') or 'TAC PMC')
        company_address = str(settings.get('address') or '')
        company_gst = str(settings.get('gst_number') or '')

        header_data = []
        company_info = [
            Paragraph(f"<b>{company_name}</b>", self.styles['DocHeaderBold']),
            Paragraph(company_address, self.styles['DocHeader']) if company_address else Spacer(1, 1),
            Paragraph(f"GST No: {company_gst}", self.styles['DocHeader']) if company_gst else Spacer(1, 1),
        ]
        
        if logo:
            header_data.append([logo, company_info])
        else:
            header_data.append([company_info])

        header_table = Table(header_data, colWidths=[2*inch, 4*inch] if logo else [6*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))

        # 2. Document Title
        story.append(Paragraph("WORK ORDER", self.styles['DocTitle']))

        # 3. WO Metadata (Ref, Date, etc.)
        wo_ref = wo_data.get('wo_ref', 'N/A')
        wo_date = wo_data.get('created_at')
        if isinstance(wo_date, datetime):
            wo_date_str = wo_date.strftime("%B %d, %Y")
        else:
            wo_date_str = "N/A"

        meta_data = [
            [Paragraph(f"<b>WO Refn:</b> {wo_ref}", self.styles['DocHeader']), 
             Paragraph(f"<b>WO Date:</b> {wo_date_str}", self.styles['DocHeader'])],
            [Paragraph(f"<b>ISSUED BY:</b> {company_name}", self.styles['DocHeader']), ""]
        ]
        meta_table = Table(meta_data, colWidths=[4*inch, 2.5*inch])
        meta_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 20))

        # 4. Vendor and Shipping Info
        vendor_name = str(vendor_data.get('name') or 'N/A') if vendor_data else 'N/A'
        vendor_address = str(vendor_data.get('address') or 'N/A') if vendor_data else 'N/A'
        
        info_data = [
            [Paragraph("<b>To,</b>", self.styles['DocHeader']), Paragraph("<b>Shipping to,</b>", self.styles['DocHeader'])],
            [Paragraph(vendor_name, self.styles['DocHeaderBold']), Paragraph(str(settings.get('shipping_address') or 'As per project location'), self.styles['DocHeader'])],
            [Paragraph(vendor_address, self.styles['DocHeader']), ""]
        ]
        info_table = Table(info_data, colWidths=[3.25*inch, 3.25*inch])
        info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))

        # 5. Line Items Table
        items_data = [[
            Paragraph('<b>Sr No.</b>', self.styles['DocHeader']),
            Paragraph('<b>Description</b>', self.styles['DocHeader']),
            Paragraph('<b>Quantity</b>', self.styles['DocHeader']),
            Paragraph('<b>Rate</b>', self.styles['DocHeader']),
            Paragraph('<b>Total</b>', self.styles['DocHeader'])
        ]]
        
        for idx, item in enumerate(wo_data.get('line_items', [])):
            items_data.append([
                str(idx + 1),
                Paragraph(str(item.get('description') or ''), self.styles['DPRBodyText']),
                format_indian_currency(item.get('qty') or 0),
                format_indian_currency(item.get('rate') or 0),
                format_indian_currency(item.get('total') or 0),
            ])
        
        items_table = Table(items_data, colWidths=[0.6*inch, 3.2*inch, 0.9*inch, 0.9*inch, 1.1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'), # Sr No Header Center
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),   # Description Header Left
            ('ALIGN', (2, 0), (-1, 0), 'RIGHT'), # Numeric Headers Right
            ('ALIGN', (0, 1), (0, -1), 'CENTER'), # Sr No Data Center
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),   # Description Data Left
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'), # Numeric Data Right
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 15))

        # 6. Financial Summary Footer
        story.append(Paragraph("<b>Notes & Payment Terms:</b>", self.styles['DocHeaderBold']))
        story.append(Paragraph("5% Retention applicable on all PC (Ref 16)", self.styles['DPRBodyText']))
        story.append(Spacer(1, 15))

        summary_data = [
            [Paragraph('Subtotal:', self.styles['DocHeader']), format_indian_currency(wo_data.get('subtotal') or 0)],
            [Paragraph('Discount:', self.styles['DocHeader']), format_indian_currency(wo_data.get('discount') or 0)],
            [Paragraph('CGST:', self.styles['DocHeader']), format_indian_currency(wo_data.get('cgst') or 0)],
            [Paragraph('SGST:', self.styles['DocHeader']), format_indian_currency(wo_data.get('sgst') or 0)],
            [Paragraph('<b>Grand Total:</b>', self.styles['DocHeader']), Paragraph(f"<b>{format_indian_currency(wo_data.get('grand_total') or 0)}</b>", self.styles['DocHeader'])],
            [Paragraph('Retention:', self.styles['DocHeader']), format_indian_currency(wo_data.get('retention_amount') or 0)],
            [Paragraph('<b>Total Payable:</b>', self.styles['DocHeader']), Paragraph(f"<b>{format_indian_currency(wo_data.get('total_payable') or 0)}</b>", self.styles['DocHeader'])],
        ]
        
        # We use a 2-column table and right-align the table itself to the page
        # The last column width (1.1*inch) matches the line items "Total" column
        summary_table = Table(summary_data, colWidths=[1.5*inch, 1.1*inch], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'), # Label Right
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'), # Value Right
            ('LINEBELOW', (0, 0), (1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0), # Remove right padding to align with table edge
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # 7. Timeline & Warranty
        timeline_data = [
            [Paragraph("<b>Timeline</b>", self.styles['SectionHeader']), Paragraph("<b>Warranty</b>", self.styles['SectionHeader'])],
            [Paragraph(f"Start Date: {str(wo_data.get('start_date') or 'N/A')}", self.styles['DocHeader']), 
             Paragraph("Product: N/A", self.styles['DocHeader'])],
            [Paragraph(f"End Date: {str(wo_data.get('end_date') or 'N/A')}", self.styles['DocHeader']), 
             Paragraph("Workmanship: 12 Months", self.styles['DocHeader'])]
        ]
        timeline_table = Table(timeline_data, colWidths=[3.25*inch, 3.25*inch])
        story.append(timeline_table)
        story.append(Spacer(1, 20))

        # Page 2: Terms and Conditions
        story.append(PageBreak())
        story.append(Paragraph("General Terms and Condition:", self.styles['SectionHeader']))
        story.append(Spacer(1, 10))

        terms = [
            "The Contractor shall ensure all labour, technicians and supervisors possess valid police verification documents, health cards and mandatory statutory clearances, available at all times during their engagement.",
            "The Contractor is fully responsible for safety of their workforce and must provide PPE such as safety shoes, helmets, belts, gloves and goggles.",
            "Any accident, injury or fatality shall be handled entirely by the Contractor including medical treatment, compensation and legal liability.",
            "Waste must be segregated, disposed safely and without burning or chemical dumping. Dust control and tidy operations must be maintained at all times.",
            "Contractor shall maintain daily site cleanliness. All debris or waste shall be stored at a designated area and cleared regularly to prevent obstruction to other works or safety hazards.",
            "Works must be executed strictly as per approved drawings, materials and specifications within stipulated timelines.",
            "Contractor is responsible for safe storage and protection of all materials (client-supplied or contractor-supplied). Any losses or damages due to improper handling will be recovered from the Contractor.",
            "All work shall follow approved site working hours. High-noise or disruptive tasks shall require 24-hour prior intimation to PMC.",
            "All PMC observations and instructions will be issued only to the Contractor’s designated site supervisor. No direct instruction will be given to labour.",
            "Any snags or defects identified by PMC must be rectified within the stipulated period. Failure to do so will result in corrective work being executed through alternate agencies at Contractor’s cost.",
            "Standard workmanship warranty of 12 Months from the date of Handover applicable to the Contractor’s. Any failure within the defects liability period shall be rectified without cost.",
            "Any increase or decrease in quantities or scope must be informed to PMC immediately. Revised Work Orders or Change Orders will be issued accordingly. Work executed without prior written approval will not be considered.",
            "Payment Certificates will be prepared by PMC based on joint measurements. Contractor must provide complete measurement sheets and ensure supervisor presence during inspections.",
            "All payments shall be released strictly against PMC-approved and signed Payment Certificates.",
            "Payment Certificates shall be prepared between the 25th and 30th of each month. Submissions outside this window will move to the next cycle.",
            "A 5% retention will be deducted from all payments. Retention will be released only after full completion of work and after a minimum three-month period post-monsoon, subject to no defects.",
            "Contractor personnel shall not share site photos, drawings, videos or project details on social media or externally without written approval from the Company/PMC.",
            "In case of breach of any clause or non-performance, the Company reserves the right to execute the works through alternate agencies. Any cost or time impact arising from such action will be fully recovered from the Contractor’s payments or retention."
        ]

        for i, term in enumerate(terms):
            story.append(Paragraph(f"{i+1}. {term}", self.styles['DPRBodyTextJustify']))
            story.append(Spacer(1, 4))

        story.append(Spacer(1, 30))

        # Signature Section
        sig_data = [
            [Paragraph("<b>Accepted and Agreed</b>", self.styles['DocHeaderBold']), ""],
            [Spacer(1, 40), Paragraph("_________________________", self.styles['DocHeader'])],
            [Paragraph(vendor_name, self.styles['DocHeaderBold']), Paragraph(f"For {company_name}", self.styles['DocHeaderBold'])],
        ]
        sig_table = Table(sig_data, colWidths=[3.25*inch, 3.25*inch])
        story.append(sig_table)

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def generate_payment_certificate_pdf(self, pc_data: Dict[str, Any], settings: Dict[str, Any], vendor_data: Optional[Dict[str, Any]] = None) -> bytes:
        """Generate professional Payment Certificate PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        story = []

        # 1. Header
        company_name = str(settings.get('name') or 'TAC PMC')
        logo = self._get_logo_image(settings.get('logo_base64'))
        
        header_data = []
        company_info = [
            Paragraph(f"<b>{company_name}</b>", self.styles['DocHeaderBold']),
            Paragraph(str(settings.get('address') or ''), self.styles['DocHeader']),
        ]
        
        if logo:
            header_data.append([logo, company_info])
        else:
            header_data.append([company_info])

        header_table = Table(header_data, colWidths=[2*inch, 4*inch] if logo else [6*inch])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))
        story.append(Paragraph("PAYMENT CERTIFICATE", self.styles['DocTitle']))

        # 2. Metadata Columns (Ref, Date)
        pc_ref = pc_data.get('pc_ref', 'N/A')
        pc_date = pc_data.get('created_at')
        if isinstance(pc_date, datetime):
            pc_date_str = pc_date.strftime("%B %d, %Y")
        else:
            pc_date_str = "N/A"
        
        vendor_name = str(vendor_data.get('name') or 'N/A') if vendor_data else 'N/A'
        vendor_gst = str(vendor_data.get('gstin') or 'N/A') if vendor_data else 'N/A'

        meta_data = [
            [Paragraph(f"<b>Contractor:</b> {vendor_name}", self.styles['DocHeader']), 
             Paragraph(f"<b>PC Refn:</b> {str(pc_data.get('pc_ref') or 'N/A')}", self.styles['DocHeader'])],
            [Paragraph(f"<b>GST No:</b> {vendor_gst}", self.styles['DocHeader']), 
             Paragraph(f"<b>PC Date:</b> {pc_date_str}", self.styles['DocHeader'])],
            ["", Paragraph(f"<b>WO Refn:</b> {str(pc_data.get('wo_ref') or 'N/A')}", self.styles['DocHeader'])]
        ]
        meta_table = Table(meta_data, colWidths=[4*inch, 2.5*inch])
        story.append(meta_table)
        story.append(Spacer(1, 15))

        # 3. Line Items Table
        items_data = [[
            Paragraph('<b>Sr. No.</b>', self.styles['DocHeader']),
            Paragraph('<b>Scope of Work</b>', self.styles['DocHeader']),
            Paragraph('<b>Rate</b>', self.styles['DocHeader']),
            Paragraph('<b>Qty</b>', self.styles['DocHeader']),
            Paragraph('<b>Unit</b>', self.styles['DocHeader']),
            Paragraph('<b>Total</b>', self.styles['DocHeader'])
        ]]
        
        for idx, item in enumerate(pc_data.get('line_items', [])):
            items_data.append([
                str(idx + 1),
                Paragraph(str(item.get('scope_of_work') or 'N/A'), self.styles['DPRBodyText']),
                format_indian_currency(item.get('rate') or 0),
                format_indian_currency(item.get('qty') or 0),
                str(item.get('unit') or 'N/A'),
                format_indian_currency(item.get('total') or 0),
            ])
        
        items_table = Table(items_data, colWidths=[0.6*inch, 2.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'), # Sr No Header Center
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),   # Scope Header Left
            ('ALIGN', (2, 0), (3, 0), 'RIGHT'),  # Rate, Qty Header Right
            ('ALIGN', (4, 0), (4, 0), 'CENTER'), # Unit Header Center
            ('ALIGN', (5, 0), (5, 0), 'RIGHT'),  # Total Header Right
            ('ALIGN', (0, 1), (0, -1), 'CENTER'), # Sr No Data Center
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),   # Scope Data Left
            ('ALIGN', (2, 1), (3, -1), 'RIGHT'),  # Rate, Qty Data Right
            ('ALIGN', (4, 1), (4, -1), 'CENTER'), # Unit Data Center
            ('ALIGN', (5, 1), (5, -1), 'RIGHT'),  # Total Data Right
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 10))

        # 4. Financial Summary Footer
        summary_data = [
            [Paragraph('Subtotal:', self.styles['DocHeader']), format_indian_currency(pc_data.get('subtotal') or 0)],
            [Paragraph('Retention:', self.styles['DocHeader']), format_indian_currency(pc_data.get('retention_amount') or 0)],
            [Paragraph('<b>After Retention:</b>', self.styles['DocHeader']), Paragraph(f"<b>{format_indian_currency(pc_data.get('total_after_retention') or 0)}</b>", self.styles['DocHeader'])],
            [Paragraph('CGST:', self.styles['DocHeader']), format_indian_currency(pc_data.get('cgst') or 0)],
            [Paragraph('SGST:', self.styles['DocHeader']), format_indian_currency(pc_data.get('sgst') or 0)],
            [Paragraph('<b>Grand Total:</b>', self.styles['DocHeader']), Paragraph(f"<b>{format_indian_currency(pc_data.get('grand_total') or 0)}</b>", self.styles['DocHeader'])],
        ]
        
        # 2-column table right-aligned to match the "Total" column width (1 inch) of the main table
        summary_table = Table(summary_data, colWidths=[1.5*inch, 1*inch], hAlign='RIGHT')
        summary_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))

        # 5. Comments Section
        story.append(Paragraph("<b>PMC Comments:</b>", self.styles['DocHeaderBold']))
        story.append(Paragraph(str(pc_data.get('remarks') or 'No additional comments.'), self.styles['DPRBodyText']))
        story.append(Spacer(1, 40))

        # 6. Signature Section
        sig_data = [
            [Paragraph("<b>Contractor Signature</b>", self.styles['DocHeaderBold']), 
             Paragraph("<b>PMC Signature</b>", self.styles['DocHeaderBold'])],
            [Spacer(1, 40), Paragraph("_________________________", self.styles['DocHeader'])],
            [Paragraph(vendor_name, self.styles['DocHeaderBold']), 
             Paragraph(f"For {company_name}", self.styles['DocHeaderBold'])],
        ]
        sig_table = Table(sig_data, colWidths=[3.25*inch, 3.25*inch])
        story.append(sig_table)

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _build_page_one(
        self,
        project_data: Dict[str, Any],
        dpr_data: Dict[str, Any],
        worker_log: Optional[Dict[str, Any]]
    ) -> List:
        """Build first page with project info, summary, and worker attendance"""
        elements = []

        # Header
        project_name = project_data.get('project_name', 'Project')
        project_code = project_data.get('project_code', 'N/A')

        # Title
        elements.append(
            Paragraph(
                "Daily Progress Report",
                self.styles['DPRTitle']))

        # Subtitle with project and date
        dpr_date = dpr_data.get('dpr_date')
        if isinstance(dpr_date, str):
            try:
                dpr_date = datetime.fromisoformat(
                    dpr_date.replace('Z', '+00:00'))
            except BaseException:
                dpr_date = datetime.now()
        elif not isinstance(dpr_date, datetime):
            dpr_date = datetime.now()

        date_str = dpr_date.strftime("%B %d, %Y")
        elements.append(
            Paragraph(
                f"{project_name} ({project_code})",
                self.styles['DPRSubtitle']))
        elements.append(Paragraph(date_str, self.styles['DPRSubtitle']))

        elements.append(Spacer(1, 20))

        # Project Details Section
        elements.append(
            Paragraph(
                "📋 Project Details",
                self.styles['SectionHeader']))

        project_table_data = [
            ['Project Name:', project_name],
            ['Project Code:', project_code],
            ['Report Date:', date_str],
            ['Weather:', dpr_data.get('weather_conditions', 'N/A')],
            ['Supervisor:', dpr_data.get('supervisor_name', 'N/A')],
        ]

        project_table = Table(
            project_table_data, colWidths=[
                2 * inch, 4 * inch])
        project_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#4a5568')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#2d3748')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(project_table)

        elements.append(Spacer(1, 20))

        # Voice Summary Section
        elements.append(
            Paragraph(
                "📝 Progress Summary",
                self.styles['SectionHeader']))

        summary_text = dpr_data.get(
            'progress_notes', '') or dpr_data.get(
            'voice_summary', '')
        if summary_text:
            elements.append(
                Paragraph(
                    summary_text,
                    self.styles['DPRBodyText']))
        else:
            elements.append(
                Paragraph(
                    "No summary provided.",
                    self.styles['DPRBodyText']))

        elements.append(Spacer(1, 20))

        # Worker Attendance Section
        elements.append(
            Paragraph(
                "👷 Worker Attendance",
                self.styles['SectionHeader']))

        if worker_log and (worker_log.get('entries')
                           or worker_log.get('workers')):
            entries = worker_log.get('entries', [])

            if entries:
                # New format with vendor entries
                worker_table_data = [['Vendor', 'Workers', 'Purpose of Work']]

                for entry in entries:
                    worker_table_data.append([
                        entry.get('vendor_name', 'N/A'),
                        str(entry.get('workers_count', 0)),
                        entry.get('purpose', 'N/A')
                    ])

                # Total row
                total_workers = sum(e.get('workers_count', 0) for e in entries)
                worker_table_data.append(['TOTAL', str(total_workers), ''])

                worker_table = Table(
                    worker_table_data, colWidths=[
                        2.5 * inch, 1 * inch, 3 * inch])
                worker_table.setStyle(TableStyle([
                    # Header
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 11),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

                    # Body
                    ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -2), 10),
                    ('ALIGN', (1, 1), (1, -1), 'CENTER'),

                    # Total row
                    ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),

                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                    ('TOPPADDING', (0, 0), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ]))
                elements.append(worker_table)
            else:
                # Legacy format or no entries
                total = worker_log.get('total_workers', 0)
                elements.append(
                    Paragraph(
                        f"Total Workers: {total}",
                        self.styles['DPRBodyText']))
        else:
            elements.append(
                Paragraph(
                    "No worker attendance recorded.",
                    self.styles['DPRBodyText']))

        return elements

    def _build_image_page(
        self,
        image_data: Dict[str, Any],
        image_num: int,
        total_images: int,
        project_data: Dict[str, Any]
    ) -> List:
        """Build a page with single image and caption"""
        elements = []

        # Page header
        elements.append(Paragraph(
            f"Photo {image_num} of {total_images}",
            self.styles['PhotoNumber']
        ))

        elements.append(Spacer(1, 10))

        # Image
        image_b64 = image_data.get(
            'image_data', '') or image_data.get(
            'base64', '')

        if image_b64:
            try:
                # Remove data URL prefix if present
                if image_b64.startswith('data:'):
                    image_b64 = image_b64.split(
                        ',')[1] if ',' in image_b64 else image_b64

                image_bytes = base64.b64decode(image_b64)
                image_buffer = BytesIO(image_bytes)

                # Calculate image dimensions to fit page
                available_width = self.page_width - 2 * self.margin
                available_height = self.page_height - 3 * \
                    inch  # Leave space for header and caption

                # Create image with max dimensions
                img = RLImage(image_buffer)

                # Scale to fit
                img_width = available_width
                img_height = available_height

                # Maintain aspect ratio (assume portrait 9:16)
                aspect_ratio = 9 / 16
                if img_width / img_height > aspect_ratio:
                    img_width = img_height * aspect_ratio
                else:
                    img_height = img_width / aspect_ratio

                img._restrictSize(img_width, img_height)

                elements.append(img)

            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                elements.append(Paragraph(
                    "[Image could not be processed]",
                    self.styles['Caption']
                ))
        else:
            elements.append(Paragraph(
                "[No image data]",
                self.styles['Caption']
            ))

        # Caption
        caption = image_data.get(
            'caption', '') or image_data.get(
            'ai_caption', '')
        if caption:
            elements.append(Paragraph(caption, self.styles['Caption']))

        return elements

    def get_filename(self, project_code: str, dpr_date: datetime) -> str:
        """
        Generate filename in format: "ProjectCode - MMM DD, YYYY.pdf"

        Example: "MCT-2025 - Feb 19, 2025.pdf"
        """
        date_str = dpr_date.strftime("%b %d, %Y")
        return f"{project_code} - {date_str}.pdf"

    def get_wo_filename(self, wo_ref: str) -> str:
        """Generate filename for Work Order"""
        return f"Work Order - {wo_ref}.pdf"

    def get_pc_filename(self, pc_ref: str) -> str:
        """Generate filename for Payment Certificate"""
        return f"Payment Certificate - {pc_ref}.pdf"

    async def generate_attendance_report(
        self,
        project_id: str,
        attendance: List[Dict[str, Any]],
        worker_logs: List[Dict[str, Any]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> bytes:
        """
        Generate a comprehensive Attendance and Worker Log report PDF.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )

        story = []

        # Title
        story.append(Paragraph("Attendance & Worker Log Report", self.styles['DPRTitle']))

        # Subtitle
        date_range = "All Time"
        if start_date and end_date:
            date_range = f"{start_date} to {end_date}"
        elif start_date:
            date_range = f"From {start_date}"
        elif end_date:
            date_range = f"Up to {end_date}"

        story.append(Paragraph(f"Project: {project_id}", self.styles['DPRSubtitle']))
        story.append(Paragraph(f"Period: {date_range}", self.styles['DPRSubtitle']))
        story.append(Spacer(1, 20))

        # 1. Supervisor Attendance Section
        story.append(Paragraph("📋 Supervisor Attendance", self.styles['SectionHeader']))
        if attendance:
            story.extend(self._build_attendance_table(attendance))
        else:
            story.append(Paragraph("No supervisor attendance records found for this period.", self.styles['DPRBodyText']))

        story.append(Spacer(1, 30))

        # 2. Worker Logs Section
        story.append(Paragraph("👷 Worker Logs", self.styles['SectionHeader']))
        if worker_logs:
            story.extend(self._build_worker_logs_table(worker_logs))
        else:
            story.append(Paragraph("No worker logs found for this period.", self.styles['DPRBodyText']))

        # Build PDF
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _build_attendance_table(self, attendance: List[Dict[str, Any]]) -> List:
        """Build table for supervisor attendance"""
        data = [['Date', 'Supervisor', 'Check-in Time', 'Status']]

        for record in attendance:
            # Extract check_in_time which is a datetime object or ISO string in some cases
            cIn_obj = record.get('check_in_time')

            dStr = "N/A"
            tStr = "N/A"

            if isinstance(cIn_obj, datetime):
                dStr = cIn_obj.strftime("%Y-%m-%d")
                tStr = cIn_obj.strftime("%H:%M")
            elif isinstance(cIn_obj, str):
                try:
                    # Try parsing ISO format
                    parsed = datetime.fromisoformat(cIn_obj.replace('Z', '+00:00'))
                    dStr = parsed.strftime("%Y-%m-%d")
                    tStr = parsed.strftime("%H:%M")
                except Exception:
                    tStr = cIn_obj

            sName = record.get('user_name', 'N/A')
            status = record.get('status', 'Present').capitalize()

            data.append([dStr, sName, tStr, status])

        table = Table(data, colWidths=[1.5*inch, 2.5*inch, 1.5*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        return [table]

    def _build_worker_logs_table(self, logs: List[Dict[str, Any]]) -> List:
        """Build detailed table for worker logs"""
        elements = []

        # We'll group entries by date for better readability if there's a lot of data,
        # or just a flat list? Let's do a table with Date/Vendor/Count/Purpose
        data = [['Date', 'Vendor', 'Count', 'Purpose']]

        for log in logs:
            date = log.get('date', 'N/A')
            entries = log.get('entries', [])
            for entry in entries:
                data.append([
                    date,
                    entry.get('vendor_name', 'N/A'),
                    str(entry.get('workers_count', 0)),
                    entry.get('remarks', entry.get('purpose', 'N/A'))
                ])

        if len(data) == 1:  # Only header
            return [Paragraph("No detailed entries found.", self.styles['DPRBodyText'])]

        table = Table(data, colWidths=[1.2*inch, 1.8*inch, 0.8*inch, 2.7*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (2, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
        return elements


# Singleton instance
pdf_generator = DPRPDFGenerator()
