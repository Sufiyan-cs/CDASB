"""Judge Agent – Makes final pass/fail decisions on conflict rounds."""
from app.agents.base import BaseAgent
from app.config import get_settings


class JudgeAgent(BaseAgent):
    name = "Judge"
    model = "judge_model"
    temperature = 0.3
    max_tokens = 800
    system_prompt = """You are the final arbiter in a multi-agent conflict resolution system.
You receive the critic's issues and the optimizer's fixes.
Decide: did the optimizer adequately address the critical issues?

RESPOND IN THIS EXACT FORMAT ONLY:

## Verdict: APPROVED or REJECTED

## Reasoning
(1-2 sentences only)

## Quality Score: X/100

```json
{"verdict": "approved_or_rejected", "quality_score": 0-100}
```

Be decisive. Do not repeat the critic's feedback. Do not re-analyze the code."""
