from app import config
from app.common import bedrock, mongo, postgres
from app.infra import mcp_server
from app.knowledge_management import repository as km_repository
from app.knowledge_management import service as km_service
from app.snapshot import models, repository, service


@mcp_server.data_mcp_server.tool()
async def relevant_sources_by_group(
    group_id: str, query: str, max_results: int = 5
) -> list[models.KnowledgeVectorResult]:
    """
    A tool to retrieve relevant documents based on a query.
    """

    db = await mongo.get_db(await mongo.get_mongo_client())
    session_factory = await postgres.get_async_session_factory()

    snapshot_repo = repository.MongoKnowledgeSnapshotRepository(db)
    vector_repo = repository.PostgresKnowledgeVectorRepository(session_factory)
    group_repo = km_repository.MongoKnowledgeGroupRepository(db)

    embedding_service = bedrock.BedrockEmbeddingService(
        bedrock.get_bedrock_client(), config.config.bedrock_embedding_config
    )
    snapshot_service = service.SnapshotService(
        snapshot_repo, vector_repo, embedding_service
    )
    knowledge_service = km_service.KnowledgeManagementService(group_repo)

    group = await knowledge_service.find_knowledge_group(group_id)

    return await snapshot_service.search_similar(group, query, max_results)
