import logging

import pydantic_ai
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.providers import bedrock as bedrock_providers

from app import config as app_config
from app.knowledge_management import service as km_service
from app.rag.api_schemas import AskResponse, SourceReference
from app.snapshot import service as snapshot_service

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a helpful assistant. Answer the user's question using only
the context documents provided. Cite specific details from the context where possible.
If the context does not contain enough information to answer the question, say so clearly
and do not make up information."""


class RagService:
    """Retrieval-augmented generation service."""

    def __init__(
        self,
        knowledge_service: km_service.KnowledgeManagementService,
        snp_service: snapshot_service.SnapshotService,
        config: app_config.AppConfig,
    ):
        self._knowledge_service = knowledge_service
        self._snp_service = snp_service

        provider = bedrock_providers.BedrockProvider(region_name=config.aws_region)

        model = f"bedrock:{config.bedrock_llm_config.model_id}"
        if config.bedrock_llm_config.inference_profile_arn:
            profile = provider.model_profile(config.bedrock_llm_config.model_id)
            model = BedrockConverseModel(
                config.bedrock_llm_config.inference_profile_arn,
                provider=provider,
                profile=profile,
            )
        self._agent = pydantic_ai.Agent(model=model, system_prompt=_SYSTEM_PROMPT)

    async def ask(
        self, group_id: str, question: str, max_context_results: int
    ) -> AskResponse:
        """
        Answer a question using retrieved context from the knowledge group.

        Args:
            group_id: The ID of the knowledge group to search
            question: The question to answer
            max_context_results: Maximum number of context documents to retrieve

        Returns:
            An AskResponse containing the generated answer and source references

        Raises:
            km_models.KnowledgeGroupNotFoundError: If the group does not exist
            snapshot_models.NoActiveSnapshotError: If the group has no active snapshot
        """
        group = await self._knowledge_service.find_knowledge_group(group_id)

        documents = await self._snp_service.search_similar(
            group, question, max_context_results
        )

        context = "\n\n".join(
            f"[Source {i + 1}]:\n{doc.content}" for i, doc in enumerate(documents)
        )
        prompt = f"Context:\n{context}\n\nQuestion: {question}"

        result = await self._agent.run(prompt)

        return AskResponse(
            answer=result.output,
            sources=[
                SourceReference(
                    content=doc.content,
                    similarity_score=doc.similarity_score,
                    name=doc.name,
                    location=doc.location,
                    source_id=doc.source_id,
                )
                for doc in documents
            ],
        )
