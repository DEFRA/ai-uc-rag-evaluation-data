import pydantic_ai
from pydantic_ai.embeddings import bedrock as bedrock_models
from pydantic_ai.providers import bedrock as bedrock_providers

import app.common.embedding.service as embedding_service
import app.config as config


class PydanticAiEmbeddingService(embedding_service.AbstractEmbeddingService):
    def __init__(self, config: config.AppConfig):
        provider = bedrock_providers.BedrockProvider(
            region_name=config.aws_region,
        )

        embedding_config = config.bedrock_embedding_config
        if embedding_config.inference_profile_arn:
            model = bedrock_models.BedrockEmbeddingModel(
                embedding_config.model_id,
                provider=provider,
                settings=bedrock_models.BedrockEmbeddingSettings(
                    bedrock_inference_profile=embedding_config.inference_profile_arn
                ),
            )
        else:
            model = bedrock_models.BedrockEmbeddingModel(
                embedding_config.model_id,
                provider=provider,
            )

        self._embedder = pydantic_ai.Embedder(
            settings=bedrock_models.BedrockEmbeddingSettings(),
            model=model,
        )

    async def generate_embeddings(self, input_text: str) -> list[float]:
        embedding_result = await self._embedder.embed_documents(input_text)

        return list(embedding_result.embeddings[0])
