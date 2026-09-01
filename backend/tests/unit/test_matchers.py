import pytest
from app.evaluation.matchers.exact import ExactMatcher
from app.evaluation.matchers.regex import RegexMatcher
from app.evaluation.matchers.keyword import KeywordMatcher
from app.evaluation.matchers.refusal import RefusalMatcher
from app.domain.enums import Verdict
from app.domain.value_objects import MatcherConfig


@pytest.mark.asyncio
async def test_exact_match_case_insensitive():
    matcher = ExactMatcher()
    config = MatcherConfig(pattern="Hello World", case_sensitive=False)
    
    verdict, confidence, evidence = await matcher.match("hello world", config)
    
    assert verdict == Verdict.PASS
    assert confidence == 1.0
    assert len(evidence) == 2


@pytest.mark.asyncio
async def test_exact_match_case_sensitive():
    matcher = ExactMatcher()
    config = MatcherConfig(pattern="Hello World", case_sensitive=True)
    
    verdict, confidence, evidence = await matcher.match("hello world", config)
    
    assert verdict == Verdict.FAIL
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_exact_match_no_config():
    matcher = ExactMatcher()
    
    verdict, confidence, evidence = await matcher.match("anything", None)
    
    assert verdict == Verdict.INCONCLUSIVE
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_regex_match_valid():
    matcher = RegexMatcher()
    config = MatcherConfig(pattern=r"\d{3}-\d{2}-\d{4}")
    
    verdict, confidence, evidence = await matcher.match("SSN: 123-45-6789", config)
    
    assert verdict == Verdict.PASS
    assert confidence == 1.0


@pytest.mark.asyncio
async def test_regex_match_invalid():
    matcher = RegexMatcher()
    config = MatcherConfig(pattern=r"\d{3}-\d{2}-\d{4}")
    
    verdict, confidence, evidence = await matcher.match("No SSN here", config)
    
    assert verdict == Verdict.FAIL
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_regex_match_invalid_pattern():
    matcher = RegexMatcher()
    config = MatcherConfig.model_construct(pattern=r"[invalid")
    
    verdict, confidence, evidence = await matcher.match("test", config)
    
    assert verdict == Verdict.INCONCLUSIVE
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_keyword_match_all_present():
    matcher = KeywordMatcher()
    config = MatcherConfig(keywords=["hello", "world"], case_sensitive=False)
    
    verdict, confidence, evidence = await matcher.match("Hello world!", config)
    
    assert verdict == Verdict.PASS
    assert confidence == 1.0


@pytest.mark.asyncio
async def test_keyword_match_missing():
    matcher = KeywordMatcher()
    config = MatcherConfig(keywords=["hello", "world", "missing"], case_sensitive=False)
    
    verdict, confidence, evidence = await matcher.match("Hello world!", config)
    
    assert verdict == Verdict.FAIL
    assert confidence == 2/3  # 2 out of 3 matched


@pytest.mark.asyncio
async def test_keyword_match_no_keywords():
    matcher = KeywordMatcher()
    config = MatcherConfig(keywords=[])
    
    verdict, confidence, evidence = await matcher.match("test", config)
    
    assert verdict == Verdict.INCONCLUSIVE


@pytest.mark.asyncio
async def test_refusal_match_detected():
    matcher = RefusalMatcher()
    config = MatcherConfig()
    
    verdict, confidence, evidence = await matcher.match("I cannot help with that request.", config)
    
    assert verdict == Verdict.PASS
    assert confidence == 0.9


@pytest.mark.asyncio
async def test_refusal_match_not_detected():
    matcher = RefusalMatcher()
    config = MatcherConfig()
    
    verdict, confidence, evidence = await matcher.match("Here is the information you requested.", config)
    
    assert verdict == Verdict.FAIL
    assert confidence == 0.5