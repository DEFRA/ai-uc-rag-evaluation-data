"""Dependency injection factories for the rag module."""

import fastapi

from app import config
from app.knowledge_management import dependencies as km_dependencies
from app.knowledge_management import service as km_service
from app.rag.service import RagService
from app.snapshot import dependencies as snapshot_dependencies
from app.snapshot import service as snapshot_service


def get_rag_service(
    knowledge_service: km_service.KnowledgeManagementService = fastapi.Depends(
        km_dependencies.get_knowledge_management_service
    ),
    snp_service: snapshot_service.SnapshotService = fastapi.Depends(
        snapshot_dependencies.get_snapshot_service
    ),
) -> RagService:
    """Dependency injection for RagService."""
    return RagService(knowledge_service, snp_service, config.config)
