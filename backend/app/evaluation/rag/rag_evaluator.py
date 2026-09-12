from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.evaluation.rag.retrieval_evaluator import (
    RetrievalEvaluationResult,
    RetrievalMetrics,
)
from app.evaluation.rag.generation_evaluator import (
    GenerationEvaluationResult,
    GenerationMetrics,
)
from app.rag.retriever import Retriever

logger = get_logger(__name__)


@dataclass
class RAGEvaluationResult:
    test_case_id: str
    query: str
    answer: str
    retrieved_docs: list[dict[str, Any]]
    ground_truth_docs: list[str]
    retrieval_result: RetrievalEvaluationResult
    generation_result: GenerationEvaluationResult
    overall_score: float
    execution_time_ms: int
    errors: list[str]


class RAGEvaluator:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever

    async def evaluate(
        self,
        test_case_id: str,
        query: str,
        answer: str,
        retrieved_docs: list[dict[str, Any]],
        ground_truth_docs: list[str] = None,
    ) -> RAGEvaluationResult:
        start_time = datetime.utcnow()
        errors = []

        try:
            retrieval_result = await self._evaluate_retrieval(
                test_case_id, query, retrieved_docs, ground_truth_docs or []
            )
        except Exception as e:
            logger.error("retrieval_evaluation_failed", test_case_id=test_case_id, error=str(e))
            errors.append(f"Retrieval evaluation failed: {e}")
            retrieval_result = RetrievalEvaluationResult(
                test_case_id=test_case_id,
                query=query,
                retrieved_docs=retrieved_docs,
                ground_truth_docs=ground_truth_docs or [],
                metrics=RetrievalMetrics(
                    relevant_docs=0,
                    retrieved_docs=len(retrieved_docs),
                    precision=0.0,
                    recall=0.0,
                    f1_score=0.0,
                    mrr=0.0,
                    ndcg=0.0,
                ),
                execution_time_ms=0,
                errors=[str(e)],
            )

        try:
            generation_result = await self._evaluate_generation(
                test_case_id, query, answer, [d.get("content", "") for d in retrieved_docs]
            )
        except Exception as e:
            logger.error("generation_evaluation_failed", test_case_id=test_case_id, error=str(e))
            errors.append(f"Generation evaluation failed: {e}")
            generation_result = GenerationEvaluationResult(
                test_case_id=test_case_id,
                query=query,
                answer=answer,
                context=[d.get("content", "") for d in retrieved_docs],
                metrics=GenerationMetrics(
                    faithfulness=0.0,
                    answer_relevance=0.0,
                    context_recall=0.0,
                    context_precision=0.0,
                    factuality=0.0,
                    hallucination_rate=1.0,
                ),
                execution_time_ms=0,
                errors=[str(e)],
            )

        overall_score = (
            retrieval_result.metrics.f1_score * 0.4 + generation_result.metrics.faithfulness * 0.6
        )

        elapsed = datetime.utcnow() - start_time
        total_time_ms = int(elapsed.total_seconds() * 1000)

        return RAGEvaluationResult(
            test_case_id=test_case_id,
            query=query,
            answer=answer,
            retrieved_docs=retrieved_docs,
            ground_truth_docs=ground_truth_docs or [],
            retrieval_result=retrieval_result,
            generation_result=generation_result,
            overall_score=overall_score,
            execution_time_ms=total_time_ms,
            errors=errors,
        )

    async def _evaluate_retrieval(
        self,
        test_case_id: str,
        query: str,
        retrieved_docs: list[dict[str, Any]],
        ground_truth_docs: list[str],
    ) -> RetrievalEvaluationResult:
        retrieved_contents = [d.get("content", "") for d in retrieved_docs]

        relevant_docs = 0
        for doc in retrieved_contents:
            for gt in ground_truth_docs:
                if gt.lower() in doc.lower():
                    relevant_docs += 1
                    break

        retrieved_count = len(retrieved_docs)
        ground_truth_count = len(ground_truth_docs)

        precision = relevant_docs / retrieved_count if retrieved_count > 0 else 0.0
        recall = relevant_docs / ground_truth_count if ground_truth_count > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        mrr = self._calculate_mrr(retrieved_contents, ground_truth_docs)
        ndcg = self._calculate_ndcg(retrieved_contents, ground_truth_docs)

        return RetrievalEvaluationResult(
            test_case_id=test_case_id,
            query=query,
            retrieved_docs=retrieved_docs,
            ground_truth_docs=ground_truth_docs,
            metrics=RetrievalMetrics(
                relevant_docs=relevant_docs,
                retrieved_docs=len(retrieved_docs),
                precision=precision,
                recall=recall,
                f1_score=f1,
                mrr=mrr,
                ndcg=ndcg,
            ),
            execution_time_ms=0,
            errors=[],
        )

    def _calculate_mrr(self, retrieved: list[str], ground_truth: list[str]) -> float:
        for i, doc in enumerate(retrieved):
            for gt in ground_truth:
                if gt.lower() in doc.lower():
                    return 1.0 / (i + 1)
        return 0.0

    def _calculate_ndcg(self, retrieved: list[str], ground_truth: list[str], k: int = 10) -> float:
        if not ground_truth:
            return 0.0

        dcg = 0.0
        for i, doc in enumerate(retrieved[:k]):
            rel = 1.0 if any(gt.lower() in doc.lower() for gt in ground_truth) else 0.0
            if rel > 0:
                import math
                dcg += rel / math.log2(i + 2)

        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(ground_truth), k)))

        return dcg / idcg if idcg > 0 else 0.0

    async def _evaluate_generation(
        self,
        test_case_id: str,
        query: str,
        answer: str,
        context: list[str],
    ) -> GenerationEvaluationResult:
        faithfulness = await self._calculate_faithfulness(answer, context)
        answer_relevance = await self._calculate_answer_relevance(answer, query)
        context_recall = await self._calculate_context_recall(query, context)
        context_precision = await self._calculate_context_precision(query, context)
        factuality = await self._calculate_factuality(answer, context)
        hallucination_rate = 1.0 - faithfulness

        return GenerationEvaluationResult(
            test_case_id=test_case_id,
            query=query,
            answer=answer,
            context=context,
            metrics=GenerationMetrics(
                faithfulness=faithfulness,
                answer_relevance=answer_relevance,
                context_recall=context_recall,
                context_precision=context_precision,
                factuality=factuality,
                hallucination_rate=hallucination_rate,
            ),
            execution_time_ms=0,
            errors=[],
        )

    async def _calculate_faithfulness(self, answer: str, context: list[str]) -> float:
        context_text = " ".join(context).lower()
        answer_lower = answer.lower()

        if not context_text:
            return 0.0

        answer_claims = self._extract_claims(answer)
        if not answer_claims:
            return 1.0

        supported = 0
        for claim in answer_claims:
            if claim.lower() in context_text:
                supported += 1

        return supported / len(answer_claims)

    async def _calculate_answer_relevance(self, answer: str, query: str) -> float:
        query_terms = set(query.lower().split())
        answer_terms = set(answer.lower().split())

        if not query_terms:
            return 0.0

        overlap = len(query_terms & answer_terms)
        return overlap / len(query_terms)

    async def _calculate_context_recall(self, query: str, context: list[str]) -> float:
        query_terms = set(query.lower().split())
        context_text = " ".join(context).lower()

        if not query_terms:
            return 1.0

        found = sum(1 for term in query_terms if term in context_text)
        return found / len(query_terms)

    async def _calculate_context_precision(self, query: str, context: list[str]) -> float:
        if not context:
            return 0.0

        query_terms = set(query.lower().split())
        relevant_docs = 0

        for doc in context:
            doc_terms = set(doc.lower().split())
            if query_terms & doc_terms:
                relevant_docs += 1

        return relevant_docs / len(context)

    async def _calculate_factuality(self, answer: str, context: list[str]) -> float:
        context_text = " ".join(context).lower()
        answer_lower = answer.lower()

        if not answer_lower:
            return 1.0

        answer_claims = self._extract_claims(answer)
        if not answer_claims:
            return 1.0

        supported = 0
        for claim in answer_claims:
            if claim.lower() in context_text:
                supported += 1

        return supported / len(answer_claims)

    def _extract_claims(self, text: str) -> list[str]:
        import re

        sentences = re.split(r"[.!?]+", text)
        claims = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        return claims