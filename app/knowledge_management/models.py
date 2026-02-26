from datetime import date
from enum import Enum

from app.common import id_utils


class SourceType(Enum):
    """Enum representing different types of knowledge sources."""

    def __str__(self) -> str:
        return self.value

    BLOB = "BLOB"
    PRECHUNKED_BLOB = "PRECHUNKED_BLOB"


class KnowledgeSource:
    """Represents the source of a knowledge entry."""

    def __init__(
        self, name: str, source_type: SourceType, location: str, source_id: str = None
    ):
        self.source_id = source_id or id_utils.generate_random_id("ks")
        self.name = name
        self.source_type = source_type
        self.location = location

    def __eq__(self, other):
        if not isinstance(other, KnowledgeSource):
            return False

        return self.source_id == other.source_id

    def __hash__(self):
        return hash(self.source_id)


class KnowledgeGroup:
    """Represents a knowledge entry with its details and sources."""

    def __init__(
        self,
        group_id: str = None,
        name: str = None,
        description: str = None,
        owner: str = None,
        created_at: date = None,
        updated_at: date = None,
        active_snapshot: str = None,
    ):
        if not name.strip():
            msg = "KnowledgeGroup name cannot be empty or whitespace."
            raise ValueError(msg)

        if not description.strip():
            msg = "KnowledgeGroup description cannot be empty or whitespace."
            raise ValueError(msg)

        if not owner.strip():
            msg = "KnowledgeGroup owner cannot be empty or whitespace."
            raise ValueError(msg)

        self.group_id = group_id or id_utils.generate_random_id("kg")
        self.name = name
        self.description = description
        self.owner = owner
        self.created_at = created_at
        self.updated_at = updated_at
        self.active_snapshot = active_snapshot

        self._sources = {}

    def __eq__(self, other):
        if not isinstance(other, KnowledgeGroup):
            return False

        return self.group_id == other.group_id

    def __hash__(self):
        return hash(self.group_id)

    def add_source(self, source: KnowledgeSource):
        self._sources[source.source_id] = source

    @property
    def sources(self) -> dict[str, KnowledgeSource]:
        return self._sources


class KnowledgeGroupAlreadyExistsError(Exception):
    """Exception raised when a knowledge group (duplicate name) already exists."""


class KnowledgeGroupNotFoundError(Exception):
    """Exception raised when a knowledge group is not found."""


class KnowledgeSourceAlreadyExistsInGroupError(Exception):
    """Exception raised when a knowledge source already exists in a knowledge group."""
