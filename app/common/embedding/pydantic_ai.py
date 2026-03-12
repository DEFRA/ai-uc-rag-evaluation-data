import pydantic_ai
from pydantic_ai.embeddings import bedrock as bedrock_models
from pydantic_ai.providers import bedrock as bedrock_providers

import app.common.embedding.service as embedding_service
import app.config as config


class BedrockInferenceProfileEmbeddingModel(bedrock_models.BedrockEmbeddingModel):
    """Extends BedrockEmbeddingModel to support AWS Application Inference Profile ARNs.

    AWS inference profile ARNs are opaque and don't encode the underlying model family,
    so pydantic-ai cannot determine the correct request format from the ARN alone.
    This class accepts both the ARN (used as the modelId in API calls) and the base
    model name (used only to select the correct request/response handler).
    """

    def __init__(
        self,
        inference_profile_arn: str,
        base_model_name: str,
        *,
        provider: bedrock_providers.BedrockProvider,
        settings: bedrock_models.BedrockEmbeddingSettings | None = None,
    ):
        # Initialise with the base model name so _get_handler_for_model picks the
        # correct handler (Titan / Cohere / Nova) for request formatting.
        super().__init__(base_model_name, provider=provider, settings=settings)
        # Override _model_name so every invoke_model call uses the ARN as modelId.
        self._model_name = inference_profile_arn


class PydanticAiEmbeddingService(embedding_service.AbstractEmbeddingService):
    def __init__(self, config: config.AppConfig):
        provider = bedrock_providers.BedrockProvider(
            region_name=config.aws_region,
        )

        embedding_config = config.bedrock_embedding_config
        if embedding_config.inference_profile_arn:
            model = BedrockInferenceProfileEmbeddingModel(
                embedding_config.inference_profile_arn,
                embedding_config.model_id,
                provider=provider,
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
