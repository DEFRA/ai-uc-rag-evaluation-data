import logging

import boto3
import sqlalchemy
import sqlalchemy.event
import sqlalchemy.ext.asyncio

from app import config
from app.common import tls
from app.snapshot import orm_models
from app.upload import orm_models as upload_orm_models

logger = logging.getLogger(__name__)

engine: sqlalchemy.ext.asyncio.AsyncEngine = None
async_session_factory: sqlalchemy.ext.asyncio.async_sessionmaker[
    sqlalchemy.ext.asyncio.AsyncSession
] = None


async def get_sql_engine() -> sqlalchemy.ext.asyncio.AsyncEngine:
    global engine

    if engine is not None:
        return engine

    url = sqlalchemy.URL.create(
        drivername="postgresql+psycopg",
        username=config.config.postgres.user,
        host=config.config.postgres.host,
        port=config.config.postgres.port,
        database=config.config.postgres.database,
    )

    cert = tls.custom_ca_certs.get(config.config.postgres.rds_truststore)

    if cert:
        logger.info(
            "Creating Postgres SQLAlchemy engine with custom TLS cert %s",
            config.config.postgres.rds_truststore,
        )
        engine = sqlalchemy.ext.asyncio.create_async_engine(
            url,
            connect_args={
                "sslmode": config.config.postgres.ssl_mode,
                "sslrootcert": cert,
            },
            hide_parameters=config.config.python_env != "development",
        )
    else:
        logger.info("Creating Postgres SQLAlchemy engine without custom TLS cert")
        engine = sqlalchemy.ext.asyncio.create_async_engine(
            url,
            connect_args={"sslmode": config.config.postgres.ssl_mode},
            hide_parameters=config.config.python_env != "development",
        )

    orm_models.start_mappers()
    upload_orm_models.start_mappers()
    logger.info("SQLAlchemy ORM mappers started")

    sqlalchemy.event.listen(engine.sync_engine, "do_connect", get_token)

    logger.info(
        "Testing Postgres SQLAlchemy connection to %s", config.config.postgres.host
    )
    await check_connection(engine)

    return engine


async def check_connection(engine: sqlalchemy.ext.asyncio.AsyncEngine) -> bool:
    async with engine.connect() as connection:
        await connection.execute(sqlalchemy.text("SELECT 1 FROM knowledge_vectors"))


def get_token(dialect, conn_rec, cargs, cparams):  # noqa: ARG001
    if config.config.python_env == "development":
        cparams["password"] = config.config.postgres.password
    else:
        logger.info("Generating RDS auth token for Postgres connection")

        client = boto3.client("rds")

        token = client.generate_db_auth_token(
            Region=config.config.aws_region,
            DBHostname=config.config.postgres.host,
            Port=config.config.postgres.port,
            DBUsername=config.config.postgres.user,
        )

        logger.info("Generated RDS auth token for Postgres connection")

        cparams["password"] = token


async def get_async_session_factory() -> sqlalchemy.ext.asyncio.async_sessionmaker[
    sqlalchemy.ext.asyncio.AsyncSession
]:
    """Get or create the async session factory."""
    global async_session_factory

    if async_session_factory is None:
        engine = await get_sql_engine()
        async_session_factory = sqlalchemy.ext.asyncio.async_sessionmaker(
            engine, class_=sqlalchemy.ext.asyncio.AsyncSession, expire_on_commit=False
        )

    return async_session_factory
