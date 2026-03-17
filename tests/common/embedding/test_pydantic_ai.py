import json
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from botocore.stub import Stubber

from app import config as config
from app.common.embedding import pydantic_ai

_INFERENCE_PROFILE_ARN = "arn:aws:bedrock:test_string"


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


@pytest.mark.asyncio
async def test_generate_embeddings_with_inference_profile(mock_config):
    """When inference_profile_arn is set, invoke_model is called with the ARN as modelId."""
    mock_config.bedrock_embedding_config.inference_profile_arn = _INFERENCE_PROFILE_ARN

    service = pydantic_ai.PydanticAiEmbeddingService(mock_config)

    expected_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    response_body = json.dumps({"embedding": expected_embedding}).encode()

    with Stubber(service._embedder.model.client) as stubber:
        input_text = "test text"
        stubber.add_response(
            "invoke_model",
            service_response={
                "body": BytesIO(response_body),
                "contentType": "application/json",
            },
            expected_params={
                "modelId": _INFERENCE_PROFILE_ARN,
                "body": json.dumps({"inputText": input_text, "normalize": True}),
                "contentType": "application/json",
                "accept": "application/json",
            },
        )

        result = await service.generate_embeddings(input_text)

    assert result == expected_embedding
