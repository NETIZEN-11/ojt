import asyncio
import re

from app.core.config import get_settings
from app.domain.enums import Verdict
from app.domain.value_objects import EvidenceItem, MatcherConfig
from app.evaluation.matchers.base import BaseMatcher

settings = get_settings()


class RegexMatcher(BaseMatcher):
    # Dangerous regex patterns that can cause catastrophic backtracking
    DANGEROUS_PATTERNS = [
        r'\(.*\)\+',  # (x+)+
        r'\(.*\)\*',  # (x*)*
        r'\(.*\)\{',  # (x+){n,m}
        r'\([^\)]*\+[^\)]*\)\+',  # Nested quantifiers
    ]
    
    def _validate_pattern_safety(self, pattern: str) -> None:
        """Check for potentially dangerous regex patterns."""
        import re
        for dangerous in self.DANGEROUS_PATTERNS:
            if re.search(dangerous, pattern):
                raise ValueError(
                    f"Regex pattern contains potentially dangerous construct: {dangerous}. "
                    "Nested quantifiers can cause ReDoS (Regular Expression Denial of Service)."
                )
    
    async def match(
        self, response: str, config: MatcherConfig | None
    ) -> tuple[Verdict, float, list[EvidenceItem]]:
        if not config or not config.pattern:
            return (
                Verdict.INCONCLUSIVE,
                0.0,
                [self._create_evidence("regex_matcher", "No pattern configured", False)],
            )

        # SECURITY: Validate pattern for ReDoS risks
        try:
            self._validate_pattern_safety(config.pattern)
        except ValueError as e:
            return (
                Verdict.INCONCLUSIVE,
                0.0,
                [self._create_evidence("regex_matcher", f"Unsafe pattern rejected: {e}", False)],
            )

        try:
            # Add timeout to compilation as well
            pattern = await asyncio.wait_for(
                asyncio.to_thread(re.compile, config.pattern),
                timeout=1.0  # 1 second max for compilation
            )
        except asyncio.TimeoutError:
            return (
                Verdict.INCONCLUSIVE,
                0.0,
                [self._create_evidence("regex_matcher", "Regex compilation timeout", False)],
            )
        except re.error as e:
            return (
                Verdict.INCONCLUSIVE,
                0.0,
                [self._create_evidence("regex_matcher", f"Invalid regex: {e}", False)],
            )

        try:
            match = await asyncio.wait_for(
                asyncio.to_thread(pattern.search, response),
                timeout=config.regex_timeout_ms / 1000
                if config.regex_timeout_ms
                else settings.REGEX_MATCH_TIMEOUT_MS / 1000,
            )
        except TimeoutError:
            return (
                Verdict.INCONCLUSIVE,
                0.0,
                [
                    self._create_evidence(
                        "regex_matcher",
                        f"Regex timeout after {config.regex_timeout_ms or settings.REGEX_MATCH_TIMEOUT_MS}ms",
                        False,
                    )
                ],
            )

        matched = match is not None

        return (
            Verdict.PASS if matched else Verdict.FAIL,
            1.0 if matched else 0.0,
            [
                self._create_evidence("regex_matcher", f"Pattern: {config.pattern}", matched),
                self._create_evidence(
                    "regex_matcher", f"Match: {match.group() if match else 'None'}", matched
                ),
                self._create_evidence(
                    "regex_matcher", f"Response preview: {response[:500]}", matched
                ),
            ],
        )
