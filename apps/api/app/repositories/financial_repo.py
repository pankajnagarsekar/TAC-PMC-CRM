from app.repositories.base_repo import BaseRepository
from app.schemas.financial import WorkOrder, PaymentCertificate

class WorkOrderRepository(BaseRepository[WorkOrder]):
    def __init__(self, db):
        super().__init__(db, "work_orders", WorkOrder)

class PCRepository(BaseRepository[PaymentCertificate]):
    def __init__(self, db):
        super().__init__(db, "payment_certificates", PaymentCertificate)
