import json
from abc import ABC, abstractmethod

import boto3

from app import config

bedrock_client: boto3.client = None


def get_bedrock_client():
    global bedrock_client

    if bedrock_client is None:
        bedrock_client = boto3.client(
            "bedrock-runtime", region_name=config.config.aws_region
        )

    return bedrock_client


class AbstractEmbeddingService(ABC):
    @abstractmethod
    def generate_embeddings(self, input_text: str) -> list[float]:
        pass


class BedrockEmbeddingService(AbstractEmbeddingService):
    def __init__(
        self, client: boto3.client, model_config: config.BedrockEmbeddingConfig
    ):
        self.client = client
        self.model_config = model_config

    def generate_embeddings(self, input_text: str) -> list[float]:
        request = {"inputText": input_text}

        invoke_options = {
            "modelId": self.model_config.model_id,
            "contentType": "application/json",
            "accept": "application/json",
            "body": json.dumps(request),
        }

        response = self.client.invoke_model(**invoke_options)

        response_body = json.loads(response["body"].read().decode("utf-8"))

        return response_body["embedding"]
