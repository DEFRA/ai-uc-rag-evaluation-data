import bson.datetime_ms
import pymongo.asynchronous.collection
import pymongo.asynchronous.database

from app.upload import models


class UploadRecordRepository:
    def __init__(self, db: pymongo.asynchronous.database.AsyncDatabase):
        self.upload_records: pymongo.asynchronous.collection.AsyncCollection = (
            db.get_collection("uploadRecords")
        )

    async def save(self, record: models.UploadRecord) -> None:
        await self.upload_records.insert_one(
            {
                "uploadStatus": record.upload_status,
                "location": record.location,
                "createdAt": bson.datetime_ms.DatetimeMS(record.created_at),
            }
        )

    async def get_status_by_location(self, location: str) -> str | None:
        doc = await self.upload_records.find_one({"location": location})
        return doc["uploadStatus"] if doc else None
