import pgvector.sqlalchemy
import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlalchemy.orm

from app.snapshot import models


class Base(sqlalchemy.orm.DeclarativeBase):
    """SQLAlchemy declarative base."""


metadata = sqlalchemy.MetaData()
mapper_registry = sqlalchemy.orm.registry(metadata=metadata)

knowledge_vectors = sqlalchemy.Table(
    "knowledge_vectors",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, nullable=False),
    sqlalchemy.Column("content", sqlalchemy.Text, nullable=False),
    sqlalchemy.Column("embedding", pgvector.sqlalchemy.Vector(1024), nullable=False),
    sqlalchemy.Column(
        "created_at",
        sqlalchemy.DateTime(timezone=True),
        nullable=False,
        server_default=sqlalchemy.func.current_timestamp(),
    ),
    sqlalchemy.Column("snapshot_id", sqlalchemy.String(50), nullable=True),
    sqlalchemy.Column("source_id", sqlalchemy.String(50), nullable=True),
    sqlalchemy.Column("metadata", sqlalchemy.dialects.postgresql.JSONB, nullable=True),
)


def start_mappers():
    mapper_registry.map_imperatively(
        models.KnowledgeVector,
        knowledge_vectors,
        properties={
            "id": knowledge_vectors.c.id,
            "content": knowledge_vectors.c.content,
            "embedding": knowledge_vectors.c.embedding,
            "created_at": knowledge_vectors.c.created_at,
            "snapshot_id": knowledge_vectors.c.snapshot_id,
            "source_id": knowledge_vectors.c.source_id,
            "metadata": knowledge_vectors.c.metadata,
        },
    )
