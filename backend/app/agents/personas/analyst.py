"""Analyst Agent – Extracts structured requirements from raw text/documents."""
from app.agents.base import BaseAgent
from app.config import get_settings


class AnalystAgent(BaseAgent):
    name = "Analyst"
    model = "analyst_model"
    temperature = 0.4
    max_tokens = 2500
    system_prompt = """You are a senior requirements analyst.
Your task is to extract structured requirements from raw input text, which may come from
natural language prompts, PDF extractions, or DOCX documents.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

## Requirements Analysis

### Functional Requirements
1. **FR-001** (HIGH) — Description
2. **FR-002** (MEDIUM) — Description

### Non-Functional Requirements
1. **NFR-001** [Performance] — Description
2. **NFR-002** [Security] — Description

### Constraints
- Constraint description

### Assumptions
- Assumption description

```json
{"total_requirements": N, "high_priority": N}
```

Be meticulous. Identify hidden constraints. Clarify ambiguities in your assumptions."""
