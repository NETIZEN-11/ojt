
from app.core.config import get_settings
from app.domain.enums import Verdict
from app.domain.value_objects import EvidenceItem, MatcherConfig
from app.evaluation.matchers.base import BaseMatcher

settings = get_settings()


class ExactMatcher(BaseMatcher):
    async def match(
        self, response: str, config: Optional[MatcherConfig]
    ) -> tuple[Verdict, float, list[EvidenceItem]]:
        if not config or not config.pattern:
            return Verdict.INCONCLUSIVE, 0.0, [
                self._create_evidence("exact_matcher", "No pattern configured", False)
            ]

        expected = config.pattern
        case_sensitive = config.case_sensitive or settings.EXACT_MATCH_CASE_SENSITIVE

        if not case_sensitive:
            response_cmp = response.lower()
            expected_cmp = expected.lower()
        else:
            response_cmp = response
            expected_cmp = expected

        matched = response_cmp == expected_cmp

        return (
            Verdict.PASS if matched else Verdict.FAIL,
            1.0 if matched else 0.0,
            [
                self._create_evidence("exact_matcher", f"Expected: {expected}", matched),
                self._create_evidence("exact_matcher", f"Actual: {response[:500]}", matched),
            ],
        )
