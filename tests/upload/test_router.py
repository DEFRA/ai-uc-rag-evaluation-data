from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.infra.fastapi_app import app
from app.upload import dependencies


@pytest.fixture
def mock_upload_repo():
    repo = AsyncMock()
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def client(mock_upload_repo):
    app.dependency_overrides[dependencies.get_upload_record_repository] = (
        lambda: mock_upload_repo
    )
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def mock_cdp_uploader_response():
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "uploadId": "abc123",
        "uploadUrl": "http://upload-here",
    }
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def test_upload_initiate_success(client, mock_cdp_uploader_response):
    with patch(
        "app.upload.service.http_client.create_async_client",
        return_value=mock_cdp_uploader_response,
    ):
        response = client.post(
            "/upload-initiate",
            json={"redirect": "/done", "groupId": "kg_123"},
        )

    assert response.status_code == 200
    assert response.json() == {"uploadId": "abc123", "uploadUrl": "http://upload-here"}
    mock_cdp_uploader_response.post.assert_called_once_with(
        "http://uploader/initiate",
        json={
            "redirect": "/done",
            "callback": "http://callback/upload-completed",
            "s3Bucket": "ai-uc-rag-evolution-data-ingestion-data",
            "metadata": {"groupId": "kg_123"},
        },
    )


def test_upload_initiate_missing_fields(client):
    response = client.post("/upload-initiate", json={})
    assert response.status_code == 400


def test_upload_initiate_cdp_error(client, mock_cdp_uploader_response):
    mock_cdp_uploader_response.post.return_value.status_code = 400
    mock_cdp_uploader_response.post.return_value.text = "Bad Request"

    with patch(
        "app.upload.service.http_client.create_async_client",
        return_value=mock_cdp_uploader_response,
    ):
        response = client.post(
            "/upload-initiate",
            json={"redirect": "/done", "groupId": "kg_123"},
        )

    assert response.status_code == 500


COMPLETED_BODY = {
    "uploadStatus": "ready",
    "metadata": {"groupId": "kg_123"},
    "form": {
        "file": {
            "s3Key": "folder/file.jsonl",
            "s3Bucket": "my-bucket",
        }
    },
}


def test_upload_completed_success(client, mock_upload_repo):
    response = client.post("/upload-completed", json=COMPLETED_BODY)

    assert response.status_code == 200
    mock_upload_repo.save.assert_called_once()
    saved = mock_upload_repo.save.call_args[0][0]
    assert saved.upload_status == "ready"
    assert saved.location == "s3://my-bucket/folder/file.jsonl"


def test_upload_completed_missing_fields(client):
    response = client.post("/upload-completed", json={})
    assert response.status_code == 400
