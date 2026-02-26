import logging
from typing import Annotated

import fastapi

from app.knowledge_management import dependencies as km_dependencies
from app.knowledge_management import models as km_models
from app.knowledge_management import service as km_service
from app.snapshot import api_schemas, dependencies, models, service

logger = logging.getLogger(__name__)
router = fastapi.APIRouter(tags=["snapshots"])


@router.get("/snapshots/{snapshot_id}", response_model=dict)
async def get_snapshot(
    snapshot_id: str,
    service: Annotated[
        service.SnapshotService,
        fastapi.Depends(dependencies.get_snapshot_service),
    ],
):
    """
    Retrieve a snapshot by its ID.

    Args:
        snapshot_id: The ID of the snapshot to retrieve
        service: Service dependency injection

    Returns:
        The snapshot data

    Raises:
        HTTPException: If snapshot is not found
    """
    try:
        snapshot = await service.get_by_id(snapshot_id)
    except models.KnowledgeSnapshotNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot with ID '{snapshot_id}' not found",
        ) from err

    return {
        "snapshotId": snapshot.snapshot_id,
        "groupId": snapshot.group_id,
        "version": snapshot.version,
        "createdAt": snapshot.created_at.isoformat(),
        "sources": list(snapshot.sources),
    }


@router.post(
    "/snapshots/query", response_model=list[api_schemas.KnowledgeVectorResultResponse]
)
async def query_snapshot(
    request: api_schemas.QuerySnapshotRequest,
    knowledge_service: Annotated[
        km_service.KnowledgeManagementService,
        fastapi.Depends(km_dependencies.get_knowledge_management_service),
    ],
    snp_service: Annotated[
        service.SnapshotService,
        fastapi.Depends(dependencies.get_snapshot_service),
    ],
):
    """
    Query a snapshot for relevant documents based on a search query.

    Args:
        request: The query request containing group_id, query, and max_results
        knowledge_service: Knowledge management service dependency injection
        snp_service: Snapshot service dependency injection
    Returns:
        A list of relevant documents
    """

    try:
        group = await knowledge_service.find_knowledge_group(request.group_id)

        if not group.active_snapshot:
            msg = f"Knowledge group with ID '{request.group_id}' has no active snapshot"
            raise models.NoActiveSnapshotError(msg)

        documents = await snp_service.search_similar(
            group, request.query, request.max_results
        )

        return [
            api_schemas.KnowledgeVectorResultResponse(
                content=doc.content,
                similarity_score=doc.similarity_score,
                similarity_category=doc.similarity_category,
                created_at=doc.created_at.isoformat(),
                source_id=doc.source_id,
                snapshot_id=doc.snapshot_id,
                name=doc.name,
                location=doc.location,
            )
            for doc in documents
        ]
    except km_models.KnowledgeGroupNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge group with ID '{request.group_id}' not found",
        ) from err
    except models.NoActiveSnapshotError as err:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge group with ID '{request.group_id}' has no active snapshot",
        ) from err


@router.patch(
    "/snapshots/{snapshot_id}/activate", status_code=fastapi.status.HTTP_200_OK
)
async def activate_snapshot(
    snapshot_id: str,
    snapshot_service: Annotated[
        service.SnapshotService,
        fastapi.Depends(dependencies.get_snapshot_service),
    ],
    knowledge_service: Annotated[
        km_service.KnowledgeManagementService,
        fastapi.Depends(km_dependencies.get_knowledge_management_service),
    ],
):
    """
    Activate a snapshot by setting it as the active snapshot for its knowledge group.

    Args:
        snapshot_id: The ID of the snapshot to activate
        snapshot_service: Snapshot service dependency injection
        knowledge_service: Knowledge management service dependency injection

    Returns:
        Success message

    Raises:
        HTTPException: If snapshot is not found
    """
    try:
        snapshot = await snapshot_service.get_by_id(snapshot_id)

        await knowledge_service.set_active_snapshot(
            group_id=snapshot.group_id, snapshot_id=snapshot_id
        )

        return {
            "message": f"Snapshot '{snapshot_id}' activated successfully for group '{snapshot.group_id}'"
        }
    except models.KnowledgeSnapshotNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Snapshot with ID '{snapshot_id}' not found",
        ) from err
    except km_models.KnowledgeGroupNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge group with ID '{snapshot.group_id}' does not exist",
        ) from err
