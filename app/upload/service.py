from logging import getLogger

from app.common import http_client

logger = getLogger(__name__)


class UploadService:
    def __init__(self, cdp_uploader_url: str, s3_bucket: str):
        self._cdp_uploader_url = cdp_uploader_url
        self._s3_bucket = s3_bucket

    async def initiate_upload(
        self,
        redirect: str,
        groupId: str
    ) -> str:
        payload = {
            "redirect": redirect,
            "s3Bucket": self._s3_bucket,
            "metadata": {
                groupId: groupId,
            },
        }

        async with http_client.create_async_client() as client:
            response = await client.post(
                f"{self._cdp_uploader_url}/initiate",
                json=payload,
            )

        logger.error(
            "CDP uploader response status: %s content-type: %s, body: %s",
            response.status_code,
            response.headers.get("content-type"),
            response.text,
        )

        if response.status_code != 201:
            raise ValueError(
                f"CDP uploader initiate failed with status {response.status_code}: {response.text}"
            )

        return response.json()