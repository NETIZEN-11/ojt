from typing import Any

from app.core.logging import get_logger
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


class Retriever:
    def __init__(self, vector_store: VectorStore, top_k: int = 5):
        self.vector_store = vector_store
        self.top_k = top_k

    async def retrieve(
        self,
        query: str,
        collection: str = "attack_taxonomy",
        top_k: int = None,
        filters: dict[str, Any] = None,
    ) -> list[dict[str, Any]]:
        top_k = top_k or self.top_k
        results = await self.vector_store.search_by_text(collection, query, top_k)

        return [
            {
                "content": doc,
                "similarity": score,
                "metadata": meta,
            }
            for doc, score, meta in results
        ]

    async def retrieve_for_judge(self, test_input: str, response: str) -> list[dict[str, Any]]:
        query = f"Test: {test_input}\nResponse: {response}"
        return await self.retrieve(query, "historical_judgments", top_k=3)

    async def retrieve_for_generator(self, category: str, previous_failures: list[str] = None) -> list[dict[str, Any]]:
        query = f"Category: {category}"
        if previous_failures:
            query += "\nPrevious failures: " + "; ".join(previous_failures[:3])
        return await self.retrieve(query, "attack_taxonomy", top_k=5)

    async def retrieve_for_review(self, regression_finding: dict[str, Any]) -> list[dict[str, Any]]:
        query = f"Regression: {regression_finding.get('regression_type')}\nCategory: {regression_finding.get('category')}"
        return await self.retrieve(query, "review_precedents", top_k=3)
