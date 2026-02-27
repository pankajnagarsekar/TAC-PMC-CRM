from fastapi import APIRouter

hardened_router = APIRouter()


class _HardenedEngine:
    async def modify_budget(
            self,
            budget_id,
            organisation_id,
            user_id,
            new_amount):
        pass


hardened_engine = _HardenedEngine()
