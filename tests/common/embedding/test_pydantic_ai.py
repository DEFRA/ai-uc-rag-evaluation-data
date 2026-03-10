from unittest.mock import AsyncMock, Mock

import pytest

from app import config as config
from app.common.embedding import pydantic_ai


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    app_config = Mock(spec=config.AppConfig)
    app_config.aws_region = "us-east-1"
    app_config.bedrock_embedding_config = Mock(spec=config.BedrockEmbeddingConfig)
    app_config.bedrock_embedding_config.model_id = "amazon.titan-embed-text-v2:0"
    app_config.bedrock_embedding_config.inference_profile_arn = None
    return app_config


@pytest.fixture
def mock_embedding_result():
    """Create a mock embedding result."""
    result = Mock()
    result.embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5]]
    return result


@pytest.mark.asyncio
async def test_generate_embeddings_success(mock_config, mock_embedding_result):
    """Test successful embedding generation."""

    # Mock the embedder directly on the instance
    service = pydantic_ai.PydanticAiEmbeddingService(mock_config)
    service._embedder = AsyncMock()
    service._embedder.embed_documents.return_value = mock_embedding_result

    # Test embedding generation
    input_text = "test text"
    result = await service.generate_embeddings(input_text)

    # Assertions
    assert result == mock_embedding_result.embeddings[0]
    service._embedder.embed_documents.assert_called_once_with(input_text)
