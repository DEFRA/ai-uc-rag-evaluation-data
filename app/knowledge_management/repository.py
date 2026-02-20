import abc

import bson.datetime_ms
import pymongo
import pymongo.asynchronous.collection
import pymongo.asynchronous.database
import pymongo.errors

from app.knowledge_management import models


class AbstractKnowledgeGroupRepository(abc.ABC):
    @abc.abstractmethod
    async def save(self, group: models.KnowledgeGroup) -> None:
        """Save knowledge group metadata only (sources managed separately)"""

    @abc.abstractmethod
    async def get_by_id(self, group_id: str) -> models.KnowledgeGroup | None:
        """Get a complete knowledge group with all its sources loaded"""

    @abc.abstractmethod
    async def list_all(self) -> list[models.KnowledgeGroup]:
        """List all knowledge groups with their sources loaded"""

    @abc.abstractmethod
    async def add_sources_to_group(
        self, group_id: str, sources: list[models.KnowledgeSource]
    ) -> None:
        """Add multiple sources to an existing knowledge group (bulk insert)"""


class MongoKnowledgeGroupRepository(AbstractKnowledgeGroupRepository):
    def __init__(self, db: pymongo.asynchronous.database.AsyncDatabase):
        self.db: pymongo.asynchronous.database.AsyncDatabase = db
        self.knowledge_groups: pymongo.asynchronous.collection.AsyncCollection = (
            self.db.get_collection("knowledgeGroups")
        )
        self.knowledge_sources: pymongo.asynchronous.collection.AsyncCollection = (
            self.db.get_collection("knowledgeSources")
        )

    async def save(self, group: models.KnowledgeGroup) -> None:
        """Save knowledge group metadata only (sources managed separately)"""
        group_data = {
            "groupId": group.group_id,
            "title": group.name,
            "description": group.description,
            "owner": group.owner,
            "createdAt": bson.datetime_ms.DatetimeMS(group.created_at),
            "updatedAt": bson.datetime_ms.DatetimeMS(group.updated_at),
            "activeSnapshot": group.active_snapshot,
        }

        try:
            # Use upsert to handle both insert and update
            await self.knowledge_groups.update_one(
                {"groupId": group.group_id}, {"$set": group_data}, upsert=True
            )
        except pymongo.errors.DuplicateKeyError:
            msg = f"Knowledge entry with group_id '{group.group_id}' already exists"
            raise models.KnowledgeGroupAlreadyExistsError(msg) from None

        group_doc = await self.knowledge_groups.find_one({"groupId": group.group_id})

        if not group_doc:
            msg = f"Failed to save knowledge group '{group.group_id}'"
            raise RuntimeError(msg)

    async def get_by_id(self, group_id: str) -> models.KnowledgeGroup | None:
        """Get a complete knowledge group with all its sources loaded"""

        group_doc = await self.knowledge_groups.find_one({"groupId": group_id})

        if not group_doc:
            return None

        # Create group instance
        group = models.KnowledgeGroup(
            group_id=group_doc["groupId"],
            name=group_doc["title"],
            description=group_doc["description"],
            owner=group_doc["owner"],
            created_at=group_doc["createdAt"],
            updated_at=group_doc["updatedAt"],
            active_snapshot=group_doc.get("activeSnapshot", None),
        )

        cursor = self.knowledge_sources.find({"groupId": group_id})

        async for source_doc in cursor:
            source = models.KnowledgeSource(
                name=source_doc["name"],
                source_type=models.SourceType(source_doc["sourceType"]),
                location=source_doc["location"],
                source_id=source_doc["sourceId"],
            )
            group.add_source(source)

        return group

    async def list_all(self) -> list[models.KnowledgeGroup]:
        """List all knowledge groups with their sources loaded"""
        cursor = self.knowledge_groups.find()
        groups = []

        async for group_doc in cursor:
            group = models.KnowledgeGroup(
                group_id=group_doc["groupId"],
                name=group_doc["title"],
                description=group_doc["description"],
                owner=group_doc["owner"],
                created_at=group_doc["createdAt"],
                updated_at=group_doc["updatedAt"],
                active_snapshot=group_doc.get("activeSnapshot", None),
            )

            source_cursor = self.knowledge_sources.find({"groupId": group.group_id})

            async for source_doc in source_cursor:
                source = models.KnowledgeSource(
                    name=source_doc["name"],
                    source_type=source_doc["sourceType"],
                    location=source_doc["location"],
                    source_id=source_doc["sourceId"],
                )

                group.add_source(source)

            groups.append(group)

        return groups

    async def add_sources_to_group(
        self, group_id: str, sources: list[models.KnowledgeSource]
    ) -> None:
        """Add multiple sources to an existing knowledge group (bulk insert)"""
        if not sources:
            return

        source_documents = []
        for source in sources:
            source_data = {
                "groupId": group_id,
                "sourceId": source.source_id,
                "name": source.name,
                "sourceType": str(source.source_type),
                "location": source.location,
            }
            source_documents.append(source_data)

        await self.knowledge_sources.insert_many(source_documents)
