import datetime
from unittest.mock import AsyncMock

import pytest

from app.knowledge_management import models as km_models
from app.snapshot import models
from app.snapshot.service import SnapshotService


@pytest.fixture
def mock_snapshot_repo():
    return AsyncMock()


@pytest.fixture
def mock_vector_repo():
    return AsyncMock()


@pytest.fixture
def mock_embedding_service():
    return AsyncMock()


@pytest.fixture
def service(mock_snapshot_repo, mock_vector_repo, mock_embedding_service):
    return SnapshotService(
        snapshot_repo=mock_snapshot_repo,
        vector_repo=mock_vector_repo,
        embedding_service=mock_embedding_service,
    )


@pytest.fixture
def source():
    return km_models.KnowledgeSource(
        source_id="ks_abc",
        name="My Source",
        source_type=km_models.SourceType.BLOB,
        location="s3://bucket/file.jsonl",
    )


@pytest.fixture
def snapshot(source):
    snap = models.KnowledgeSnapshot(
        group_id="kg_123",
        version=1,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    snap.add_source(source)
    return snap


CREATED_AT = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)


@pytest.fixture
def vector_result():
    return models.KnowledgeVectorResult(
        content="Some content",
        similarity_score=0.95,
        created_at=CREATED_AT,
        snapshot_id="kg_123_v1",
        source_id="ks_abc",
        metadata={"page": 1},
    )


# --- search_similar ---


@pytest.mark.asyncio
async def test_search_similar_with_snapshot_id(
    service,
    snapshot,
    vector_result,
    mock_snapshot_repo,
    mock_vector_repo,
    mock_embedding_service,
):
    group = km_models.KnowledgeGroup(
        group_id="kg_123",
        name="Test Group",
        description="A test group",
        owner="test-owner",
    )
    mock_snapshot_repo.get_by_id.return_value = snapshot
    mock_embedding_service.generate_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_vector_repo.query_by_snapshot.return_value = [vector_result]

    results = await service.search_similar(
        group, "test query", max_results=5, snapshot_id="kg_123_v1"
    )

    mock_snapshot_repo.get_by_id.assert_called_once_with("kg_123_v1")
    assert len(results) == 1
    assert results[0].content == "Some content"
    assert results[0].similarity_score == 0.95
    assert results[0].created_at == CREATED_AT
    assert results[0].snapshot_id == "kg_123_v1"
    assert results[0].source_id == "ks_abc"
    assert results[0].metadata == {"page": 1}
    assert results[0].name == "My Source"
    assert results[0].location == "s3://bucket/file.jsonl"


@pytest.mark.asyncio
async def test_search_similar_without_snapshot_id_uses_active_snapshot(
    service,
    snapshot,
    vector_result,
    mock_snapshot_repo,
    mock_vector_repo,
    mock_embedding_service,
):
    group = km_models.KnowledgeGroup(
        group_id="kg_123",
        name="Test Group",
        description="A test group",
        owner="test-owner",
        active_snapshot="kg_123_v1",
    )
    mock_snapshot_repo.get_by_id.return_value = snapshot
    mock_embedding_service.generate_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_vector_repo.query_by_snapshot.return_value = [vector_result]

    results = await service.search_similar(group, "test query", max_results=5)

    mock_snapshot_repo.get_by_id.assert_called_once_with("kg_123_v1")
    assert len(results) == 1
    assert results[0].content == "Some content"
    assert results[0].similarity_score == 0.95
    assert results[0].created_at == CREATED_AT
    assert results[0].snapshot_id == "kg_123_v1"
    assert results[0].source_id == "ks_abc"
    assert results[0].metadata == {"page": 1}
    assert results[0].name == "My Source"
    assert results[0].location == "s3://bucket/file.jsonl"


@pytest.mark.asyncio
async def test_search_similar_raises_when_no_snapshot_id_and_no_active_snapshot(
    service,
):
    group = km_models.KnowledgeGroup(
        group_id="kg_123",
        name="Test Group",
        description="A test group",
        owner="test-owner",
    )

    with pytest.raises(models.NoActiveSnapshotError):
        await service.search_similar(group, "test query", max_results=5)


@pytest.mark.asyncio
async def test_search_similar_continues_when_source_id_not_in_snapshot(
    service, snapshot, mock_snapshot_repo, mock_vector_repo, mock_embedding_service
):
    group = km_models.KnowledgeGroup(
        group_id="kg_123",
        name="Test Group",
        description="A test group",
        owner="test-owner",
        active_snapshot="kg_123_v1",
    )
    result_with_unknown_source = models.KnowledgeVectorResult(
        content="Some content",
        similarity_score=0.8,
        created_at=datetime.datetime.now(datetime.UTC),
        snapshot_id="kg_123_v1",
        source_id="ks_unknown",
    )
    mock_snapshot_repo.get_by_id.return_value = snapshot
    mock_embedding_service.generate_embeddings.return_value = [0.1, 0.2, 0.3]
    mock_vector_repo.query_by_snapshot.return_value = [result_with_unknown_source]

    results = await service.search_similar(group, "test query", max_results=5)

    assert len(results) == 1
    assert results[0].name is None
    assert results[0].location is None
