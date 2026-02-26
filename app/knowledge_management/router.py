import datetime
from typing import Annotated

import fastapi

from app.ingestion import models as ingestion_models
from app.ingestion import service as ingestion_service
from app.knowledge_management import api_schemas, dependencies, models
from app.knowledge_management import service as km_service
from app.snapshot import dependencies as snapshot_dependencies
from app.snapshot import service as snapshot_service

router = fastapi.APIRouter(tags=["knowledge-management"])


def _map_sources(
    sources: dict[str, models.KnowledgeSource],
) -> dict[str, api_schemas.KnowledgeSourceResponse]:
    return {
        sid: api_schemas.KnowledgeSourceResponse(
            source_id=s.source_id, name=s.name, type=s.source_type, location=s.location
        )
        for sid, s in sources.items()
    }


@router.get(
    "/knowledge/groups",
    status_code=fastapi.status.HTTP_200_OK,
    response_model=list[api_schemas.KnowledgeGroupResponse],
    responses={
        fastapi.status.HTTP_204_NO_CONTENT: {"description": "No knowledge groups found"}
    },
)
async def list_groups(
    service: Annotated[
        km_service.KnowledgeManagementService,
        fastapi.Depends(dependencies.get_knowledge_management_service),
    ],
):
    """
    List all knowledge groups.

    Args:
        service: Service dependency injection

    Returns:
        A list of knowledge group responses
    """
    groups = await service.list_knowledge_groups()

    if len(groups) == 0:
        return fastapi.Response(status_code=fastapi.status.HTTP_204_NO_CONTENT)

    return [
        api_schemas.KnowledgeGroupResponse(
            group_id=group.group_id,
            title=group.name,
            description=group.description,
            owner=group.owner,
            created_at=group.created_at.isoformat(),
            updated_at=group.updated_at.isoformat(),
            sources=_map_sources(group.sources),
        )
        for group in groups
    ]


@router.post(
    "/knowledge/groups",
    status_code=fastapi.status.HTTP_201_CREATED,
    response_model=api_schemas.KnowledgeGroupResponse,
)
async def create_group(
    group: api_schemas.CreateKnowledgeGroupRequest,
    service: Annotated[
        km_service.KnowledgeManagementService,
        fastapi.Depends(dependencies.get_knowledge_management_service),
    ],
):
    """
    Create a new knowledge group.

    Args:
        group: The knowledge group request data
        service: Service dependency injection

    Returns:
        Success message with the created group name
    """
    knowledge_group = models.KnowledgeGroup(
        name=group.name,
        description=group.description,
        owner=group.owner,
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )

    for source in group.sources:
        knowledge_group.add_source(
            models.KnowledgeSource(
                name=source.name, source_type=source.type, location=source.location
            )
        )

    await service.create_knowledge_group(knowledge_group)

    return api_schemas.KnowledgeGroupResponse(
        group_id=knowledge_group.group_id,
        title=knowledge_group.name,
        description=knowledge_group.description,
        owner=knowledge_group.owner,
        created_at=knowledge_group.created_at.isoformat(),
        updated_at=knowledge_group.updated_at.isoformat(),
        sources=_map_sources(knowledge_group.sources),
    )


@router.get(
    "/knowledge/groups/{group_id}",
    response_model=api_schemas.KnowledgeGroupResponse,
    responses={
        fastapi.status.HTTP_404_NOT_FOUND: {"description": "Knowledge group not found"}
    },
)
async def get_group(
    group_id: str,
    service: Annotated[
        km_service.KnowledgeManagementService,
        fastapi.Depends(dependencies.get_knowledge_management_service),
    ],
):
    """
    Retrieve a knowledge group by its group ID.

    Args:
        group_id: The ID of the knowledge group to retrieve
        service: Service dependency injection

    Returns:
        The knowledge group response data or None if not found
    """
    try:
        group = await service.find_knowledge_group(group_id)

        return api_schemas.KnowledgeGroupResponse(
            group_id=group.group_id,
            title=group.name,
            description=group.description,
            owner=group.owner,
            created_at=group.created_at.isoformat(),
            updated_at=group.updated_at.isoformat(),
            sources=_map_sources(group.sources),
        )
    except models.KnowledgeGroupNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=404, detail=f"Knowledge group with ID '{group_id}' not found"
        ) from err


