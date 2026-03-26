from fastapi import APIRouter, Depends, Query, status
from typing import List

from app.core.dependencies import get_authenticated_user, get_client_service
from app.services.client_service import ClientService
from app.schemas.client import Client, ClientCreate, ClientUpdate
from app.schemas.shared import GenericResponse

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("/", response_model=GenericResponse[List[Client]])
async def list_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    clients = await client_service.list_clients(user["organisation_id"], skip, limit)
    return GenericResponse(data=clients)

@router.post("/", response_model=GenericResponse[Client], status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: ClientCreate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    client = await client_service.create_client(user, client_data)
    return GenericResponse(data=client, message="Client created successfully")

@router.get("/{client_id}", response_model=GenericResponse[Client])
async def get_client(
    client_id: str,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    client = await client_service.get_client(client_id, user["organisation_id"])
    return GenericResponse(data=client)

@router.put("/{client_id}", response_model=GenericResponse[Client])
async def update_client(
    client_id: str,
    client_data: ClientUpdate,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    client = await client_service.update_client(user, client_id, client_data)
    return GenericResponse(data=client, message="Client updated successfully")

@router.delete("/{client_id}", response_model=GenericResponse[dict])
async def delete_client(
    client_id: str,
    user: dict = Depends(get_authenticated_user),
    client_service: ClientService = Depends(get_client_service)
):
    result = await client_service.delete_client(user, client_id)
    return GenericResponse(data=result, message="Client deleted successfully")
