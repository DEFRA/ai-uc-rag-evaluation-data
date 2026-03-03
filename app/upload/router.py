from logging import getLogger
from typing import Annotated

import fastapi
import pydantic

from app.upload import dependencies, service as upload_service

logger = getLogger(__name__)

router = fastapi.APIRouter(tags=["upload"])


class InitiateUploadRequest(pydantic.BaseModel):
    redirect: str
    groupId: str


@router.post("/upload-initiate")
async def upload_initiate(
    request: InitiateUploadRequest,
    service: Annotated[
        upload_service.UploadService,
        fastapi.Depends(dependencies.get_upload_service),
    ],
):

    logger.info("Initiating upload with redirect: %s", request.redirect)

    return await service.initiate_upload(
        redirect=request.redirect,
        groupId=request.groupId
    )