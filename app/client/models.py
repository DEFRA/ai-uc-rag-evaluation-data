"""Request/response models for the Defra Data API client."""

from dataclasses import dataclass
from enum import Enum
from typing import Union


class SourceType(str, Enum):
    """Type of knowledge source."""

    BLOB = "BLOB"
    PRECHUNKED_BLOB = "PRECHUNKED_BLOB"


@dataclass
class KnowledgeSource:
    """A knowledge source within a group."""

    source_id: str
    name: str
    type: SourceType
    location: str


@dataclass
class KnowledgeGroup:
    """A knowledge group with its sources."""

    group_id: str
    title: str
    description: str
    owner: str
    created_at: str
    updated_at: str
    sources: dict[str, KnowledgeSource]


@dataclass
class CreateKnowledgeGroupRequest:
    """Request to create a knowledge group."""

    name: str
    description: str
    owner: str
    sources: list[Union["KnowledgeSourceInput", dict]]  # dict: {name, type, location}


@dataclass
class KnowledgeSourceInput:
    """Input for adding a knowledge source."""

    name: str
    type: SourceType
    location: str


@dataclass
class Snapshot:
    """A snapshot of a knowledge group."""

    snapshot_id: str
    group_id: str
    version: int
    created_at: str
    sources: list[dict]


@dataclass
class KnowledgeVectorResult:
    """A single result from a vector search query."""

    content: str
    similarity_score: float
    similarity_category: str
    created_at: str
    name: str
    location: str
    snapshot_id: str
    source_id: str


@dataclass
class QueryResult:
    """Container for query results."""

    results: list[KnowledgeVectorResult]
