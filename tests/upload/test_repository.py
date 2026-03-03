from unittest.mock import AsyncMock, MagicMock

import pytest

from app.upload import models
from app.upload.repository import UploadRecordRepository


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    return session


@pytest.fixture
def repo(mock_session):
    return UploadRecordRepository(MagicMock(return_value=mock_session))


@pytest.mark.asyncio
async def test_save(repo, mock_session):
    record = models.UploadRecord(
        upload_status="ready", location="s3://bucket/file.jsonl"
    )

    await repo.save(record)

    mock_session.add.assert_called_once_with(record)
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_status_by_location_returns_status(repo, mock_session):
    mock_row = MagicMock()
    mock_row.upload_status = "ready"
    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_session.execute.return_value = mock_result

    result = await repo.get_status_by_location("s3://bucket/file.jsonl")

    assert result == "ready"


@pytest.mark.asyncio
async def test_get_status_by_location_returns_none_when_not_found(repo, mock_session):
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repo.get_status_by_location("s3://bucket/missing.jsonl")

    assert result is None
