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
        if '.' in s: main, decimal = s.split('.')
        else: main, decimal = s, "00"
        l = len(main)
        if l <= 3: return f"{main}.{decimal}"
        res = main[-3:]; main = main[:-3]
        while len(main) > 0:
            if len(main) > 1: res = main[-2:] + "," + res; main = main[:-2]
            else: res = main + "," + res; main = ""
        return f"{res}.{decimal}"
    except: return "0.00"

class DPRPDFGenerator:
    """Sovereign PDF Generation Engine (Ported from Legacy Core)"""

    def __init__(self):
        self.page_width, self.page_height = A4
        self.margin = 0.75 * inch
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(name='DPRTitle', parent=self.styles['Heading1'], fontSize=24, alignment=TA_CENTER, spaceAfter=20, textColor=colors.HexColor('#1a365d'), fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='DPRSubtitle', parent=self.styles['Normal'], fontSize=14, alignment=TA_CENTER, spaceAfter=30, textColor=colors.HexColor('#4a5568')))
        self.styles.add(ParagraphStyle(name='SectionHeader', parent=self.styles['Heading2'], fontSize=14, spaceBefore=20, spaceAfter=10, textColor=colors.HexColor('#2d3748'), fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='DPRBodyText', parent=self.styles['Normal'], fontSize=10, spaceAfter=6, leading=14, textColor=colors.HexColor('#2d3748')))
        self.styles.add(ParagraphStyle(name='DPRBodyTextJustify', parent=self.styles['DPRBodyText'], alignment=TA_JUSTIFY))
        self.styles.add(ParagraphStyle(name='Caption', parent=self.styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceBefore=10, spaceAfter=10, textColor=colors.HexColor('#4a5568')))
        self.styles.add(ParagraphStyle(name='DocHeader', parent=self.styles['Normal'], fontSize=10, leading=12, textColor=colors.HexColor('#4a5568')))
        self.styles.add(ParagraphStyle(name='DocHeaderBold', parent=self.styles['DocHeader'], fontName='Helvetica-Bold'))
        self.styles.add(ParagraphStyle(name='DocTitle', parent=self.styles['Heading1'], fontSize=20, alignment=TA_CENTER, spaceAfter=24, textColor=colors.HexColor('#2d3748'), fontName='Helvetica-Bold'))

    def _get_logo_image(self, logo_base64: Optional[str], width=1.5*inch):
        if not logo_base64: return None
        try:
            if logo_base64.startswith('data:'): logo_base64 = logo_base64.split(',')[1]
            img_data = base64.b64decode(logo_base64)
            img = RLImage(BytesIO(img_data))
            aspect = img.imageHeight / img.imageWidth
            img.drawHeight = width * aspect
            img.drawWidth = width
            return img
        except: return None

    def generate_pdf(self, project_data: Dict[str, Any], dpr_data: Dict[str, Any], worker_log: Optional[Dict[str, Any]], images: List[Dict[str, Any]]) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        story = []
        story.extend(self._build_page_one(project_data, dpr_data, worker_log))
        for idx, image in enumerate(images):
            story.append(PageBreak())
            story.extend(self._build_image_page(image, idx + 1, len(images), project_data))
        doc.build(story)
        return buffer.getvalue()

    def _build_page_one(self, project_data: Dict[str, Any], dpr_data: Dict[str, Any], worker_log: Optional[Dict[str, Any]]) -> List:
        elements = []
        project_name = project_data.get('project_name', 'Project')
        project_code = project_data.get('project_code', 'N/A')
        elements.append(Paragraph("Daily Progress Report", self.styles['DPRTitle']))
        elements.append(Paragraph(f"{project_name} ({project_code})", self.styles['DPRSubtitle']))
        elements.append(Spacer(1, 20))
        # Project Details
        elements.append(Paragraph("📋 Project Details", self.styles['SectionHeader']))
        data = [['Project Name:', project_name], ['Project Code:', project_code], ['Weather:', dpr_data.get('weather_conditions', 'N/A')]]
        t = Table(data, colWidths=[2*inch, 4*inch])
        t.setStyle(TableStyle([('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'), ('ALIGN', (0, 0), (0, -1), 'RIGHT')]))
        elements.append(t)
        return elements

    def _build_image_page(self, image_data: Dict[str, Any], image_num: int, total_images: int, project_data: Dict[str, Any]) -> List:
        elements = []
        elements.append(Paragraph(f"Photo {image_num} of {total_images}", self.styles['Caption']))
        image_b64 = image_data.get('image_data', '') or image_data.get('base64', '')
        if image_b64:
            try:
                if image_b64.startswith('data:'): image_b64 = image_b64.split(',')[1]
                img_data = base64.b64decode(image_b64)
                img = RLImage(BytesIO(img_data))
                img._restrictSize(6*inch, 8*inch)
                elements.append(img)
            except: pass
        elements.append(Paragraph(image_data.get('caption', ''), self.styles['Caption']))
        return elements
