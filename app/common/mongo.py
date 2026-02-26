import logging

import fastapi
import pymongo

from app import config
from app.common import tls

logger = logging.getLogger(__name__)

client: pymongo.AsyncMongoClient | None = None
db: pymongo.asynchronous.database.AsyncDatabase | None = None


async def get_mongo_client() -> pymongo.AsyncMongoClient:
    global client
    if client is None:
        # Use the custom CA Certs from env vars if set.
        # We can remove this once we migrate to mongo Atlas.
        cert = tls.custom_ca_certs.get(config.config.mongo_truststore)
        if cert:
            logger.info(
                "Creating MongoDB client with custom TLS cert %s",
                config.config.mongo_truststore,
            )
            client = pymongo.AsyncMongoClient(config.config.mongo_uri, tlsCAFile=cert)
        else:
            logger.info("Creating MongoDB client")
            client = pymongo.AsyncMongoClient(config.config.mongo_uri)

        logger.info("Testing MongoDB connection to %s", config.config.mongo_uri)
        await check_connection(client)
    return client


async def get_db(
    client: pymongo.AsyncMongoClient = fastapi.Depends(get_mongo_client),
) -> pymongo.asynchronous.database.AsyncDatabase:
    global db
    if db is None:
        db = client.get_database(config.config.mongo_database)

        await _ensure_indexes(db)
    return db


async def check_connection(client: pymongo.AsyncMongoClient):
    database = client.get_database(config.config.mongo_database)
    response = await database.command("ping")
    logger.info("MongoDB PING %s", response)


async def _ensure_indexes(db: pymongo.asynchronous.database.AsyncDatabase) -> None:
    """Ensure indexes are created on startup."""
    logger.info("Ensuring MongoDB indexes are present")

    knowledge_entries = db.get_collection("knowledgeEntries")

    await knowledge_entries.create_index("title", unique=True)

    logger.info("MongoDB indexes ensured")
