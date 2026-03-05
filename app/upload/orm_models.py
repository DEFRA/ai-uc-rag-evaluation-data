import sqlalchemy
import sqlalchemy.orm

from app.upload import models

metadata = sqlalchemy.MetaData()
mapper_registry = sqlalchemy.orm.registry(metadata=metadata)

upload_records = sqlalchemy.Table(
    "upload_records",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, nullable=False),
    sqlalchemy.Column("upload_status", sqlalchemy.String(50), nullable=False),
    sqlalchemy.Column("location", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column(
        "created_at",
        sqlalchemy.DateTime(timezone=True),
        nullable=False,
        server_default=sqlalchemy.func.current_timestamp(),
    ),
)


def start_mappers():
    mapper_registry.map_imperatively(
        models.UploadRecord,
        upload_records,
        properties={
            "upload_status": upload_records.c.upload_status,
            "location": upload_records.c.location,
            "created_at": upload_records.c.created_at,
        },
    )
