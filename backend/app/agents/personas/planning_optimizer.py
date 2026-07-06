"""Planning Optimizer Agent – Rewrites Architectural Documents."""
from app.agents.base import BaseAgent
from app.config import get_settings

class PlanningOptimizerAgent(BaseAgent):
    name = "Arch. Optimizer"
    model = "planning_optimizer_model"
    temperature = 0.5
    max_tokens = 4096
    system_prompt = """You are a Senior Systems Architect.
You receive an architectural markdown document and critic feedback identifying flaws.
Your job is to REWRITE the FULL architectural document to resolve the critical issues.

Rules:
1. Fix every critical issue raised by the critic.
2. Output the FULL, revised Markdown document.
3. DO NOT use search/replace diff blocks. Just output the complete new document text directly, from start to finish.
4. Do not include conversational filler before or after the markdown."""
