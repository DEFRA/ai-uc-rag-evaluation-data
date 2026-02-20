import pydantic
import pydantic_settings


class BedrockEmbeddingConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict()
    model_id: str = pydantic.Field(..., alias="BEDROCK_EMBEDDING_MODEL_ID")


class PostgresConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict()
    host: str = pydantic.Field(..., alias="POSTGRES_HOST")
    port: int = pydantic.Field(5432, alias="POSTGRES_PORT")
    database: str = pydantic.Field(default="ai_uc_rag_evaluation_data", alias="POSTGRES_DB")
    user: str = pydantic.Field(default="ai_uc_rag_evaluation_data", alias="POSTGRES_USER")
    password: str | None = pydantic.Field(default=None, alias="POSTGRES_PASSWORD")
    ssl_mode: str = pydantic.Field(default="require", alias="POSTGRES_SSL_MODE")
    rds_truststore: str | None = pydantic.Field(
        default=None, alias="TRUSTSTORE_RDS_ROOT_CA"
    )


class AppConfig(pydantic_settings.BaseSettings):
    aws_region: str = pydantic.Field(..., alias="AWS_REGION")
    model_config = pydantic_settings.SettingsConfigDict()
    python_env: str = "development"
    host: str | None = None
    port: int
    log_config: str | None = None
    mongo_uri: str | None = None
    mongo_database: str = "ai-uc-rag-evaluation-data"
    mongo_truststore: str = "TRUSTSTORE_CDP_ROOT_CA"
    localstack_url: str | None = None
    http_proxy: pydantic.HttpUrl | None = None
    enable_metrics: bool = False
    tracing_header: str = "x-cdp-request-id"
    ingestion_data_bucket: str = pydantic.Field(..., alias="INGESTION_DATA_BUCKET_NAME")
    postgres: PostgresConfig = PostgresConfig()
    bedrock_embedding_config: BedrockEmbeddingConfig = BedrockEmbeddingConfig()


config = AppConfig()
