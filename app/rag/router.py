import logging
from typing import Annotated

import fastapi

from app.knowledge_management import models as km_models
from app.rag import api_schemas, dependencies
from app.rag.service import RagService
from app.snapshot import models as snapshot_models

logger = logging.getLogger(__name__)
router = fastapi.APIRouter(tags=["rag"])


@router.post(
    "/knowledge/groups/{group_id}/ask",
    response_model=api_schemas.AskResponse,
)
async def ask(
    group_id: str,
    request: api_schemas.AskRequest,
    service: Annotated[RagService, fastapi.Depends(dependencies.get_rag_service)],
):
    """
    Answer a question using retrieval-augmented generation against a knowledge group.

    Retrieves the most relevant documents from the group's active snapshot and uses
    a Bedrock LLM to generate a grounded answer.

    Args:
        group_id: The ID of the knowledge group to search
        request: The question and retrieval parameters

    Returns:
        A generated answer with the source documents used

    Raises:
        HTTPException 400: If the group does not exist or has no active snapshot
    """
    try:
        return await service.ask(
            group_id, request.question, request.max_context_results
        )
    except km_models.KnowledgeGroupNotFoundError as err:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge group with ID '{group_id}' not found",
        ) from err
    except snapshot_models.NoActiveSnapshotError as err:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail=f"Knowledge group with ID '{group_id}' has no active snapshot",
        ) from err
