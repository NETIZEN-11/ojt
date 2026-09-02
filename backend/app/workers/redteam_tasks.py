import asyncio
from uuid import UUID

from celery import shared_task

from app.core.config import get_settings
from app.core.database import get_async_session
from app.core.logging import get_logger
from app.redteam.agent import RedTeamAgent
from app.redteam.generator import AdversarialGenerator
from app.redteam.planner import AttackPlanner
from app.repositories.agents import TargetAgentRepository

settings = get_settings()
logger = get_logger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def run_redteam_attack(self, target_agent_id: str, strategy: dict = None):
    agent_uuid = UUID(target_agent_id)
    logger.info("redteam_task_started", target_agent_id=target_agent_id)

    async def _run():
        async with get_async_session() as session:
            agent_repo = TargetAgentRepository(session)
            agent = await agent_repo.get(agent_uuid)
            if not agent:
                logger.error("target_agent_not_found", target_agent_id=target_agent_id)
                return None

            redteam_agent = RedTeamAgent(
                target_agent_url=agent.endpoint_url,
                target_agent_headers=agent.auth_config.get("headers", {}),
            )

            from app.redteam.agent import AttackStrategy
            attack_strategy = AttackStrategy(**(strategy or {}))

            result = await redteam_agent.run(attack_strategy)
            logger.info("redteam_task_completed", target_agent_id=target_agent_id, verdict=result.final_verdict)
            return {"verdict": result.final_verdict.value if result.final_verdict else None}

    return asyncio.run(_run())


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_adversarial_tests(self, categories: list = None, count: int = 10):
    logger.info("adversarial_generation_started", categories=categories, count=count)

    async def _run():
        generator = AdversarialGenerator()
        from app.domain.enums import TestCaseCategory
        category_enums = [TestCaseCategory(c) for c in (categories or [])]
        candidates = await generator.generate_candidates(category_enums, count)
        logger.info("adversarial_generation_completed", generated=len(candidates))
        return candidates

    return asyncio.run(_run())


@shared_task
def plan_attack_strategy(objective: str, target_context: dict = None):
    logger.info("attack_planning_started", objective=objective)

    async def _run():
        planner = AttackPlanner()
        plan = await planner.plan_attack(objective, target_context or {})
        logger.info("attack_planning_completed", strategy=plan.get("strategy"))
        return plan

    return asyncio.run(_run())
