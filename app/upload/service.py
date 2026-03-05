from logging import getLogger

from app.common import http_client
from app.upload import models, repository

logger = getLogger(__name__)


class UploadService:
    def __init__(
        self,
        cdp_uploader_url: str,
        s3_bucket: str,
        callback_base_url: str,
        upload_repo: repository.UploadRecordRepository,
    ):
        self._cdp_uploader_url = cdp_uploader_url
        self._s3_bucket = s3_bucket
        self._callback_base_url = callback_base_url
        self._upload_repo = upload_repo

    async def initiate_upload(
        self,
        redirect: str,
        group_id: str,
    ) -> str:
        payload = {
            "redirect": redirect,
            "callback": f"{self._callback_base_url}/upload-completed",
            "s3Bucket": self._s3_bucket,
            "metadata": {
                "groupId": group_id,
            },
        }

        async with http_client.create_async_client() as client:
            response = await client.post(
                f"{self._cdp_uploader_url}/initiate",
                json=payload,
            )

        if response.status_code != 201:
            error_message = f"CDP uploader initiate failed with status {response.status_code}: {response.text}"
            raise ValueError(error_message)

        return response.json()

    async def save_completed(
        self, upload_status: str, s3_bucket: str, s3_key: str
    ) -> None:
        location = f"s3://{s3_bucket}/{s3_key}"
        await self._upload_repo.save(
            models.UploadRecord(
                upload_status=upload_status,
                location=location,
            )
        )
