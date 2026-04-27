from typing import Any, Dict
from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_authenticated_user, get_snapshot_service
from app.modules.shared.application.snapshot_service import SnapshotService
from app.modules.shared.domain.schemas import GenericResponse

router = APIRouter()


@router.get(
    "/{entity_type}/{entity_id}/versions",
    response_model=GenericResponse[Dict[str, Any]],
)
async def list_snapshot_versions(
    entity_type: str,
    entity_id: str,
    user: dict = Depends(get_authenticated_user),
    service: SnapshotService = Depends(get_snapshot_service),
):
    """List all available snapshot versions for an entity."""
    # Note: entity_type from frontend is capitalized (e.g., DPR)
    # snapshot_service uses it as-is or mapped

    # We use list_snapshots but we need versions specifically
    # Let's check SnapshotService implementation in detail if it has a better method
    # Actually, SnapshotService.list_snapshots filters by organisation and project
    # But VersionSelector calls /snapshots/{type}/{id}/versions

    # We'll implement a helper in service or query repo directly here for now to match UI expectation
    from app.modules.shared.infrastructure.snapshot_repo import SnapshotRepository
    repo = SnapshotRepository(service.db)

    query = {"entity_type": entity_type.upper(), "entity_id": entity_id}
    snapshots = await repo.list(query, sort=[("version", -1)])

    versions = [
        {
            "version": s["version"],
            "snapshot_id": str(s["id"]),
            "created_at": (
                s["generated_at"].isoformat()
                if hasattr(s["generated_at"], "isoformat")
                else s["generated_at"]
            ),
            "is_current": s.get("is_latest", False)
        }
        for s in snapshots
    ]

    return GenericResponse(data={"versions": versions})


@router.get(
    "/{entity_type}/{entity_id}",
    response_model=GenericResponse[Dict[str, Any]],
)
async def get_snapshot_by_version(
    entity_type: str,
    entity_id: str,
    version: int = Query(...),
    user: dict = Depends(get_authenticated_user),
    service: SnapshotService = Depends(get_snapshot_service),
):
    """Retrieve specific snapshot data for an entity and version."""
    from app.modules.shared.infrastructure.snapshot_repo import SnapshotRepository
    repo = SnapshotRepository(service.db)

    query = {
        "entity_type": entity_type.upper(),
        "entity_id": entity_id,
        "version": version
    }
    snapshot = await repo.find_one(query)

    if not snapshot:
        from app.modules.shared.domain.exceptions import NotFoundError
        raise NotFoundError("Snapshot", f"{entity_type}/{entity_id} v{version}")

    return GenericResponse(data=snapshot.get("data_json", {}))
