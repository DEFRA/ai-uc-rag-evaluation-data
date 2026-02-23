import os


def pytest_configure(config):  # noqa: ARG001
    """Set environment variables before any imports happen."""
    os.environ.update(
        {
            "AWS_REGION": "eu-west-2",
            "AWS_DEFAULT_REGION": "eu-west-2",
            "AWS_ACCESS_KEY_ID": "change_me",
            "AWS_SECRET_ACCESS_KEY": "change_me",
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "ai_uc_rag_evolution_data",
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "ppp",
            "POSTGRES_SSL_MODE": "disable",
            "BEDROCK_EMBEDDING_MODEL_ID": "amazon.titan-embed-text-v2:0",
            "INGESTION_DATA_BUCKET_NAME": "ai-uc-rag-evolution-data-ingestion-data",
            "PORT": "8000",
        }
    )
