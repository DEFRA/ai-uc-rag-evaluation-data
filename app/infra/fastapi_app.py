import logging
from contextlib import asynccontextmanager

import fastapi
import fastapi.exceptions
import fastapi.responses

from app.common import mongo, postgres, tracing
from app.health import router as health_router
from app.infra import mcp_server
from app.knowledge_management import router as knowledge_management_router
from app.snapshot import router as snapshot_router
from app.upload import router as upload_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: fastapi.FastAPI):
    client = await mongo.get_mongo_client()
    logger.info("MongoDB client connected")

    engine = await postgres.get_sql_engine()
    logger.info("Postgres SQLAlchemy engine created")

    yield

    # Shutdown
    if client:
        await client.close()
        logger.info("MongoDB client closed")

    if engine:
        await engine.dispose()
        logger.info("Postgres SQLAlchemy engine disposed")


mcp_app = mcp_server.data_mcp_server.http_app(path="/mcp")


@asynccontextmanager
async def combined_lifespan(app: fastapi.FastAPI):
    async with lifespan(app), mcp_app.lifespan(app):
        yield


app = fastapi.FastAPI(lifespan=combined_lifespan)


@app.exception_handler(fastapi.exceptions.RequestValidationError)
async def validation_exception_handler(request, exc):  # noqa: ARG001
    return fastapi.responses.JSONResponse(
        status_code=400,
        content={"detail": exc.errors()},
    )


# Setup middleware
app.add_middleware(tracing.TraceIdMiddleware)

# Setup Routes
app.include_router(health_router.router)
app.include_router(knowledge_management_router.router)
app.include_router(snapshot_router.router)
app.include_router(upload_router.router)

app.mount("/", mcp_app)
