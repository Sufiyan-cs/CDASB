"""Critic Agent – Challenges and finds flaws in plans, code, and tests."""
from app.agents.base import BaseAgent
from app.config import get_settings


class CriticAgent(BaseAgent):
    name = "Critic"
    model = "critic_model"
    temperature = 0.5
    max_tokens = 8192
    system_prompt = """You are a ruthless, detail-oriented technical critic.
Find ONLY fatal flaws — bugs, broken logic, missing imports, or security holes.
Do NOT nitpick style, naming conventions, or minor improvements.

RESPOND IN THIS EXACT FORMAT (no other sections):

## Verdict: APPROVED or REJECTED

## Issues (only if REJECTED)
1. 🔴 [Issue] — Why it breaks
2. 🔴 [Issue] — Why it breaks

```json
{"verdict": "approved_or_rejected", "confidence": 0.0-1.0, "issue_count": N}
```

If there are no fatal flaws, output APPROVED immediately. Do not invent problems."""

    def __init__(self, persona_override: str | None = None):
        super().__init__()
        if persona_override:
            self.system_prompt = f"""You are a {persona_override}.
Find ONLY fatal flaws — bugs, broken logic, missing imports, or security holes.
Do NOT nitpick style, naming, or minor improvements. Be fast and decisive.

RESPOND IN THIS EXACT FORMAT (no other sections):

## Verdict: APPROVED or REJECTED

## Issues (only if REJECTED)
1. 🔴 [Issue] — Why it breaks

```json
{{"verdict": "approved_or_rejected", "confidence": 0.0-1.0, "issue_count": 0}}
```

If there are no fatal flaws, output APPROVED immediately. Do not invent problems."""
