
from app.domain.enums import Verdict
from app.domain.value_objects import EvidenceItem, MatcherConfig
from app.evaluation.matchers.base import BaseMatcher


class KeywordMatcher(BaseMatcher):
    async def match(
        self, response: str, config: Optional[MatcherConfig]
    ) -> tuple[Verdict, float, list[EvidenceItem]]:
        if not config or not config.keywords:
            return Verdict.INCONCLUSIVE, 0.0, [
                self._create_evidence("keyword_matcher", "No keywords configured", False)
            ]

        response_lower = response.lower()
        matched_keywords = []
        missing_keywords = []

        for keyword in config.keywords:
            kw_lower = keyword.lower()
            if kw_lower in response_lower:
                matched_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)

        matched = len(missing_keywords) == 0
        confidence = len(matched_keywords) / len(config.keywords) if config.keywords else 0.0

        evidence = [
            self._create_evidence("keyword_matcher", f"Matched keywords: {', '.join(matched_keywords) or 'None'}", matched),
            self._create_evidence("keyword_matcher", f"Missing keywords: {', '.join(missing_keywords) or 'None'}", matched),
            self._create_evidence("keyword_matcher", f"Response preview: {response[:500]}", matched),
        ]

        return Verdict.PASS if matched else Verdict.FAIL, confidence, evidence
