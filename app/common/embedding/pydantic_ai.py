from pydantic_ai import Embedder
from pydantic_ai.embeddings.bedrock import (
    BedrockEmbeddingModel,
    BedrockEmbeddingSettings,
)
from pydantic_ai.providers.bedrock import BedrockProvider

from app.common.embedding.service import AbstractEmbeddingService
from app.config import AppConfig


class PydanticAiEmbeddingService(AbstractEmbeddingService):
    def __init__(self, config: AppConfig):
        provider = BedrockProvider(
            region_name=config.aws_region,
        )
        self._embedder = Embedder(
            settings=BedrockEmbeddingSettings(),
            model=BedrockEmbeddingModel(
                config.bedrock_embedding_config.model_id, provider=provider
            ),
        )

    async def generate_embeddings(self, input_text: str) -> list[float]:
        embedding_result = await self._embedder.embed_documents(input_text)

        return list(embedding_result.embeddings[0])
