from typing import Dict, List, Any, Optional
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class DPRPDFGenerator:
    def generate_pdf(self, project_data: Dict[str, Any], dpr_data: Dict[str, Any], worker_log: Optional[Dict[str, Any]], images: List[Dict[str, Any]]) -> bytes:
        return b"%PDF-1.4 mock content"

    def generate_work_order_pdf(self, wo_data: Dict[str, Any], settings: Dict[str, Any], vendor_data: Optional[Dict[str, Any]] = None) -> bytes:
        return b"%PDF-1.4 mock work order"

    def generate_payment_certificate_pdf(self, pc_data: Dict[str, Any], settings: Dict[str, Any], vendor_data: Optional[Dict[str, Any]] = None) -> bytes:
        return b"%PDF-1.4 mock payment certificate"
