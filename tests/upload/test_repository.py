from unittest.mock import AsyncMock, MagicMock

import pytest

from app.upload import models
from app.upload.repository import UploadRecordRepository


@pytest.fixture
def mock_collection():
    return AsyncMock()


@pytest.fixture
def repo(mock_collection):
    db = MagicMock()
    db.get_collection.return_value = mock_collection
    return UploadRecordRepository(db)


@pytest.mark.asyncio
async def test_save(repo, mock_collection):
    record = models.UploadRecord(
        upload_status="ready", location="s3://bucket/file.jsonl"
    )

    await repo.save(record)

    mock_collection.insert_one.assert_called_once()
    doc = mock_collection.insert_one.call_args[0][0]
    assert doc["uploadStatus"] == "ready"
    assert doc["location"] == "s3://bucket/file.jsonl"


@pytest.mark.asyncio
async def test_get_status_by_location_returns_status(repo, mock_collection):
    mock_collection.find_one.return_value = {
        "uploadStatus": "ready",
        "location": "s3://bucket/file.jsonl",
    }

    result = await repo.get_status_by_location("s3://bucket/file.jsonl")

    assert result == "ready"


@pytest.mark.asyncio
async def test_get_status_by_location_returns_none_when_not_found(
    repo, mock_collection
):
    mock_collection.find_one.return_value = None

    result = await repo.get_status_by_location("s3://bucket/missing.jsonl")

    assert result is None
