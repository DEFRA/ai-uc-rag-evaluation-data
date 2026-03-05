"""Dependency injection factories for knowledge management module."""

import fastapi
import pymongo.asynchronous.database

from app import config
from app.common import mongo, postgres, s3
from app.common.embedding import pydantic_ai
from app.common.embedding import service as embedding
from app.ingestion import repository as ingestion_repository
from app.ingestion import service as ingestion_service
from app.knowledge_management import repository as km_repository
from app.knowledge_management import service as km_service
from app.snapshot import repository as snapshot_repository
from app.snapshot import service as snapshot_service
from app.upload import dependencies as upload_dependencies
from app.upload import repository as upload_repository


def get_knowledge_repository(
    db: pymongo.asynchronous.database.AsyncDatabase = fastapi.Depends(mongo.get_db),
) -> km_repository.AbstractKnowledgeGroupRepository:
    """Dependency injection for MongoKnowledgeGroupRepository."""
    return km_repository.MongoKnowledgeGroupRepository(db)


def get_ingestion_data_repository() -> (
    ingestion_repository.AbstractIngestionDataRepository
):
    return ingestion_repository.S3IngestionDataRepository(
        s3_client=s3.get_s3_client(), bucket_name=config.config.ingestion_data_bucket
    )


def get_snapshot_repository_for_ingestion(
    db: pymongo.asynchronous.database.AsyncDatabase = fastapi.Depends(mongo.get_db),
) -> snapshot_repository.AbstractKnowledgeSnapshotRepository:
    """Dependency injection for MongoKnowledgeSnapshotRepository used by ingestion service."""
    return snapshot_repository.MongoKnowledgeSnapshotRepository(db)


def get_knowledge_vector_repository_for_ingestion(
    session_factory=fastapi.Depends(postgres.get_async_session_factory),
) -> snapshot_repository.AbstractKnowledgeVectorRepository:
    """Dependency injection for PostgresKnowledgeVectorRepository used by ingestion service."""
    return snapshot_repository.PostgresKnowledgeVectorRepository(session_factory)


def get_pydantic_embedding_service() -> embedding.AbstractEmbeddingService:
    """Dependency injection for BedrockEmbeddingService."""
    return pydantic_ai.PydanticAiEmbeddingService(config.config)


def get_snapshot_service_for_ingestion(
    snapshot_repo: snapshot_repository.AbstractKnowledgeSnapshotRepository = fastapi.Depends(
        get_snapshot_repository_for_ingestion
    ),
    vector_repo: snapshot_repository.AbstractKnowledgeVectorRepository = fastapi.Depends(
        get_knowledge_vector_repository_for_ingestion
    ),
    embedding_service: embedding.AbstractEmbeddingService = fastapi.Depends(
        get_pydantic_embedding_service
    ),
) -> snapshot_service.SnapshotService:
    """Dependency injection for SnapshotService used by ingestion service."""
    return snapshot_service.SnapshotService(
        snapshot_repo, vector_repo, embedding_service
    )


def get_knowledge_management_service(
    group_repo: km_repository.AbstractKnowledgeGroupRepository = fastapi.Depends(
        get_knowledge_repository
    ),
    upload_repo: upload_repository.UploadRecordRepository = fastapi.Depends(
        upload_dependencies.get_upload_record_repository
    ),
) -> km_service.KnowledgeManagementService:
    """Dependency injection for KnowledgeManagementService."""
    return km_service.KnowledgeManagementService(group_repo, upload_repo)


def get_ingestion_service(
    ingestion_repository: ingestion_repository.AbstractIngestionDataRepository = fastapi.Depends(
        get_ingestion_data_repository
    ),
    embedding_service: embedding.AbstractEmbeddingService = fastapi.Depends(
        get_pydantic_embedding_service
    ),
    snapshot_service: snapshot_service.SnapshotService = fastapi.Depends(
        get_snapshot_service_for_ingestion
    ),
    background_tasks: fastapi.BackgroundTasks = None,
) -> ingestion_service.IngestionService:
    """Dependency injection for IngestionService."""
    return ingestion_service.IngestionService(
        ingestion_repository, embedding_service, snapshot_service, background_tasks
    )
