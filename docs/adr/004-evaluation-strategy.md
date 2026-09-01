# ADR 004: Evaluation Strategy

## Status
Accepted

## Context
The framework evaluates AI agent responses against expected behaviors. We need a strategy that:
- Prioritizes deterministic evaluation where possible
- Uses LLMs only for open-ended rubrics
- Provides structured, validated judge output
- Supports double-scoring for reliability
- Handles judge failures gracefully
- Produces evidence-rich results
- Enables regression detection

## Decision
Implement a **Tiered Evaluation Pipeline** with deterministic-first approach:

```
Test Case
    ↓
Expected Behavior Type
    ↓
┌─────────────────────────────────────┐
│  Deterministic Matchers (Tier 1)    │
│  Exact, Regex, Keyword, Refusal     │
│  → No LLM call, 100% reliable       │
└─────────────────────────────────────┘
    ↓ (if no matcher or LLM_RUBRIC)
┌─────────────────────────────────────┐
│  LLM Judge (Tier 2)                 │
│  Structured output + schema validation│
│  Retry once on schema error         │
│  Double-score with fallback judge   │
│  Disagreement → INCONCLUSIVE        │
└─────────────────────────────────────┘
    ↓
Final Verdict: PASS | FAIL | INCONCLUSIVE
```

## Matcher Types (Tier 1 - Deterministic)

| Matcher | Use Case | Config |
|---------|----------|--------|
| **Exact Match** | Fixed responses, structured output | `pattern`, `case_sensitive` |
| **Regex Match** | Pattern validation, format checking | `pattern`, `timeout_ms` |
| **Keyword Match** | Required terms present | `keywords[]`, `case_sensitive` |
| **Refusal** | Safety refusals, "I cannot" | Built-in patterns |
| **Structured Output** | JSON schema validation | `expected_keys[]`, `required_fields[]` |

### Matcher Guarantees
- **No LLM calls**: Pure string/regex operations
- **Deterministic**: Same input → same output always
- **Fast**: Sub-millisecond execution
- **Auditable**: Clear evidence (matched text, pattern)
- **Configurable**: Timeout, case sensitivity, etc.

## LLM Judge (Tier 2 - Probabilistic)

### When Used
- Expected behavior type = `LLM_RUBRIC`
- Complex semantic evaluation needed
- No deterministic matcher can express the criteria

### Judge Output Contract (Strict Schema)

```json
{
  "verdict": "PASS | FAIL | INCONCLUSIVE",
  "confidence": 0.0-1.0,
  "rationale": "string (required, non-empty)",
  "evidence": [
    {"source": "target_response", "text": "string"}
  ],
  "criteria_results": [
    {"criterion": "string", "passed": true, "evidence": "string", "confidence": 0.0-1.0}
  ],
  "metadata": {
    "tokens_used": 0,
    "estimated_cost": 0.0,
    "provider": "openai",
    "model": "gpt-4o-2024-08-06"
  }
}
```

### Validation Rules
1. `verdict` ∈ {PASS, FAIL, INCONCLUSIVE}
2. `confidence` ∈ [0.0, 1.0]
3. `rationale` non-empty string
4. `evidence` non-empty array for PASS/FAIL
5. `criteria_results` consistent with verdict
6. Retry once on schema validation failure
7. Escalate to INCONCLUSIVE after failed retry

### Double Scoring
```
Primary Judge (Tier 2)
    ↓ (validate schema)
    ↓ (confidence ≥ threshold?)
Secondary Judge (Fallback)
    ↓ (validate schema)
Compare Verdicts:
    SAME → Final Verdict
    DIFFERENT → INCONCLUSIVE (human review required)
```

### Fallback Chain
```
Primary Judge (OpenAI GPT-4o)
    ↓ (timeout/error/schema fail)
Secondary Judge (Anthropic Claude)
    ↓ (timeout/error/schema fail)
Mock Judge (Deterministic)
    ↓ (always succeeds)
INCONCLUSIVE
```

## Rubric Structure

```python
class LLMRubricCriterion:
    name: str              # "Factual Accuracy"
    description: str       # "Response contains no hallucinated facts"
    weight: float          # 0.0-1.0, relative importance
    pass_threshold: float  # 0.0-1.0, minimum score to pass

class LLMRubric:
    criteria: List[LLMRubricCriterion]
    overall_threshold: float  # 0.0-1.0, weighted average to pass
    require_evidence: bool    # Evidence required for PASS/FAIL
```

## Scoring Algorithm

```python
def score_with_rubric(response: str, rubric: LLMRubric) -> JudgeOutput:
    # 1. Build prompt with rubric
    prompt = build_judge_prompt(test_input, response, rubric)
    
    # 2. Call primary judge
    primary = call_llm(prompt, temperature=0.0, json_schema=JudgeOutput)
    validate_schema(primary)
    
    # 3. Double-score if enabled
    if settings.JUDGE_DOUBLE_SCORE:
        secondary = call_fallback_judge(prompt)
        validate_schema(secondary)
        
        if primary.verdict != secondary.verdict:
            return JudgeOutput(
                verdict=Verdict.INCONCLUSIVE,
                confidence=min(primary.confidence, secondary.confidence),
                rationale="Judge disagreement",
                evidence=primary.evidence + secondary.evidence,
            )
    
    return primary
```

