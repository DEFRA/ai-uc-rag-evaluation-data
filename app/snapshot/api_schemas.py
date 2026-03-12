import pydantic


class QuerySnapshotRequest(pydantic.BaseModel):
    """Request model for querying a snapshot."""

    group_id: str = pydantic.Field(
        description="The ID of the knowledge group", validation_alias="groupId"
    )
    query: str = pydantic.Field(description="The search query")
    max_results: int = pydantic.Field(
        5,
        description="Maximum number of results to return",
        validation_alias="maxResults",
    )
    snapshot_id: str | None = pydantic.Field(
        default=None,
        description="Specific snapshot to query. Defaults to the group's active snapshot.",
        validation_alias="snapshotId",
    )


class KnowledgeSnapshotResponse(pydantic.BaseModel):
    """Response model for a knowledge group."""

    snapshot_id: str = pydantic.Field(
        description="The unique identifier of the knowledge snapshot",
        alias="snapshotId",
    )
    group_id: str = pydantic.Field(
        description="The unique identifier of the knowledge group", alias="groupId"
    )
    version: int = pydantic.Field(description="The version number of the snapshot")
    created_at: str = pydantic.Field(
        description="The creation date of the knowledge snapshot in ISO format",
        alias="createdAt",
    )
    ingestion_status: str = pydantic.Field(
        description="The ingestion status of the snapshot",
        alias="ingestionStatus",
    )
    sources: list[dict] = pydantic.Field(
        description="List of knowledge snapshot sources"
    )


class KnowledgeVectorResultResponse(pydantic.BaseModel):
    """Response model for a knowledge vector search result."""

    content: str = pydantic.Field(
        description="The content of the knowledge vector result"
    )
    similarity_score: float = pydantic.Field(
        description="The similarity score of the result (0.0 to 1.0)",
        serialization_alias="similarityScore",
    )
    similarity_category: str = pydantic.Field(
        description="The similarity category of the result (very_high, high, medium, low)",
        serialization_alias="similarityCategory",
    )
    created_at: str = pydantic.Field(
        description="The creation date of the knowledge vector result in ISO format",
        serialization_alias="createdAt",
    )
    name: str = pydantic.Field(description="The name of the knowledge vector result")
    location: str = pydantic.Field(
        description="The location of the knowledge vector result"
    )
    snapshot_id: str = pydantic.Field(
        description="Internal ID representing the snapshot used",
        serialization_alias="snapshotId",
    )
    source_id: str = pydantic.Field(
        description="Internal ID representing the source document",
        serialization_alias="sourceId",
    )