@router.get("/knowledge/groups/{group_id}/snapshots", response_model=list[dict])
async def list_group_snapshots(
    group_id: str,
    service: Annotated[
        snapshot_service.SnapshotService,
        fastapi.Depends(snapshot_dependencies.get_snapshot_service),
    ],
):
    """
    List all snapshots for a specific knowledge group.

    Args:
        group_id: The ID of the knowledge group
        service: Service dependency injection

    Returns:
        A list of snapshots for the group
    """
    snapshots = await service._snapshot_repo.list_snapshots_by_group(group_id)

    return [
        {
            "snapshot_id": snapshot.snapshot_id,
            "group_id": snapshot.group_id,
            "version": snapshot.version,
            "created_at": snapshot.created_at.isoformat(),
            "sources": [source.__dict__ for source in snapshot.sources.values()],
        }
        for snapshot in snapshots
    ]


@router.post(
    "/knowledge/groups/{group_id}/ingest",
    status_code=fastapi.status.HTTP_202_ACCEPTED,
    responses={
        fastapi.status.HTTP_404_NOT_FOUND: {"description": "Knowledge group not found"},
        fastapi.status.HTTP_409_CONFLICT: {
            "description": "Ingestion already in progress"
        },
    },
)
async def ingest_group(
    group_id: str,
    km_service: Annotated[
        km_service.KnowledgeManagementService,
        fastapi.Depends(dependencies.get_knowledge_management_service),
    ],
    ingestion_service: Annotated[
        ingestion_service.IngestionService,
        fastapi.Depends(dependencies.get_ingestion_service),
    ],
):
    """
    Initiate the ingestion process for a specific knowledge group.
    Each source will be processed individually.

    Args:
        group_id: The ID of the knowledge group to ingest
        km_service: Knowledge management service dependency injection
        ingestion_service: Ingestion service dependency injection
    Returns:
        Acknowledgment of ingestion initiation
    """

    try:
        group = await km_service.find_knowledge_group(group_id)

        if not group.sources:
            return {"message": f"No sources found for knowledge group '{group_id}'."}

        await ingestion_service.process_group(group)

        return {
            "message": f"Ingestion for knowledge group '{group_id}' has been initiated. Processing {len(group.sources)} sources individually."
        }
    except ingestion_models.IngestionAlreadyInProgressError as err:
        raise fastapi.HTTPException(
            status_code=409,
            detail=str(err),
        ) from err
    except models.KnowledgeGroupNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=404, detail=f"Knowledge group with ID '{group_id}' not found"
        ) from err


@router.patch(
    "/knowledge/groups/{group_id}/sources",
    response_model=api_schemas.KnowledgeGroupResponse,
    responses={
        fastapi.status.HTTP_404_NOT_FOUND: {"description": "Knowledge group not found"},
    },
)
async def add_source(
    group_id: str,
    source_data: api_schemas.KnowledgeSource,
    service: Annotated[
        km_service.KnowledgeManagementService,
        fastapi.Depends(dependencies.get_knowledge_management_service),
    ],
):
    """
    Add a source to a knowledge group.

    Args:
        group_id: The ID of the knowledge group
        source: The knowledge source to add
        service: Service dependency injection

    Returns:
        The updated knowledge group response data
    """
    try:
        source = models.KnowledgeSource(
            name=source_data.name,
            source_type=source_data.type,
            location=source_data.location,
        )

        group = await service.add_source_to_group(group_id, source)

        return api_schemas.KnowledgeGroupResponse(
            group_id=group.group_id,
            title=group.name,
            description=group.description,
            owner=group.owner,
            created_at=group.created_at.isoformat(),
            updated_at=group.updated_at.isoformat(),
            sources=_map_sources(group.sources),
        )
    except models.KnowledgeGroupNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=404, detail=f"Knowledge group with ID '{group_id}' not found"
        ) from err