## Evidence Requirements

### For PASS/FAIL
- At least one evidence item required
- Source must be `target_response` or `test_input`
- Text must be relevant excerpt (not full response)

### For INCONCLUSIVE
- Evidence optional but encouraged
- Rationale must explain uncertainty

### Evidence Format
```python
{
    "source": "target_response",
    "text": "Relevant excerpt from response",
    "metadata": {"matched": true, "position": 42}
}
```

## Regression Detection

### Deterministic Comparison
```python
# By test_case_id (immutable)
baseline_verdict = baseline_items[test_case_id].verdict
current_verdict = results[test_case_id].verdict

if baseline_verdict != current_verdict:
    regression_type = classify_transition(baseline_verdict, current_verdict)
    severity = classify_severity(regression_type, test_case_category)
    create_regression_finding(...)
```

### Transition Types
| Previous → Current | Type | Base Severity |
|-------------------|------|---------------|
| PASS → FAIL | PASS_TO_FAIL | HIGH |
| PASS → INCONCLUSIVE | PASS_TO_INCONCLUSIVE | MEDIUM |
| FAIL → FAIL | FAIL_TO_FAIL | LOW |
| FAIL → PASS | FAIL_TO_PASS | LOW |
| INCONCLUSIVE → FAIL | INCONCLUSIVE_TO_FAIL | MEDIUM |
| New test case | NEW_FAILURE | MEDIUM |

### Critical Severity Overrides
Deterministic rules override LLM classification:
- PII leakage → CRITICAL
- Severe safety failure → CRITICAL
- Critical jailbreak → CRITICAL
- Security boundary bypass → CRITICAL

## CI Gate Logic

```python
def evaluate_gate(regressions: List[Regression], inconclusive: int, infra_fail: bool = False):
    if infra_fail:
        return GateResult(decision=FAIL, exit_code=2)
    
    critical = count(regressions, severity=CRITICAL)
    high = count(regressions, severity=HIGH)
    medium = count(regressions, severity=MEDIUM)
    low = count(regressions, severity=LOW)
    
    if critical > 0:
        return GateResult(decision=BLOCK, exit_code=1)
    elif high > 0:
        return GateResult(decision=BLOCK, exit_code=1)
    elif medium > 0:
        return GateResult(decision=WARN, exit_code=0)
    elif low > 0:
        return GateResult(decision=WARN, exit_code=0)
    elif inconclusive > 0:
        return GateResult(decision=FAIL, exit_code=1)  # Fail closed
    else:
        return GateResult(decision=PASS, exit_code=0)
```

### Exit Codes
- `0` = PASS/WARN (gate passes)
- `1` = BLOCK/FAIL (regression or inconclusive)
- `2` = Infrastructure failure

## Cost Controls

| Operation | Target | Limit |
|-----------|--------|-------|
| Standard test | < $0.05 | $0.10 |
| PR evaluation | < $5 | $10 |
| Full adversarial sweep | < $50 | $100 |
| Daily total | - | Configurable |

## Configuration

```bash
# Judge
JUDGE_TEMPERATURE=0.0
JUDGE_MAX_TOKENS=2048
JUDGE_CONFIDENCE_THRESHOLD=0.7
JUDGE_DOUBLE_SCORE=true
JUDGE_RETRY_ON_SCHEMA_ERROR=true

# Matchers
EXACT_MATCH_CASE_SENSITIVE=false
REGEX_MATCH_TIMEOUT_MS=1000

# Regression
REGRESSION_DETECTION_ENABLED=true
SEVERITY_CRITICAL_OVERRIDE=true

# Gate
GATE_CRITICAL_ACTION=block
GATE_HIGH_ACTION=block
GATE_MEDIUM_ACTION=warn
GATE_LOW_ACTION=warn
GATE_INCONCLUSIVE_ACTION=fail
GATE_INFRA_FAILURE_ACTION=fail
```

## Consequences

### Positive
- **Deterministic where possible**: 80%+ of tests use Tier 1 matchers
- **Structured output**: No free-text parsing, schema validation
- **Double scoring**: Catches judge errors, flags disagreement
- **Fail-closed**: Infrastructure failures, disagreements → INCONCLUSIVE → FAIL
- **Evidence-rich**: Every verdict has supporting evidence
- **Cost-aware**: Tier 1 free, Tier 2 controlled

### Negative
- **LLM latency**: Tier 2 adds 2-8s per test
- **Judge costs**: API calls for open-ended evaluation
- **Schema maintenance**: Judge output schema must be versioned
- **Prompt engineering**: Rubric quality affects results

## Implementation Notes

### Prompt Versioning
- System/user prompts stored as versioned files
- `backend/app/prompts/judge/v1/system.txt`
- Promoted via API, tracked in `prompt_versions` table

### Model Pinning
- Never use "latest" model identifiers
- Explicit versions: `gpt-4o-2024-08-06`, `claude-3-5-sonnet-20241022`
- Tracked in `model_versions` on each run

### Observability
- Metrics: judge latency, token usage, cost, schema error rate
- Logs: structured, correlation IDs, no sensitive content
- Traces: full evaluation pipeline with OpenTelemetry