from abc import ABC, abstractmethod


class AbstractIngestionDataRepository(ABC):
    @abstractmethod
    def list(self, path: str) -> list[str]:
        """List all file IDs in the repository"""

    @abstractmethod
    def get(self, path: str) -> bytes | None:
        """Retrieve a file by its ID"""


class S3IngestionDataRepository(AbstractIngestionDataRepository):
    def __init__(self, s3_client, bucket_name: str):
        self.s3_client = s3_client
        self.bucket_name = bucket_name

    def list(self, path: str) -> list[str]:
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=path)
        if "Contents" not in response:
            return []
        return [item["Key"] for item in response["Contents"]]

    def get(self, path: str) -> bytes | None:
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=path)
        except self.s3_client.exceptions.NoSuchKey:
            return None

        return response["Body"].read()
