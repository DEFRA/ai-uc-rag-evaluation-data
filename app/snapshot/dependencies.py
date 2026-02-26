"""Dependency injection factories for snapshot module."""

import fastapi
import pymongo.asynchronous.database

from app import config
from app.common import bedrock, mongo, postgres
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


def get_bedrock_embedding_service() -> bedrock.AbstractEmbeddingService:
    """Dependency injection for BedrockEmbeddingService."""
    return bedrock.BedrockEmbeddingService(
        bedrock.get_bedrock_client(), config.config.bedrock_embedding_config
    )


def get_snapshot_service(
    snapshot_repo: repository.AbstractKnowledgeSnapshotRepository = fastapi.Depends(
        get_snapshot_repository
    ),
    vector_repo: repository.AbstractKnowledgeVectorRepository = fastapi.Depends(
        get_knowledge_vector_repository
    ),
    embedding_service: bedrock.AbstractEmbeddingService = fastapi.Depends(
        get_bedrock_embedding_service
    ),
) -> service.SnapshotService:
    """Dependency injection for SnapshotService."""
    return service.SnapshotService(snapshot_repo, vector_repo, embedding_service)
