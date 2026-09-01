from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from app.domain.value_objects import LLMRubric, JudgeOutput, EvidenceItem


class BaseJudge(ABC):
    @abstractmethod
    async def judge(
        self,
        test_input: str,
        response: str,
        rubric: Optional[LLMRubric],
    ) -> JudgeOutput:
        pass