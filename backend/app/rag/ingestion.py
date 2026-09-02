from typing import Any

from app.core.logging import get_logger
from app.rag.vector_store import VectorStore

logger = get_logger(__name__)


class IngestionPipeline:
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store

    async def ingest_attack_taxonomy(self, entries: list[dict[str, Any]]):
        texts = []
        embeddings = []
        metadatas = []

        for entry in entries:
            content = f"{entry.get('technique', '')}: {entry.get('description', '')}"
            if entry.get("examples"):
                content += "\nExamples: " + "; ".join(entry["examples"][:3])

            texts.append(content)
            metadatas.append({
                "category": entry.get("category"),
                "subcategory": entry.get("subcategory"),
                "technique": entry.get("technique"),
                "severity": entry.get("severity"),
                "tags": entry.get("tags", []),
            })

        if texts:
            embeddings = await self.vector_store.embedding_provider.embed_batch(texts)
            await self.vector_store.add_batch("attack_taxonomy", texts, embeddings, metadatas)
            logger.info("ingested_attack_taxonomy", count=len(texts))

    async def ingest_judgment(self, test_input: str, response: str, verdict: str, rationale: str, metadata: dict[str, Any] = None):
        content = f"Input: {test_input}\nResponse: {response}\nVerdict: {verdict}\nRationale: {rationale}"
        meta = {"verdict": verdict}
        if metadata:
            meta.update(metadata)

        embedding = await self.vector_store.embedding_provider.embed(content)
        await self.vector_store.add("historical_judgments", content, embedding, meta)

    async def ingest_review_precedent(self, regression: dict[str, Any], review_label: str, reviewer_notes: str):
        content = f"Regression: {regression.get('regression_type')}\nCategory: {regression.get('category')}\nLabel: {review_label}\nNotes: {reviewer_notes}"
        meta = {
            "regression_type": regression.get("regression_type"),
            "category": regression.get("category"),
            "label": review_label,
        }

        embedding = await self.vector_store.embedding_provider.embed(content)
        await self.vector_store.add("review_precedents", content, embedding, meta)

    async def ingest_adversarial_prompt(self, prompt: str, metadata: dict[str, Any] = None):
        embedding = await self.vector_store.embedding_provider.embed(prompt)
        await self.vector_store.add("adversarial_prompts", prompt, embedding, metadata or {})
