from logging import getLogger
from typing import Annotated

import fastapi
import pydantic

from app.upload import dependencies
from app.upload import service as upload_service

logger = getLogger(__name__)

router = fastapi.APIRouter(tags=["upload"])


class InitiateUploadRequest(pydantic.BaseModel):  # noqa: N815
    redirect: str
    groupId: str  # noqa: N815


@router.post("/upload-initiate")
async def upload_initiate(
    request: InitiateUploadRequest,
    service: Annotated[
        upload_service.UploadService,
        fastapi.Depends(dependencies.get_upload_service),
    ],
):
    log_statement = f"Redirect url set to {request.redirect}"
    logger.info(log_statement)
    return await service.initiate_upload(
        redirect=request.redirect,
        group_id=request.groupId,
    )


class UploadCompletedRequest(pydantic.BaseModel):
    class Metadata(pydantic.BaseModel):
        groupId: str  # noqa: N815

    class Form(pydantic.BaseModel):
        class File(pydantic.BaseModel):
            s3Key: str  # noqa: N815
            s3Bucket: str  # noqa: N815

        file: File

    uploadStatus: str  # noqa: N815
    metadata: Metadata
    form: Form


@router.post("/upload-completed")
async def upload_completed(
    body: UploadCompletedRequest,
    upload_service: Annotated[
        upload_service.UploadService,
        fastapi.Depends(dependencies.get_upload_service),
    ],
):
    await upload_service.save_completed(
        upload_status=body.uploadStatus,
        s3_bucket=body.form.file.s3Bucket,
        s3_key=body.form.file.s3Key,
    )

    return fastapi.Response(status_code=fastapi.status.HTTP_200_OK)
