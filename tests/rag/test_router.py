from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.infra.fastapi_app import app
from app.knowledge_management import models as km_models
from app.rag import api_schemas, dependencies
from app.snapshot import models as snapshot_models


@pytest.fixture
def mock_rag_service():
    return AsyncMock()


@pytest.fixture
def client(mock_rag_service):
    app.dependency_overrides[dependencies.get_rag_service] = lambda: mock_rag_service
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _make_ask_response(answer="The answer is 42.", sources=None):
    return api_schemas.AskResponse(
        answer=answer,
        sources=sources
        or [
            api_schemas.SourceReference(
                content="Relevant document content.",
                similarity_score=0.92,
                name="doc.pdf",
                location="s3://bucket/doc.pdf",
                source_id="src_001",
            )
        ],
    )


def test_ask_success(client, mock_rag_service):
    mock_rag_service.ask.return_value = _make_ask_response()

    response = client.post(
        "/knowledge/groups/group_123/ask",
        json={"question": "What is the answer?", "maxContextResults": 3},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "The answer is 42."
    assert len(body["sources"]) == 1
    assert body["sources"][0]["similarityScore"] == 0.92
    assert body["sources"][0]["sourceId"] == "src_001"

    mock_rag_service.ask.assert_called_once_with("group_123", "What is the answer?", 3)


def test_ask_uses_default_max_context_results(client, mock_rag_service):
    mock_rag_service.ask.return_value = _make_ask_response()

    client.post(
        "/knowledge/groups/group_123/ask",
        json={"question": "What is the answer?"},
    )

    _, _, max_context_results = mock_rag_service.ask.call_args.args
    assert max_context_results == 5


def test_ask_group_not_found(client, mock_rag_service):
    mock_rag_service.ask.side_effect = km_models.KnowledgeGroupNotFoundError

    response = client.post(
        "/knowledge/groups/missing_group/ask",
        json={"question": "What is the answer?"},
    )

    assert response.status_code == 400
    assert "missing_group" in response.json()["detail"]


def test_ask_no_active_snapshot(client, mock_rag_service):
    mock_rag_service.ask.side_effect = snapshot_models.NoActiveSnapshotError

    response = client.post(
        "/knowledge/groups/group_123/ask",
        json={"question": "What is the answer?"},
    )

    assert response.status_code == 400
    assert "group_123" in response.json()["detail"]


def test_ask_missing_question(client):
    response = client.post("/knowledge/groups/group_123/ask", json={})

    assert response.status_code == 400
