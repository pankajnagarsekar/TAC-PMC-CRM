from fastapi import APIRouter, Depends, Query, status
from typing import List

from app.core.dependencies import get_authenticated_user
from app.core.deps import get_client_service
from app.services.client_service import ClientService
from app.schemas.client import Client, ClientCreate, ClientUpdate

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("/", response_model=List[Client])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    return await client_service.list_clients(user["organisation_id"], skip, limit)

@router.post("/", response_model=Client, status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    return await client_service.create_client(user, client_data)

@router.get("/{client_id}", response_model=Client)
async def get_client(
    client_id: str,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    return await client_service.get_client(client_id, user["organisation_id"])

@router.put("/{client_id}", response_model=Client)
async def update_client(
    client_id: str,
    client_data: ClientUpdate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    return await client_service.update_client(user, client_id, client_data)

@router.delete("/{client_id}")
async def delete_client(
    client_id: str,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    return await client_service.delete_client(user, client_id)
