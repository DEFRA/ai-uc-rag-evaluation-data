import dataclasses
import datetime
from enum import StrEnum

from app.knowledge_management import models as km_models


class IngestionStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclasses.dataclass
class KnowledgeVector:
    """Domain model for knowledge vectors."""

    content: str
    embedding: list[float]
    snapshot_id: str
    source_id: str
    metadata: dict | None = None


@dataclasses.dataclass
class KnowledgeVectorResult:
    """Represents a knowledge search result with similarity scoring."""

    content: str
    similarity_score: float
    created_at: datetime.datetime

    snapshot_id: str
    source_id: str
    metadata: dict | None = None

    name: str | None = None
    location: str | None = None

    @property
    def similarity_category(self) -> str:
        """Categorize similarity level."""
        if self.similarity_score >= 0.9:
            return "very_high"
        if self.similarity_score >= 0.8:
            return "high"
        if self.similarity_score >= 0.6:
            return "medium"
        return "low"


@dataclasses.dataclass
class KnowledgeSnapshot:
    """Represents a snapshot of a knowledge group at a specific point in time."""

    group_id: str
    version: int
    created_at: datetime.date
    ingestion_status: str = IngestionStatus.IN_PROGRESS
    sources: dict[str, km_models.KnowledgeSource] = dataclasses.field(
        default_factory=dict
    )

    @property
    def snapshot_id(self) -> str:
        """Generate snapshot ID from group_id and version."""
        return f"{self.group_id}_v{self.version}"

    def add_source(self, source: km_models.KnowledgeSource):
        self.sources[source.source_id] = source


class KnowledgeSnapshotNotFoundError(Exception):
    """Exception raised when a knowledge snapshot is not found."""


class NoActiveSnapshotError(Exception):
    """Exception raised when a knowledge group has no active snapshot."""
