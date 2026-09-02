from abc import ABC, abstractmethod

from app.domain.value_objects import JudgeOutput, LLMRubric


class BaseJudge(ABC):
    @abstractmethod
    async def judge(
        self,
        test_input: str,
        response: str,
        rubric: LLMRubric | None,
    ) -> JudgeOutput:
        pass
