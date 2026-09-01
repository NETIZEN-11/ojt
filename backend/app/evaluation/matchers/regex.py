import re
import asyncio
from typing import List, Tuple, Optional
from app.domain.enums import Verdict
from app.domain.value_objects import MatcherConfig, EvidenceItem
from app.evaluation.matchers.base import BaseMatcher
from app.core.config import get_settings

settings = get_settings()


class RegexMatcher(BaseMatcher):
    async def match(
        self, response: str, config: Optional[MatcherConfig]
    ) -> Tuple[Verdict, float, List[EvidenceItem]]:
        if not config or not config.pattern:
            return Verdict.INCONCLUSIVE, 0.0, [
                self._create_evidence("regex_matcher", "No pattern configured", False)
            ]

        try:
            pattern = re.compile(config.pattern)
        except re.error as e:
            return Verdict.INCONCLUSIVE, 0.0, [
                self._create_evidence("regex_matcher", f"Invalid regex: {e}", False)
            ]

        try:
            match = await asyncio.wait_for(
                asyncio.to_thread(pattern.search, response),
                timeout=config.regex_timeout_ms / 1000 if config.regex_timeout_ms else settings.REGEX_MATCH_TIMEOUT_MS / 1000,
            )
        except asyncio.TimeoutError:
            return Verdict.INCONCLUSIVE, 0.0, [
                self._create_evidence("regex_matcher", f"Regex timeout after {config.regex_timeout_ms or settings.REGEX_MATCH_TIMEOUT_MS}ms", False)
            ]

        matched = match is not None

        return (
            Verdict.PASS if matched else Verdict.FAIL,
            1.0 if matched else 0.0,
            [
                self._create_evidence("regex_matcher", f"Pattern: {config.pattern}", matched),
                self._create_evidence("regex_matcher", f"Match: {match.group() if match else 'None'}", matched),
                self._create_evidence("regex_matcher", f"Response preview: {response[:500]}", matched),
            ],
        )