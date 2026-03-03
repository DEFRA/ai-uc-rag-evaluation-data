from abc import ABC, abstractmethod


class AbstractEmbeddingService(ABC):
    @abstractmethod
    async def generate_embeddings(self, input_text: str) -> list[float]:
        pass
