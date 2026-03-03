import sqlalchemy
import sqlalchemy.ext.asyncio

from app.upload import models, orm_models


class UploadRecordRepository:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def save(self, record: models.UploadRecord) -> None:
        async with self.session_factory() as session:
            session.add(record)
            await session.commit()

    async def get_status_by_location(self, location: str) -> str | None:
        async with self.session_factory() as session:
            result = await session.execute(
                sqlalchemy.select(orm_models.upload_records.c.upload_status).where(
                    orm_models.upload_records.c.location == location
                )
            )
            row = result.first()
            return row.upload_status if row else None
