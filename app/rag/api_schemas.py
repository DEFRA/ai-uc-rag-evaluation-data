import pydantic


class AskRequest(pydantic.BaseModel):
    """Request model for asking a question against a knowledge group."""

    question: str = pydantic.Field(description="The question to answer")
    max_context_results: int = pydantic.Field(
        5,
        description="Maximum number of context documents to retrieve",
        validation_alias="maxContextResults",
    )


class SourceReference(pydantic.BaseModel):
    """A source document used to answer the question."""

    content: str = pydantic.Field(description="The content of the source document")
    similarity_score: float = pydantic.Field(
        description="Similarity score of this source to the question (0.0 to 1.0)",
        serialization_alias="similarityScore",
    )
    name: str | None = pydantic.Field(
        default=None, description="Name of the source document"
    )
    location: str | None = pydantic.Field(
        default=None, description="Location of the source document"
    )
    source_id: str = pydantic.Field(
        description="Internal ID of the source document",
        serialization_alias="sourceId",
    )


class AskResponse(pydantic.BaseModel):
    """Response model for a RAG question answer."""

    answer: str = pydantic.Field(description="The generated answer to the question")
    sources: list[SourceReference] = pydantic.Field(
        description="Source documents used to generate the answer"
    )
