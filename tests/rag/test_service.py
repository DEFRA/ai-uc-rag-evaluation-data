import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.rag.service import RagService
from app.snapshot import models as snapshot_models


@pytest.fixture
def mock_knowledge_service():
    service = AsyncMock()
    service.find_knowledge_group.return_value = Mock()
    return service


@pytest.fixture
def mock_snp_service():
    return AsyncMock()


@pytest.fixture
def mock_config():
    config = Mock()
    config.aws_region = "eu-west-2"
    config.bedrock_llm_config.model_id = "eu.anthropic.claude-3-5-sonnet-20241022-v2:0"
    config.bedrock_llm_config.inference_profile_arn = None
    return config


@pytest.fixture
def service(mock_knowledge_service, mock_snp_service, mock_config):
    with (
        patch("app.rag.service.bedrock_providers.BedrockProvider"),
        patch("app.rag.service.pydantic_ai.Agent") as mock_agent_cls,
    ):
        svc = RagService(mock_knowledge_service, mock_snp_service, mock_config)
        svc._agent = mock_agent_cls.return_value
        yield svc


def _make_document(content="Relevant content.", source_id="src_001", score=0.9):
    return snapshot_models.KnowledgeVectorResult(
        content=content,
        similarity_score=score,
        created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
        snapshot_id="snap_001",
        source_id=source_id,
        name="doc.pdf",
        location="s3://bucket/doc.pdf",
    )


@pytest.mark.asyncio
async def test_ask_returns_answer_and_sources(service, mock_snp_service):
    document = _make_document()
    mock_snp_service.search_similar.return_value = [document]
    service._agent.run = AsyncMock(return_value=Mock(output="The answer."))

    result = await service.ask(
        "group_123", "What is the answer?", max_context_results=3
    )

    assert result.answer == "The answer."
    assert len(result.sources) == 1
    assert result.sources[0].content == document.content
    assert result.sources[0].similarity_score == document.similarity_score
    assert result.sources[0].source_id == document.source_id


@pytest.mark.asyncio
async def test_ask_fetches_group_and_searches(
    service, mock_knowledge_service, mock_snp_service
):
    mock_group = mock_knowledge_service.find_knowledge_group.return_value
    mock_snp_service.search_similar.return_value = [_make_document()]
    service._agent.run = AsyncMock(return_value=Mock(output="Answer."))

    await service.ask("group_123", "What is the answer?", max_context_results=5)

    mock_knowledge_service.find_knowledge_group.assert_called_once_with("group_123")
    mock_snp_service.search_similar.assert_called_once_with(
        mock_group, "What is the answer?", 5
    )


@pytest.mark.asyncio
async def test_ask_builds_context_prompt_from_documents(service, mock_snp_service):
    mock_snp_service.search_similar.return_value = [
        _make_document("First chunk.", source_id="src_001"),
        _make_document("Second chunk.", source_id="src_002"),
    ]
    mock_run = AsyncMock(return_value=Mock(output="Answer."))
    service._agent.run = mock_run

    await service.ask("group_123", "What is it?", max_context_results=2)

    prompt = mock_run.call_args.args[0]
    assert "[Source 1]:\nFirst chunk." in prompt
    assert "[Source 2]:\nSecond chunk." in prompt
    assert "Question: What is it?" in prompt


@pytest.mark.asyncio
async def test_ask_with_no_documents_still_calls_llm(service, mock_snp_service):
    mock_snp_service.search_similar.return_value = []
    service._agent.run = AsyncMock(return_value=Mock(output="I don't know."))

    result = await service.ask("group_123", "Unknown question?", max_context_results=5)

    assert result.answer == "I don't know."
    assert result.sources == []
    service._agent.run.assert_called_once()
