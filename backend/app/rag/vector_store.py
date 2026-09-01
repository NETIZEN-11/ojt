from typing import List, Tuple, Dict, Any, Optional
from uuid import UUID, uuid4
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.embeddings import EmbeddingProvider

settings = get_settings()
logger = get_logger(__name__)


class VectorStore:
    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collections: Dict[str, Any] = {}

    def _get_collection(self, name: str):
        full_name = f"{settings.CHROMA_COLLECTION_PREFIX}_{name}"
        if full_name not in self.collections:
            self.collections[full_name] = self.client.get_or_create_collection(full_name)
        return self.collections[full_name]

    async def add(self, collection: str, text: str, embedding: List[float], metadata: Dict[str, Any] = None):
        col = self._get_collection(collection)
        doc_id = str(uuid4())
        col.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata or {}],
        )
        return doc_id

    async def add_batch(self, collection: str, texts: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Any]] = None):
        col = self._get_collection(collection)
        ids = [str(uuid4()) for _ in texts]
        col.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas or [{} for _ in texts],
        )
        return ids

    async def search(self, collection: str, query_embedding: List[float], top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        col = self._get_collection(collection)
        results = col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        output = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 1.0
                similarity = 1.0 - distance
                output.append((
                    results["documents"][0][i],
                    similarity,
                    results["metadatas"][0][i] if results["metadatas"] else {},
                ))
        return output

    async def search_by_text(self, collection: str, query_text: str, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        embedding = await self.embedding_provider.embed(query_text)
        return await self.search(collection, embedding, top_k)

    async def delete(self, collection: str, ids: List[str]):
        col = self._get_collection(collection)
        col.delete(ids=ids)

    async def get_collection_stats(self, collection: str) -> Dict[str, Any]:
        col = self._get_collection(collection)
        return {"count": col.count(), "name": col.name}