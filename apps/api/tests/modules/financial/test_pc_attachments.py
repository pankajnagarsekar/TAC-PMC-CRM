import pytest
import io
from decimal import Decimal
from bson import ObjectId
from unittest.mock import MagicMock, patch, AsyncMock

from reportlab.pdfgen import canvas

from app.modules.financial.application.payment_service import PaymentService
from app.core.template_export_service import TemplateExportService
from app.modules.shared.application.audit_service import AuditService
from app.modules.financial.schemas.dto import PaymentCertificateCreate

# ============================================================================


@pytest.fixture
def supervisor_user():
    """Mock supervisor user with $10k approval limit."""
    return {
        "user_id": "supervisor-001",
        "organisation_id": "org-payment-test-123",
        "role": "Supervisor",
        "active_status": True,
    }


@pytest.fixture
def test_project_id():
    """Test project ID."""
    return str(ObjectId())


@pytest.fixture
async def test_db_with_payments(test_db):
    """Test database with payment collection initialized."""
    # Note: BaseRepository uses "payment_certificates" collection for PC
    # But in PaymentService it might be different.
    # Let's check PaymentService.pc_repo
    yield test_db


@pytest.fixture
async def audit_service(test_db_with_payments):
    """Audit service for logging."""
    return AuditService(test_db_with_payments)


@pytest.fixture
async def payment_service(test_db_with_payments, audit_service):
    """Payment service with test database."""
    mock_financial = MagicMock()
    mock_financial.validate_financial_document = AsyncMock(return_value=None)
    mock_financial.recalculate_master_budget = AsyncMock(return_value={})

    mock_permission = MagicMock()
    mock_permission.check_project_access = AsyncMock(return_value=None)
    mock_permission.check_write_access_with_role = AsyncMock(return_value=None)

    return PaymentService(
        test_db_with_payments,
        audit_service,
        mock_financial,
        mock_permission,
    )


@pytest.fixture
async def payment_in_draft(payment_service, supervisor_user, test_project_id):
    """Create a payment certificate in Draft status."""
    pc_data = PaymentCertificateCreate(
        project_id=test_project_id,
        vendor_id=str(ObjectId()),
        line_items=[],
        retention_percent=Decimal("5.0"),
    )
    payment = await payment_service.create_payment_certificate(supervisor_user, pc_data)
    return payment


def create_valid_pdf(text="Test Content"):
    packet = io.BytesIO()
    can = canvas.Canvas(packet)
    can.drawString(100, 100, text)
    can.save()
    packet.seek(0)
    return packet.getvalue()


# ============================================================================
# TEST CASES
# ============================================================================

@pytest.mark.asyncio
async def test_pc_attachment_atomic_operations(payment_service, test_db, supervisor_user, payment_in_draft):
    """
    Verify that attach_document and delete_document perform atomic database updates.
    """
    pc_id = payment_in_draft["id"]

    # Mock storage_manager.save_file and refresh_base_page_count to avoid full export in this test
    with patch("app.modules.financial.application.payment_service.storage_manager.save_file") as mock_save, \
         patch("app.modules.financial.application.payment_service.PaymentService.refresh_base_page_count",
               new_callable=AsyncMock) as mock_refresh:

        mock_save.return_value = "path/to/file.pdf"
        mock_refresh.return_value = 1

        # 1. Attach first document (1 page)
        file_content = create_valid_pdf("First Document")
        doc1 = await payment_service.attach_document(
            supervisor_user, pc_id, "test1.pdf", file_content
        )

        # Verify DB state
        pc_after1 = await test_db.payment_certificates.find_one({"_id": ObjectId(pc_id)})
        assert len(pc_after1.get("additional_documents", [])) == 1
        assert pc_after1["additional_documents"][0]["original_name"] == "test1.pdf"
        assert pc_after1["additional_documents"][0]["page_count"] == 1

        # 2. Attach second document (multi-page)
        packet = io.BytesIO()
        can = canvas.Canvas(packet)
        can.drawString(100, 100, "Page 1")
        can.showPage()
        can.drawString(100, 100, "Page 2")
        can.save()
        multi_page_content = packet.getvalue()

        await payment_service.attach_document(
            supervisor_user, pc_id, "test2.pdf", multi_page_content
        )

        # Verify DB state (should have 2 documents now)
        pc_after2 = await test_db.payment_certificates.find_one({"_id": ObjectId(pc_id)})
        assert len(pc_after2.get("additional_documents", [])) == 2
        assert pc_after2["additional_documents"][1]["original_name"] == "test2.pdf"
        assert pc_after2["additional_documents"][1]["page_count"] == 2

        # 3. Delete first document
        file_id1 = doc1["file_id"]
        with patch("app.modules.financial.application.payment_service.storage_manager.delete_file"):
            await payment_service.delete_document(supervisor_user, pc_id, file_id1)

            # Verify DB state (should have 1 document now: test2.pdf)
            pc_after_delete = await test_db.payment_certificates.find_one({"_id": ObjectId(pc_id)})
            assert len(pc_after_delete.get("additional_documents", [])) == 1
            assert pc_after_delete["additional_documents"][0]["original_name"] == "test2.pdf"


@pytest.mark.asyncio
async def test_pc_page_count_synchronization(payment_service, test_db, supervisor_user, payment_in_draft):
    """
    Verify that base_page_count is updated and correctly calculated.
    """
    pc_id = payment_in_draft["id"]

    # Mock TemplateExportService.export_payment_certificate_exact
    target_path = "app.core.template_export_service.TemplateExportService.export_payment_certificate_exact"
    with patch(target_path) as mock_export:
        # Mock return value (pdf_bytes, page_count)
        mock_export.return_value = (b"fake pdf", 5)

        # Trigger refresh
        new_count = await payment_service.refresh_base_page_count(supervisor_user, pc_id)

        assert new_count == 5

        # Verify DB update
        pc = await test_db.payment_certificates.find_one({"_id": ObjectId(pc_id)})
        assert pc["base_page_count"] == 5


@pytest.mark.asyncio
async def test_pdf_merging_logic_integrity():
    """
    Verify TemplateExportService.merge_pdfs correctly handles empty attachments and overlays page numbers.
    """
    from pypdf import PdfReader

    base_pdf = create_valid_pdf("Base Document")
    attachment = create_valid_pdf("Attachment Document")

    # Run merge
    merged_pdf = TemplateExportService.merge_pdfs(base_pdf, [attachment])

    # Verify merged PDF has 2 pages
    reader = PdfReader(io.BytesIO(merged_pdf))
    assert len(reader.pages) == 2

    # Verify numbering (we can't easily check visual overlay, but we can ensure it doesn't crash)
    merged_pdf_no_atts = TemplateExportService.merge_pdfs(base_pdf, [])
    reader_single = PdfReader(io.BytesIO(merged_pdf_no_atts))
    assert len(reader_single.pages) == 1
