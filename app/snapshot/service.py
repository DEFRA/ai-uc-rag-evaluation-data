import datetime
import logging

from app.common import bedrock
from app.knowledge_management import models as km_models
from app.snapshot import models, repository

logger = logging.getLogger(__name__)


class SnapshotService:
    """Service for managing knowledge vector snapshots and search operations."""

    def __init__(
        self,
        snapshot_repo: repository.MongoKnowledgeSnapshotRepository,
        vector_repo: repository.AbstractKnowledgeVectorRepository,
        embedding_service: bedrock.AbstractEmbeddingService,
    ):
        self._snapshot_repo = snapshot_repo
        self._vector_repo = vector_repo
        self._embedding_service = embedding_service

    async def create_snapshot(
        self, group_id: str, sources: list[dict]
    ) -> models.KnowledgeSnapshot:
        """
        Create a new knowledge snapshot for a group.

        Args:
            group_id: The ID of the knowledge group
            sources: A list of source metadata dictionaries to include in the snapshot

        Returns:
            The created KnowledgeSnapshot domain object
        """

        previous_snapshots = await self._snapshot_repo.list_snapshots_by_group(group_id)

        new_version = len(previous_snapshots) + 1

        snapshot = models.KnowledgeSnapshot(
            group_id=group_id,
            version=new_version,
            created_at=datetime.datetime.now(tz=datetime.UTC),
        )

        for source in sources:
            snapshot.add_source(source)

        await self._snapshot_repo.save(snapshot)

        return snapshot

    async def get_latest_by_group(self, group_id: str):
        """
        Get the latest knowledge snapshot for a group.

        Args:
            group_id: The ID of the knowledge group

        Returns:
            The latest KnowledgeSnapshot object or None if no snapshots exist
        """

        return await self._snapshot_repo.get_latest_by_group(group_id)

    async def get_by_id(self, snapshot_id: str):
        """
        Retrieve knowledge snapshot metadata by its ID.

        Args:
            snapshot_id: The ID of the knowledge snapshot to retrieve

        Returns:
            The found KnowledgeSnapshot object

        Raises:
            KnowledgeSnapshotNotFoundError: If a snapshot with the given ID does not exist
        """

        snapshot = await self._snapshot_repo.get_by_id(snapshot_id)

        if not snapshot:
            msg = f"Snapshot '{snapshot_id}' not found"
            raise models.KnowledgeSnapshotNotFoundError(msg)

        return snapshot

    async def store_vectors(self, vectors: list[models.KnowledgeVector]) -> None:
        """
        Store a batch of knowledge vectors in the repository.

        Args:
            vectors: A list of KnowledgeVector objects to store
        """

        logger.info("Storing %d vectors for search operations", len(vectors))

        await self._vector_repo.add_batch(vectors)

        logger.info("Successfully stored vectors for search")

    async def search_similar(
        self, group: km_models.KnowledgeGroup, query: str, max_results: int
    ) -> list[models.KnowledgeVectorResult]:
        """
        Search for documents similar to the provided query within a specific snapshot.

        Args:
            snapshot_id: The ID of the knowledge snapshot to base the search on
            query: The search query string
            top_k: The maximum number of results to return

        Returns:
            A list of KnowledgeVectorResult objects representing the most relevant documents

        Raises:
            KnowledgeSnapshotNotFoundError: If the snapshot with the given ID does not exist
            NoActiveSnapshotError: If the knowledge group has no active snapshot
        """

        if not group.active_snapshot:
            msg = f"Knowledge group with ID '{group.group_id}' has no active snapshot"
            raise models.NoActiveSnapshotError(msg)

        snapshot = await self.get_by_id(group.active_snapshot)

        embedding = self._embedding_service.generate_embeddings(query)

        documents = await self._vector_repo.query_by_snapshot(
            embedding, group.active_snapshot, max_results
        )

        for doc in documents:
            source = snapshot.sources[doc.source_id]

            if not source:
                continue

            doc.name = source.name
            doc.location = source.location

        return documents
