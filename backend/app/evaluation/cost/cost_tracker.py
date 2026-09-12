from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.core.config import get_settings
from app.core.database import get_async_session
from app.core.logging import get_logger
from app.evaluation.cost.cost_models import (
    CostBreakdown,
    CostCategory,
    CostEntry,
    CostSummary,
    CostTrend,
)
from app.models.cost import CostEntryModel

settings = get_settings()
logger = get_logger(__name__)


class CostTracker:
    def __init__(self):
        self.pricing = {
            "openai": {
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-4-turbo": {"input": 0.01, "output": 0.03},
                "gpt-4o": {"input": 0.005, "output": 0.015},
                "gpt-4o-2024-08-06": {"input": 0.005, "output": 0.015},
                "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
                "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
                "text-embedding-3-small": {"input": 0.00002, "output": 0},
                "text-embedding-3-large": {"input": 0.00013, "output": 0},
            },
            "anthropic": {
                "claude-3-opus": {"input": 0.015, "output": 0.075},
                "claude-3-sonnet": {"input": 0.003, "output": 0.015},
                "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
                "claude-3.5-sonnet": {"input": 0.003, "output": 0.015},
                "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
                "claude-3-5-sonnet": {"input": 0.003, "output": 0.015},
            },
            "google": {
                "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
                "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
            },
            "cohere": {
                "command-r-plus": {"input": 0.003, "output": 0.015},
                "command-r": {"input": 0.0005, "output": 0.0015},
            },
        }

    def calculate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        provider = provider.lower()
        model_key = model.lower()

        if provider in self.pricing:
            # Exact match
            if model_key in self.pricing[provider]:
                pricing = self.pricing[provider][model_key]
                input_cost = (input_tokens / 1000) * pricing.get("input", 0)
                output_cost = (output_tokens / 1000) * pricing.get("output", 0)
                return input_cost + output_cost
            # Fallback: strip version suffix and try base model
            base_model = model_key.split("-202")[0].split("-20")[0]
            if base_model in self.pricing[provider]:
                pricing = self.pricing[provider][base_model]
                input_cost = (input_tokens / 1000) * pricing.get("input", 0)
                output_cost = (output_tokens / 1000) * pricing.get("output", 0)
                return input_cost + output_cost
            # Partial prefix match for claude/gpt variants
            for key, pricing in self.pricing[provider].items():
                if model_key.startswith(key) or key.startswith(model_key):
                    input_cost = (input_tokens / 1000) * pricing.get("input", 0)
                    output_cost = (output_tokens / 1000) * pricing.get("output", 0)
                    return input_cost + output_cost

        logger.warning("cost_unknown_model", provider=provider, model=model)
        return 0.0

    async def track_cost(
        self,
        category: CostCategory,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        run_id: UUID = None,
        test_case_id: UUID = None,
        metadata: dict[str, Any] = None,
    ) -> CostEntry:
        cost_usd = self.calculate_cost(provider, model, input_tokens, output_tokens)

        entry = CostEntry(
            id=uuid4(),
            run_id=run_id,
            test_case_id=test_case_id,
            category=category,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd,
            metadata=metadata or {},
        )

        logger.info(
            "cost_tracked",
            category=category.value,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

        async with get_async_session() as session:
            db_entry = CostEntryModel(
                id=entry.id,
                run_id=entry.run_id,
                test_case_id=entry.test_case_id,
                category=entry.category.value,
                provider=entry.provider,
                model=entry.model,
                input_tokens=entry.input_tokens,
                output_tokens=entry.output_tokens,
                total_tokens=entry.total_tokens,
                cost_usd=entry.cost_usd,
                currency=entry.currency,
                metadata_json=entry.metadata,
            )
            session.add(db_entry)

            trend = CostTrendModel(
                id=uuid4(),
                date=datetime.utcnow(),
                cost_usd=entry.cost_usd,
                token_count=entry.total_tokens,
                request_count=1,
                run_id=entry.run_id,
                provider=entry.provider,
                model=entry.model,
                category=entry.category.value,
            )
            session.add(trend)

            await session.commit()

        return entry

    def check_limits(
        self,
        run_cost: float,
        daily_cost: float,
    ) -> dict[str, bool]:
        limits = {
            "run_limit_exceeded": run_cost > settings.COST_PER_RUN_LIMIT_USD,
            "daily_limit_exceeded": daily_cost > settings.COST_DAILY_LIMIT_USD,
        }
        return limits

    async def get_summary(
        self,
        start_time: datetime,
        end_time: datetime,
        run_ids: list[UUID] = None,
    ) -> CostSummary:
        async with get_async_session() as session:
            from sqlalchemy import select, func, and_

            query = select(
                func.sum(CostEntryModel.cost_usd).label("total_cost"),
                func.sum(CostEntryModel.input_tokens).label("total_input"),
                func.sum(CostEntryModel.output_tokens).label("total_output"),
                func.sum(CostEntryModel.total_tokens).label("total_tokens"),
            ).where(
                and_(
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            )

            if run_ids:
                query = query.where(CostEntryModel.run_id.in_(run_ids))

            result = await session.execute(query)
            row = result.one()

            by_category_q = select(
                CostEntryModel.category,
                func.sum(CostEntryModel.cost_usd).label("cost"),
            ).where(
                and_(
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            ).group_by(CostEntryModel.category)

            by_provider_q = select(
                CostEntryModel.provider,
                func.sum(CostEntryModel.cost_usd).label("cost"),
            ).where(
                and_(
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            ).group_by(CostEntryModel.provider)

            by_model_q = select(
                CostEntryModel.model,
                func.sum(CostEntryModel.cost_usd).label("cost"),
            ).where(
                and_(
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            ).group_by(CostEntryModel.model)

            by_run_q = select(
                CostEntryModel.run_id,
                func.sum(CostEntryModel.cost_usd).label("cost"),
            ).where(
                and_(
                    CostEntryModel.created_at >= start_time,
                    CostEntryModel.created_at <= end_time,
                )
            ).group_by(CostEntryModel.run_id)

            by_category_res = await session.execute(by_category_q)
            by_provider_res = await session.execute(by_provider_q)
            by_model_res = await session.execute(by_model_q)
            by_run_res = await session.execute(by_run_q)

            by_category = {row.category: float(row.cost or 0) for row in by_category_res}
            by_provider = {row.provider: float(row.cost or 0) for row in by_provider_res}
            by_model = {row.model: float(row.cost or 0) for row in by_model_res}
            by_run = {str(row.run_id): float(row.cost or 0) for row in by_run_res if row.run_id}

            return CostSummary(
                total_cost_usd=float(row.total_cost or 0),
                total_input_tokens=int(row.total_input or 0),
                total_output_tokens=int(row.total_output or 0),
                total_tokens=int(row.total_tokens or 0),
                by_category=by_category,
                by_provider=by_provider,
                by_model=by_model,
                by_run=by_run,
                period_start=start_time,
                period_end=end_time,
            )

    async def get_breakdown(self, run_id: UUID) -> CostBreakdown:
        async with get_async_session() as session:
            from sqlalchemy import select

            query = select(CostEntryModel).where(CostEntryModel.run_id == run_id)
            result = await session.execute(query)
            entries = result.scalars().all()

            total_cost = sum(e.cost_usd for e in entries)
            entries_data = [
                {
                    "id": str(e.id),
                    "category": e.category,
                    "provider": e.provider,
                    "model": e.model,
                    "input_tokens": e.input_tokens,
                    "output_tokens": e.output_tokens,
                    "total_tokens": e.total_tokens,
                    "cost_usd": e.cost_usd,
                    "created_at": e.created_at.isoformat(),
                }
                for e in entries
            ]

            return CostBreakdown(
                run_id=run_id,
                run_name="",
                total_cost_usd=total_cost,
                entries=entries_data,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
            )

    async def record_trend(
        self,
        run_id: UUID = None,
        provider: str = "",
        model: str = "",
        category: CostCategory = CostCategory.LLM_INFERENCE,
        cost_usd: float = 0.0,
        token_count: int = 0,
    ) -> None:
        async with get_async_session() as session:
            trend = CostTrendModel(
                id=uuid4(),
                date=datetime.utcnow(),
                cost_usd=cost_usd,
                token_count=0,
                request_count=1,
                run_id=run_id,
                provider=provider,
                model=model,
                category=category.value,
            )
            session.add(trend)
            await session.commit()
