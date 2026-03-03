"""Dependency injection factories for snapshot module."""

import fastapi
import pymongo.asynchronous.database

from app import config
from app.common import mongo, postgres
from app.common.embedding import pydantic_ai
from app.common.embedding import service as embedding
from app.snapshot import repository, service


def get_snapshot_repository(
    db: pymongo.asynchronous.database.AsyncDatabase = fastapi.Depends(mongo.get_db),
) -> repository.AbstractKnowledgeSnapshotRepository:
    """Dependency injection for MongoKnowledgeSnapshotRepository."""
    return repository.MongoKnowledgeSnapshotRepository(db)


def get_knowledge_vector_repository(
    session_factory=fastapi.Depends(postgres.get_async_session_factory),
) -> repository.AbstractKnowledgeVectorRepository:
    """Dependency injection for PostgresKnowledgeVectorRepository."""
    return repository.PostgresKnowledgeVectorRepository(session_factory)


def get_pydantic_embedding_service() -> embedding.AbstractEmbeddingService:
    """Dependency injection for BedrockEmbeddingService."""
    return pydantic_ai.PydanticAiEmbeddingService(config.config)


def get_snapshot_service(
    snapshot_repo: repository.AbstractKnowledgeSnapshotRepository = fastapi.Depends(
        get_snapshot_repository
    ),
    vector_repo: repository.AbstractKnowledgeVectorRepository = fastapi.Depends(
        get_knowledge_vector_repository
    ),
    embedding_service: embedding.AbstractEmbeddingService = fastapi.Depends(
        get_pydantic_embedding_service
    ),
) -> service.SnapshotService:
    """Dependency injection for SnapshotService."""
    return service.SnapshotService(snapshot_repo, vector_repo, embedding_service)
