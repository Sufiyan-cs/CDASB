"""Task Decomposer Agent – Breaks down a plan into iteration chunks."""
from app.agents.base import BaseAgent
from app.config import get_settings


class TaskDecomposerAgent(BaseAgent):
    name = "TaskDecomposer"
    model = "planner_model"
    temperature = 0.2
    max_tokens = 4096
    system_prompt = """You are an expert Technical Project Manager.
Your job is to read an architecture plan and decompose it into an execution sequence.

Rules:
1. Break down the entire project into individual files to be generated.
2. Ensure the order respects dependencies strictly (e.g., build the database schema file BEFORE the API routes file).
3. If the project is COMPLEX, ensure you prefix the description with its feature group (e.g. "Database: Auth schema").
4. Output strict JSON only. No markdown formatting.

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

```json
{
  "chunks": [
    {"type": "file", "name": "schema.py", "description": "Database models and connections"},
    {"type": "file", "name": "auth.py", "description": "Authentication endpoints relying on schema"}
  ]
}
```
"""
