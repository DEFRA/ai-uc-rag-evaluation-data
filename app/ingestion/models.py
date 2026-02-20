from dataclasses import dataclass

from app.snapshot import models


@dataclass
class IngestionVector:
    """Domain model for vectors during ingestion processing."""

    content: str
    embedding: list[float]
    snapshot_id: str
    source_id: str
    metadata: dict | None = None

    def to_knowledge_vector(self):
        """Convert to KnowledgeVector for the snapshot domain."""

        return models.KnowledgeVector(
            content=self.content,
            embedding=self.embedding,
            snapshot_id=self.snapshot_id,
            source_id=self.source_id,
            metadata=self.metadata,
        )


@dataclass(frozen=True)
class ChunkData:
    source: str
    text: str


class NoSourceDataError(Exception):
    """Raised when no source data is found for a given source."""


class IngestionAlreadyInProgressError(Exception):
    """Raised when ingest is already running for a knowledge group."""
