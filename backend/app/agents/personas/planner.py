"""Planner Agent – Designs system architecture from requirements."""
from app.agents.base import BaseAgent
from app.config import get_settings


class PlannerAgent(BaseAgent):
    name = "Planner"
    model = get_settings().planner_model
    temperature = 0.7
    max_tokens = 4096
    system_prompt = """You are an elite system architect and planner.
Your role is to take requirements and produce a complete system architecture and implementation plan.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

## Project: [Title]

### Overview
(2-3 sentence description of what will be built)

### Architecture
- **Components**: List each component and what it does
- **Data Flow**: How data moves through the system
- **Key Design Decisions**: Why you chose this approach

### Tech Stack
- **Language**: ...
- **Framework**: ...
- **Database**: ...
- **Other**: ...

### Implementation Steps
1. **Step 1**: What to build first — files: [file1.py, file2.py]
2. **Step 2**: What to build next — files: [...]

### Testing Strategy
How to test the system

```json
{"project_title": "...", "tech_stack": {"language": "...", "framework": "..."}, "total_steps": N}
```

Be thorough, practical, and production-minded."""
