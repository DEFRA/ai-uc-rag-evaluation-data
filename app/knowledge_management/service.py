import logging

from app.knowledge_management import models, repository
from app.upload import repository as upload_repository

logger = logging.getLogger(__name__)


class KnowledgeManagementService:
    """Service for managing knowledge groups and their metadata"""

    def __init__(
        self,
        group_repo: repository.AbstractKnowledgeGroupRepository,
        upload_repo: upload_repository.UploadRecordRepository,
    ):
        self.group_repo = group_repo
        self.upload_repo = upload_repo

    async def create_knowledge_group(self, group: models.KnowledgeGroup) -> None:
        """
        Create a new knowledge group in the database.

        Args:
            group: The knowledge group domain model to create
        """
        logger.info("Creating knowledge group: %s", group.name)

        await self.group_repo.save(group)

        if group.sources:
            await self.group_repo.add_sources_to_group(
                group.group_id, list(group.sources.values())
            )

        logger.info("Knowledge group created successfully: %s", group.name)

    async def list_knowledge_groups(self) -> list[models.KnowledgeGroup]:
        """
        List all knowledge entries in the database.

        Returns:
            A list of knowledge entries
        """
        return await self.group_repo.list_all()

    async def find_knowledge_group(self, group_id: str) -> models.KnowledgeGroup:
        """
        Find a knowledge entry by its group ID.

        Args:
            group_id: The group ID of the knowledge entry to find

        Returns:
            The found knowledge entry

        Raises:
            KnowledgeGroupNotFoundError: If no entry is found with the given group ID
        """
        entry = await self.group_repo.get_by_id(group_id)

        if entry:
            for source in entry.sources.values():
                source.upload_status = await self.upload_repo.get_status_by_location(source.location) or "Unknown"
            return entry

        msg = f"Knowledge entry with group ID '{group_id}' not found"
        raise models.KnowledgeGroupNotFoundError(msg)

    async def set_active_snapshot(self, group_id: str, snapshot_id: str) -> None:
        """
        Set the active snapshot for a knowledge group.

        Args:
            group_id: The group ID of the knowledge entry to update
            snapshot_id: The snapshot ID to set as active
        """
        group = await self.find_knowledge_group(group_id)

        group.active_snapshot = snapshot_id

        await self.group_repo.save(group)

        logger.info(
            "Set active snapshot for group %s to %s", group_id, group.active_snapshot
        )

    async def add_source_to_group(
        self, group_id: str, source: models.KnowledgeSource
    ) -> models.KnowledgeGroup:
        """
        Add a source URL to a knowledge group.

        Args:
            group_id: The group ID of the knowledge entry to update
            source: The source to add
        """
        # Verify group exists first
        group = await self.find_knowledge_group(group_id)

        # Check if source already exists
        if source.source_id in group.sources:
            from app.knowledge_management.models import (
                KnowledgeSourceAlreadyExistsInGroupError,
            )

            error_msg = f"Source {source.source_id} already exists in group {group_id}"
            raise KnowledgeSourceAlreadyExistsInGroupError(error_msg)

        # Add source using bulk method (efficient even for single source)
        await self.group_repo.add_sources_to_group(group_id, [source])

        # Update the domain model and return updated group
        group.add_source(source)

        source.upload_status = await self.upload_repo.get_status_by_location(source.location) or "Unknown"

        return group
