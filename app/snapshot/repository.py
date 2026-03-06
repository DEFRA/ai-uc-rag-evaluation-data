import abc

import bson.datetime_ms
import pymongo.asynchronous.database
import sqlalchemy

from app.knowledge_management import models as km_models
from app.snapshot import models


class AbstractKnowledgeSnapshotRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, snapshot) -> None:
        """Save a knowledge snapshot"""

    @abc.abstractmethod
    async def get_by_id(self, snapshot_id: str):
        """Get a knowledge snapshot by its ID"""

    @abc.abstractmethod
    async def list_snapshots_by_group(
        self, group_id: str
    ) -> list[models.KnowledgeSnapshot]:
        """List all knowledge snapshots for a specific group"""

    @abc.abstractmethod
    async def get_latest_by_group(self, group_id: str):
        """Get the latest knowledge snapshot for a specific group"""

    @abc.abstractmethod
    async def update_ingestion_status(self, snapshot_id: str, status: str) -> None:
        """Update the ingestion status of a snapshot"""


class MongoKnowledgeSnapshotRepository(AbstractKnowledgeSnapshotRepository):
    def __init__(self, db: pymongo.asynchronous.database.AsyncDatabase):
        self.db: pymongo.asynchronous.database.AsyncDatabase = db
        self.knowledge_snapshots: pymongo.asynchronous.database.AsyncCollection = (
            self.db.get_collection("knowledgeSnapshots")
        )

    async def save(self, snapshot: models.KnowledgeSnapshot) -> None:
        """Save a knowledge snapshot"""

        snapshot_data = {
            "snapshotId": snapshot.snapshot_id,
            "groupId": snapshot.group_id,
            "version": snapshot.version,
            "createdAt": bson.datetime_ms.DatetimeMS(snapshot.created_at),
            "ingestionStatus": snapshot.ingestion_status,
            "sources": [
                {
                    "sourceId": source.source_id,
                    "name": source.name,
                    "location": source.location,
                    "sourceType": str(source.source_type),
                }
                for source in snapshot.sources.values()
            ],
        }

        await self.knowledge_snapshots.insert_one(snapshot_data)

    async def get_by_id(self, snapshot_id: str) -> models.KnowledgeSnapshot | None:
        """Get a knowledge snapshot by its ID"""
        doc = await self.knowledge_snapshots.find_one({"snapshotId": snapshot_id})

        if not doc:
            return None

        snapshot = models.KnowledgeSnapshot(
            group_id=doc["groupId"],
            version=doc["version"],
            created_at=doc["createdAt"],
            ingestion_status=doc.get(
                "ingestionStatus", models.IngestionStatus.IN_PROGRESS
            ),
        )

        for source_doc in doc["sources"]:
            snapshot.add_source(
                km_models.KnowledgeSource(
                    source_id=source_doc["sourceId"],
                    name=source_doc["name"],
                    location=source_doc["location"],
                    source_type=km_models.SourceType(source_doc["sourceType"]),
                )
            )

        return snapshot

    async def update_ingestion_status(self, snapshot_id: str, status: str) -> None:
        """Update the ingestion status of a snapshot"""
        await self.knowledge_snapshots.update_one(
            {"snapshotId": snapshot_id}, {"$set": {"ingestionStatus": status}}
        )

    async def list_snapshots_by_group(
        self, group_id: str
    ) -> list[models.KnowledgeSnapshot]:
        """List all knowledge snapshots for a specific group"""
        cursor = self.knowledge_snapshots.find({"groupId": group_id})
        snapshots = []

        async for doc in cursor:
            snapshot = models.KnowledgeSnapshot(
                group_id=doc["groupId"],
                version=doc["version"],
                created_at=doc["createdAt"],
                ingestion_status=doc.get(
                    "ingestionStatus", models.IngestionStatus.IN_PROGRESS
                ),
            )
            for source_doc in doc["sources"]:
                snapshot.add_source(
                    km_models.KnowledgeSource(
                        source_id=source_doc["sourceId"],
                        name=source_doc["name"],
                        location=source_doc["location"],
                        source_type=km_models.SourceType(source_doc["sourceType"]),
                    )
                )
            snapshots.append(snapshot)

        return snapshots

    async def get_latest_by_group(
        self, group_id: str
    ) -> models.KnowledgeSnapshot | None:
        """Get the latest knowledge snapshot for a specific group"""
        doc = await self.knowledge_snapshots.find_one(
            {"groupId": group_id}, sort=[("version", -1)]
        )

        if not doc:
            return None

        snapshot = models.KnowledgeSnapshot(
            group_id=doc["groupId"], version=doc["version"], created_at=doc["createdAt"]
        )

        for source_doc in doc["sources"]:
            snapshot.add_source(
                km_models.KnowledgeSource(
                    source_id=source_doc["sourceId"],
                    name=source_doc["name"],
                    location=source_doc["location"],
                    source_type=km_models.SourceType(source_doc["sourceType"]),
                )
            )

        return snapshot


class AbstractKnowledgeVectorRepository(abc.ABC):
    @abc.abstractmethod
    async def add(self, knowledge_vector: models.KnowledgeVector) -> None:
        """Add a knowledge vector entry"""

    @abc.abstractmethod
    async def query_by_snapshot(
        self, embedding: list[float], snapshot_id: str, top_k: int
    ) -> list[models.KnowledgeVectorResult]:
        """Query for the top_k most similar knowledge vectors within a specific snapshot"""


class PostgresKnowledgeVectorRepository(AbstractKnowledgeVectorRepository):
    """PostgreSQL implementation of KnowledgeVectorRepository using pgvector."""

    def __init__(self, session_factory):
        """
        Initialize with SQLAlchemy async session.

        Args:
            session: An asynchronous SQLAlchemy session factory
        """
        self.session_factory = session_factory

    async def add(self, knowledge_vector: models.KnowledgeVector) -> None:
        """Add a knowledge vector entry to PostgreSQL."""
        async with self.session_factory() as session:
            session.add(knowledge_vector)
            await session.commit()

    async def add_batch(self, vectors: list[models.KnowledgeVector]) -> None:
        """Add multiple knowledge vector entries to PostgreSQL in batch."""
        async with self.session_factory() as session:
            session.add_all(vectors)
            await session.commit()

    async def query_by_snapshot(
        self, embedding: list[float], snapshot_id: str, max_results: int
    ) -> list[models.KnowledgeVectorResult]:
        """Query for the top_k most similar knowledge vectors within a specific snapshot."""
        async with self.session_factory() as session:
            query = (
                sqlalchemy.select(
                    models.KnowledgeVector.id,
                    models.KnowledgeVector.content,
                    models.KnowledgeVector.embedding,
                    models.KnowledgeVector.created_at,
                    models.KnowledgeVector.snapshot_id,
                    models.KnowledgeVector.source_id,
                    models.KnowledgeVector.metadata,
                    models.KnowledgeVector.embedding.cosine_distance(embedding).label(
                        "distance"
                    ),
                )
                .where(models.KnowledgeVector.snapshot_id == snapshot_id)
                .order_by(models.KnowledgeVector.embedding.cosine_distance(embedding))
                .limit(max_results)
            )

            result = await session.execute(query)
            rows = result.fetchall()

            return [
                models.KnowledgeVectorResult(
                    name=None,
                    location=None,
                    content=row.content,
                    similarity_score=1.0 - float(row.distance),
                    created_at=row.created_at,
                    snapshot_id=row.snapshot_id,
                    source_id=row.source_id,
                    metadata=row.metadata,
                )
                for row in rows
            ]
