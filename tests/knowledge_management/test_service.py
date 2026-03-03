import datetime
from unittest.mock import AsyncMock

import pytest

from app.knowledge_management import models
from app.knowledge_management.service import KnowledgeManagementService


@pytest.fixture
def mock_group_repo():
    return AsyncMock()


@pytest.fixture
def mock_upload_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_group_repo, mock_upload_repo):
    return KnowledgeManagementService(
        group_repo=mock_group_repo,
        upload_repo=mock_upload_repo,
    )


@pytest.fixture
def group():
    return models.KnowledgeGroup(
        group_id="kg_123",
        name="Test Group",
        description="A test group",
        owner="test-owner",
        created_at=datetime.datetime.now(datetime.UTC),
        updated_at=datetime.datetime.now(datetime.UTC),
    )


@pytest.fixture
def source():
    return models.KnowledgeSource(
        name="Test Source",
        source_type=models.SourceType.BLOB,
        location="s3://bucket/file.jsonl",
    )


# --- find_knowledge_group ---


@pytest.mark.asyncio
async def test_find_knowledge_group_returns_group(
    service, group, source, mock_group_repo, mock_upload_repo
):
    group.add_source(source)
    mock_group_repo.get_by_id.return_value = group
    mock_upload_repo.get_status_by_location.return_value = "ready"

    result = await service.find_knowledge_group("kg_123")

    assert result == group
    assert result.sources[source.source_id].upload_status == "ready"
    mock_upload_repo.get_status_by_location.assert_called_once_with(source.location)


@pytest.mark.asyncio
async def test_find_knowledge_group_defaults_upload_status_to_unknown(
    service, group, source, mock_group_repo, mock_upload_repo
):
    group.add_source(source)
    mock_group_repo.get_by_id.return_value = group
    mock_upload_repo.get_status_by_location.return_value = None

    result = await service.find_knowledge_group("kg_123")

    source = list(result.sources.values())[0]
    assert source.upload_status == "Unknown"


@pytest.mark.asyncio
async def test_find_knowledge_group_raises_when_not_found(service, mock_group_repo):
    mock_group_repo.get_by_id.return_value = None

    with pytest.raises(models.KnowledgeGroupNotFoundError):
        await service.find_knowledge_group("kg_missing")


# --- add_source_to_group ---


@pytest.mark.asyncio
async def test_add_source_to_group_adds_source(
    service, group, source, mock_group_repo, mock_upload_repo
):
    mock_group_repo.get_by_id.return_value = group
    mock_upload_repo.get_status_by_location.return_value = "ready"

    result = await service.add_source_to_group("kg_123", source)

    assert source.source_id in result.sources
    assert source.upload_status == "ready"
    mock_group_repo.add_sources_to_group.assert_called_once_with("kg_123", [source])


@pytest.mark.asyncio
async def test_add_source_to_group_defaults_upload_status_to_unknown(
    service, group, source, mock_group_repo, mock_upload_repo
):
    mock_group_repo.get_by_id.return_value = group
    mock_upload_repo.get_status_by_location.return_value = None

    await service.add_source_to_group("kg_123", source)

    assert source.upload_status == "Unknown"


@pytest.mark.asyncio
async def test_add_source_to_group_raises_if_source_already_exists(
    service, group, source, mock_group_repo, mock_upload_repo
):
    group.add_source(source)
    mock_group_repo.get_by_id.return_value = group
    mock_upload_repo.get_status_by_location.return_value = None

    with pytest.raises(models.KnowledgeSourceAlreadyExistsInGroupError):
        await service.add_source_to_group("kg_123", source)


@pytest.mark.asyncio
async def test_add_source_to_group_raises_when_group_not_found(
    service, source, mock_group_repo
):
    mock_group_repo.get_by_id.return_value = None

    with pytest.raises(models.KnowledgeGroupNotFoundError):
        await service.add_source_to_group("kg_missing", source)
