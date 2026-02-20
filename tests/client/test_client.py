"""Tests for the Defra Data API client library."""

import httpx
import pytest

from app.client import (
    AsyncDefraDataClient,
    CreateKnowledgeGroupRequest,
    DefraDataClient,
    KnowledgeSourceInput,
    SourceType,
)


def _make_handler(responses: dict[str, httpx.Response]):
    """Build a transport handler that returns responses by method+path key."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        if key not in responses:
            return httpx.Response(404, text=f"Unexpected: {key}")
        return responses[key]

    return handler


# --- Fixtures ---

GROUP_RESPONSE_CAMEL = {
    "groupId": "kg-123",
    "title": "Test Group",
    "description": "A test",
    "owner": "owner",
    "createdAt": "2025-01-01T00:00:00",
    "updatedAt": "2025-01-01T00:00:00",
    "sources": {
        "ks-1": {
            "sourceId": "ks-1",
            "name": "doc",
            "type": "BLOB",
            "location": "s3://bucket/file.pdf",
        }
    },
}

GROUP_RESPONSE_SNAKE = {
    "group_id": "kg-456",
    "title": "Snake Group",
    "description": "Snake case",
    "owner": "owner",
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00",
    "sources": {
        "ks-2": {
            "source_id": "ks-2",
            "name": "doc2",
            "type": "PRECHUNKED_BLOB",
            "location": "s3://bucket/file2.json",
        }
    },
}

SNAPSHOT_RESPONSE = {
    "snapshotId": "snap-1",
    "groupId": "kg-123",
    "version": 1,
    "createdAt": "2025-01-01T00:00:00",
    "sources": [{"source_id": "ks-1"}],
}

VECTOR_RESULT = {
    "content": "Some content",
    "similarityScore": 0.95,
    "similarityCategory": "very_high",
    "createdAt": "2025-01-01T00:00:00",
    "name": "doc",
    "location": "s3://bucket/file.pdf",
    "snapshotId": "snap-1",
    "sourceId": "ks-1",
}


def client_with_transport(handler):
    transport = httpx.MockTransport(handler)
    return DefraDataClient(base_url="http://test", transport=transport)


def async_client_with_transport(handler):
    transport = httpx.MockTransport(handler)
    return AsyncDefraDataClient(base_url="http://test", transport=transport)


# --- Sync client tests ---


def test_list_groups_empty():
    handler = _make_handler(
        {
            "GET /knowledge/groups": httpx.Response(204),
        }
    )
    with client_with_transport(handler) as client:
        assert client.list_groups() == []


def test_list_groups():
    handler = _make_handler(
        {
            "GET /knowledge/groups": httpx.Response(200, json=[GROUP_RESPONSE_CAMEL]),
        }
    )
    with client_with_transport(handler) as client:
        groups = client.list_groups()
        assert len(groups) == 1
        assert groups[0].group_id == "kg-123"
        assert groups[0].title == "Test Group"
        assert groups[0].sources["ks-1"].source_id == "ks-1"
        assert groups[0].sources["ks-1"].type == SourceType.BLOB


def test_get_group():
    handler = _make_handler(
        {
            "GET /knowledge/groups/kg-123": httpx.Response(
                200, json=GROUP_RESPONSE_CAMEL
            ),
        }
    )
    with client_with_transport(handler) as client:
        group = client.get_group("kg-123")
        assert group.group_id == "kg-123"
        assert group.title == "Test Group"


def test_get_group_parses_snake_case():
    handler = _make_handler(
        {
            "GET /knowledge/groups/kg-456": httpx.Response(
                200, json=GROUP_RESPONSE_SNAKE
            ),
        }
    )
    with client_with_transport(handler) as client:
        group = client.get_group("kg-456")
        assert group.group_id == "kg-456"
        assert group.sources["ks-2"].type == SourceType.PRECHUNKED_BLOB


def test_create_group_with_sources():
    handler = _make_handler(
        {
            "POST /knowledge/groups": httpx.Response(201, json=GROUP_RESPONSE_CAMEL),
        }
    )
    with client_with_transport(handler) as client:
        req = CreateKnowledgeGroupRequest(
            name="New",
            description="Desc",
            owner="me",
            sources=[
                KnowledgeSourceInput(
                    name="doc", type=SourceType.BLOB, location="s3://bucket/file.pdf"
                )
            ],
        )
        group = client.create_group(req)
        assert group.group_id == "kg-123"


def test_create_group_with_dict_sources():
    handler = _make_handler(
        {
            "POST /knowledge/groups": httpx.Response(201, json=GROUP_RESPONSE_CAMEL),
        }
    )
    with client_with_transport(handler) as client:
        req = CreateKnowledgeGroupRequest(
            name="New",
            description="Desc",
            owner="me",
            sources=[
                {"name": "doc", "type": "BLOB", "location": "s3://bucket/file.pdf"}
            ],
        )
        group = client.create_group(req)
        assert group.group_id == "kg-123"


def test_add_source():
    handler = _make_handler(
        {
            "PATCH /knowledge/groups/kg-123/sources": httpx.Response(
                200, json=GROUP_RESPONSE_CAMEL
            ),
        }
    )
    with client_with_transport(handler) as client:
        group = client.add_source(
            "kg-123",
            KnowledgeSourceInput(name="doc", type=SourceType.BLOB, location="s3://x"),
        )
        assert group.group_id == "kg-123"


def test_ingest_group():
    handler = _make_handler(
        {
            "POST /knowledge/groups/kg-123/ingest": httpx.Response(
                202,
                json={"message": "Ingestion initiated"},
            ),
        }
    )
    with client_with_transport(handler) as client:
        result = client.ingest_group("kg-123")
        assert result["message"] == "Ingestion initiated"


def test_list_group_snapshots():
    handler = _make_handler(
        {
            "GET /knowledge/groups/kg-123/snapshots": httpx.Response(
                200, json=[SNAPSHOT_RESPONSE]
            ),
        }
    )
    with client_with_transport(handler) as client:
        snapshots = client.list_group_snapshots("kg-123")
        assert len(snapshots) == 1
        assert snapshots[0].snapshot_id == "snap-1"
        assert snapshots[0].group_id == "kg-123"
        assert snapshots[0].version == 1


def test_get_snapshot():
    handler = _make_handler(
        {
            "GET /snapshots/snap-1": httpx.Response(200, json=SNAPSHOT_RESPONSE),
        }
    )
    with client_with_transport(handler) as client:
        snap = client.get_snapshot("snap-1")
        assert snap.snapshot_id == "snap-1"


def test_activate_snapshot():
    handler = _make_handler(
        {
            "PATCH /snapshots/snap-1/activate": httpx.Response(
                200,
                json={"message": "Snapshot activated"},
            ),
        }
    )
    with client_with_transport(handler) as client:
        result = client.activate_snapshot("snap-1")
        assert "activated" in result["message"]


def test_query():
    handler = _make_handler(
        {
            "POST /snapshots/query": httpx.Response(200, json=[VECTOR_RESULT]),
        }
    )
    with client_with_transport(handler) as client:
        result = client.query("kg-123", "search term", max_results=10)
        assert len(result.results) == 1
        assert result.results[0].content == "Some content"
        assert result.results[0].similarity_score == 0.95
        assert result.results[0].similarity_category == "very_high"


def test_query_default_max_results():
    handler = _make_handler(
        {
            "POST /snapshots/query": httpx.Response(200, json=[]),
        }
    )
    with client_with_transport(handler) as client:
        result = client.query("kg-123", "search")
        assert result.results == []


def test_query_parses_snake_case_vector_result():
    """Vector results can use snake_case from API."""
    snake_result = {
        "content": "content",
        "similarity_score": 0.8,
        "similarity_category": "high",
        "created_at": "2025-01-01T00:00:00",
        "name": "doc",
        "location": "s3://x",
        "snapshot_id": "snap-1",
        "source_id": "ks-1",
    }
    handler = _make_handler(
        {
            "POST /snapshots/query": httpx.Response(200, json=[snake_result]),
        }
    )
    with client_with_transport(handler) as client:
        result = client.query("kg-123", "q")
        assert result.results[0].similarity_score == 0.8
        assert result.results[0].similarity_category == "high"


def test_http_error_raises():
    handler = _make_handler(
        {
            "GET /knowledge/groups/missing": httpx.Response(
                404,
                json={"detail": "Not found"},
            ),
        }
    )
    with client_with_transport(handler) as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.get_group("missing")
        assert exc_info.value.response.status_code == 404


def test_http_error_no_json_detail():
    handler = _make_handler(
        {
            "GET /knowledge/groups/x": httpx.Response(500, text="Internal error"),
        }
    )
    with client_with_transport(handler) as client:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.get_group("x")
        assert "Internal error" in str(exc_info.value)


# --- Async client tests ---


@pytest.mark.asyncio
async def test_async_list_groups_empty():
    handler = _make_handler(
        {
            "GET /knowledge/groups": httpx.Response(204),
        }
    )
    async with async_client_with_transport(handler) as client:
        groups = await client.list_groups()
        assert groups == []


@pytest.mark.asyncio
async def test_async_list_groups():
    handler = _make_handler(
        {
            "GET /knowledge/groups": httpx.Response(200, json=[GROUP_RESPONSE_CAMEL]),
        }
    )
    async with async_client_with_transport(handler) as client:
        groups = await client.list_groups()
        assert len(groups) == 1
        assert groups[0].group_id == "kg-123"


@pytest.mark.asyncio
async def test_async_create_group():
    handler = _make_handler(
        {
            "POST /knowledge/groups": httpx.Response(201, json=GROUP_RESPONSE_CAMEL),
        }
    )
    async with async_client_with_transport(handler) as client:
        req = CreateKnowledgeGroupRequest(
            name="New",
            description="Desc",
            owner="me",
            sources=[
                KnowledgeSourceInput(
                    name="doc", type=SourceType.BLOB, location="s3://x"
                )
            ],
        )
        group = await client.create_group(req)
        assert group.group_id == "kg-123"


@pytest.mark.asyncio
async def test_async_query():
    handler = _make_handler(
        {
            "POST /snapshots/query": httpx.Response(200, json=[VECTOR_RESULT]),
        }
    )
    async with async_client_with_transport(handler) as client:
        result = await client.query("kg-123", "search", max_results=5)
        assert len(result.results) == 1
        assert result.results[0].content == "Some content"


@pytest.mark.asyncio
async def test_async_http_error():
    handler = _make_handler(
        {
            "GET /knowledge/groups/x": httpx.Response(
                404, json={"detail": "Not found"}
            ),
        }
    )
    async with async_client_with_transport(handler) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_group("x")


# --- Context manager ---


def test_sync_context_manager():
    handler = _make_handler({"GET /knowledge/groups": httpx.Response(204)})
    with client_with_transport(handler) as client:
        client.list_groups()
    # client closed without error


@pytest.mark.asyncio
async def test_async_context_manager():
    handler = _make_handler({"GET /knowledge/groups": httpx.Response(204)})
    async with async_client_with_transport(handler) as client:
        await client.list_groups()
    # client closed without error
