from abc import ABC, abstractmethod
from typing import List, Tuple
from app.domain.enums import Verdict
from app.domain.value_objects import MatcherConfig, EvidenceItem


class BaseMatcher(ABC):
    @abstractmethod
    async def match(
        self, response: str, config: Optional[MatcherConfig]
    ) -> Tuple[Verdict, float, List[EvidenceItem]]:
        pass

    def _create_evidence(self, source: str, text: str, matched: bool = True) -> EvidenceItem:
        return EvidenceItem(
            source=source,
            text=text,
            metadata={"matched": matched}
        )