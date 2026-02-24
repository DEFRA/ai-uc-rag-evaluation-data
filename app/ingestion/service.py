import json
import logging

import fastapi

from app.common.embedding.service import AbstractEmbeddingService
from app.ingestion import models as ingestion_models
from app.ingestion import repository
from app.knowledge_management import models as km_models
from app.snapshot import service as snapshot_service

logger = logging.getLogger(__name__)

# Tracks group_ids currently being ingested to prevent duplicate concurrent runs
_ingest_in_progress: set[str] = set()


class IngestionService:
    """Service class for processing knowledge sources."""

    def __init__(
        self,
        ingestion_repository: repository.AbstractIngestionDataRepository,
        embedding_service: AbstractEmbeddingService,
        snapshot_service: snapshot_service.SnapshotService,
        background_tasks: fastapi.BackgroundTasks,
    ):
        self.ingestion_repository = ingestion_repository
        self.embedding_service = embedding_service
        self.snapshot_service = snapshot_service
        self.background_tasks = background_tasks

    async def process_group(self, group: km_models.KnowledgeGroup) -> None:
        """
        Initiate background processing for all sources in a knowledge group.
        Rejects if ingest is already in progress for this group.

        Args:
            group: The knowledge group containing sources to process

        Raises:
            IngestionAlreadyInProgressError: If ingest is already running for this group
        """
        if group.group_id in _ingest_in_progress:
            error_message = (
                f"Ingestion already in progress for group '{group.group_id}'"
            )
            raise ingestion_models.IngestionAlreadyInProgressError(error_message)
        _ingest_in_progress.add(group.group_id)

        snapshot = await self.snapshot_service.create_snapshot(
            group.group_id, group.sources.values()
        )

        self.background_tasks.add_task(
            self._process_group_background,
            group,
            snapshot.snapshot_id,
        )

    async def _process_group_background(
        self, group: km_models.KnowledgeGroup, snapshot_id: str
    ) -> None:
        """Process all sources in background; clears ingest lock when done."""
        try:
            for source in group.sources.values():
                await self._process_source(source, snapshot_id)
        finally:
            _ingest_in_progress.discard(group.group_id)

    async def _process_source(
        self, source: km_models.KnowledgeSource, snapshot_id: str
    ) -> None:
        """
        Process a single source: process data, generate embeddings, and store vector for search.

        Args:
            source: The knowledge source to process
            snapshot_id: The associated snapshot ID
        """
        logger.info("Processing source: %s for group: %s", source.name, snapshot_id)

        vectors: ingestion_models.IngestionVector = None

        match source.source_type:
            case km_models.SourceType.PRECHUNKED_BLOB:
                vectors = await self._process_prechunked_source(source, snapshot_id)
            case _:
                msg = f"Source type {source.source_type} ingestion not implemented"
                raise NotImplementedError(msg)

        if vectors:
            knowledge_vectors = [vector.to_knowledge_vector() for vector in vectors]
            await self.snapshot_service.store_vectors(knowledge_vectors)
        else:
            logger.warning("No vectors generated for source: %s", source.source_id)

        logger.info("Processing completed for source: %s", source.source_id)

    async def _process_prechunked_source(
        self, source: km_models.KnowledgeSource, snapshot_id: str
    ) -> list[ingestion_models.IngestionVector]:
        """
        Process a source that has pre-chunked data available.
        This method retrieves the chunked data, generates embeddings, and stores the vectors.
        """
        logger.info("Processing pre-chunked source: %s", source.source_id)

        chunk_files = self.ingestion_repository.list(source.source_id)

        if len(chunk_files) == 0:
            msg = f"No pre-chunked data found for source {source.source_id}"
            raise ingestion_models.NoSourceDataError(msg)

        vectors = []

        for chunk_file in chunk_files:
            file = self.ingestion_repository.get(chunk_file)

            if file is None:
                msg = f"Failed to retrieve file {chunk_file} from repository for source {source.source_id}"
                raise ingestion_models.NoSourceDataError(msg)

            file_vectors = await self._process_chunked_data(
                file, snapshot_id, source.source_id
            )

            vectors.extend(file_vectors)

        return vectors

    async def _process_chunked_data(
        self, file: bytes, snapshot_id: str, source_id: str
    ) -> list[ingestion_models.IngestionVector]:
        """
        Process pre-chunked data from a file: read content, generate embeddings, and prepare vectors.
        Returns processed vectors ready for search storage.
        """
        logger.info("Processing pre-chunked data from file")

        chunk_fields = set(ingestion_models.ChunkData.__dataclass_fields__)
        chunks = [
            ingestion_models.ChunkData(
                **{k: v for k, v in json.loads(line).items() if k in chunk_fields}
            )
            for line in file.splitlines()
        ]

        logger.info("Generating embeddings for %d chunks", len(chunks))

        vectors = []

        for chunk_no in range(len(chunks)):
            chunk = chunks[chunk_no]
            embedding = await self.embedding_service.generate_embeddings(chunk.text)
            vector = ingestion_models.IngestionVector(
                content=chunk.text,
                embedding=embedding,
                snapshot_id=snapshot_id,
                source_id=source_id,
                metadata=None,
            )

            vectors.append(vector)

            if (chunk_no + 1) % 50 == 0:
                logger.info("Generated embeddings for %d chunks", chunk_no + 1)

        return vectors
