from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.upload import service as upload_service


@pytest.fixture
def mock_upload_repo():
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def service(mock_upload_repo):
    return upload_service.UploadService(
        cdp_uploader_url="http://cdp-uploader",
        s3_bucket="test-bucket",
        callback_base_url="http://my-service",
        upload_repo=mock_upload_repo,
    )


@pytest.mark.asyncio
async def test_initiate_upload_success(service):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"uploadId": "abc123"}

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.upload.service.http_client.create_async_client", return_value=mock_client
    ):
        result = await service.initiate_upload(redirect="/done", group_id="kg_123")

    assert result == {"uploadId": "abc123"}
    mock_client.post.assert_called_once_with(
        "http://cdp-uploader/initiate",
        json={
            "redirect": "/done",
            "callback": "http://my-service/upload-completed",
            "s3Bucket": "test-bucket",
            "metadata": {"groupId": "kg_123"},
        },
    )


@pytest.mark.asyncio
async def test_initiate_upload_raises_on_non_201(service):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad Request"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "app.upload.service.http_client.create_async_client",
            return_value=mock_client,
        ),
        pytest.raises(ValueError, match="400"),
    ):
        await service.initiate_upload(redirect="/done", group_id="kg_123")


@pytest.mark.asyncio
async def test_save_completed(service, mock_upload_repo):
    await service.save_completed(
        upload_status="ready",
        s3_key="folder/file.jsonl",
    )

    mock_upload_repo.save.assert_called_once()
    saved_record = mock_upload_repo.save.call_args[0][0]
    assert saved_record.upload_status == "ready"
    assert saved_record.location == "folder/file.jsonl"
