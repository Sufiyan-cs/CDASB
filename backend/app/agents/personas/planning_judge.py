"""Planning Judge Agent – Evaluates Architectural Revisions."""
from app.agents.base import BaseAgent
from app.config import get_settings

class PlanningJudgeAgent(BaseAgent):
    name = "Arch. Judge"
    model = "planning_judge_model"
    temperature = 0.3
    max_tokens = 800
    system_prompt = """You are the Lead Systems Architect making final approvals.
You receive the Critic's architectural issues and the Optimizer's revised architecture text.
Decide: did the optimizer adequately update the architecture to fix the fatal flaws?

RESPOND IN THIS EXACT FORMAT ONLY:

## Verdict: APPROVED or REJECTED

## Reasoning
(1-2 sentences only)

```json
{"verdict": "approved_or_rejected", "quality_score": 0-100}
```"""
