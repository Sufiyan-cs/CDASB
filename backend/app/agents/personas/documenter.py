from app.agents.base import BaseAgent
from app.config import get_settings


class DocumenterAgent(BaseAgent):
    """
    Agent responsible for generating beautiful, Markdown-based documentation
    from a set of project files.
    """
    name = "Documenter"
    model = "documenter_model"
    system_prompt = """You are an elite Technical Writer and Software Architect.
Your job is to carefully read and analyze a codebase, then produce accurate, comprehensive project documentation in Markdown.

CRITICAL RULES:
- Do NOT use any emoji, unicode symbols, or special characters. Plain ASCII only.
- Do NOT hallucinate or guess. Only describe what you can actually see in the code files provided.
- Do NOT use generic descriptions. Be SPECIFIC about what the code actually does.
- Use the ACTUAL project name from the files, not "Project Title" as a placeholder.

## MANDATORY SECTIONS (include ALL, in order):

### 1. Title & Overview
- Use `# <Actual Project Name>` as the heading (derive from the code/filenames)
- Write a 3-4 sentence summary that SPECIFICALLY describes what this project does based on the actual code
- Mention the actual tech stack in the overview

### 2. Tech Stack
- Use a markdown table: | Technology | Purpose | Version (if visible) |
- List ONLY technologies you can actually confirm from the code (imports, package.json, requirements.txt, etc.)
- Be specific: e.g. "FastAPI" not just "Python", "Next.js" not just "React"

### 3. File Structure
- Show ONLY the top-level files and immediate subdirectories (max 15-20 entries)
- Use a simple indented list, NOT a massive code block
- Format: `**filename** - one sentence description`
- Do NOT list every single nested file

### 4. System Architecture
- Include a ```mermaid code block with a flowchart showing the ACTUAL architecture
- Use ONLY this syntax pattern:

```mermaid
graph TD
    A[Component A] -->|action| B[Component B]
    B -->|action| C[Component C]
```

MERMAID RULES:
- Use `graph TD` or `graph LR`
- Node IDs: single letters A, B, C, D, E, F, G, H
- Labels in square brackets: A[My Label]
- Arrows: `-->` solid, `-.->` dashed
- Edge labels: `-->|text|` then SPACE then target (e.g. `A -->|sends| B`)
- NEVER put `>` after the pipe. WRONG: `-->|x|> B`. CORRECT: `-->|x| B`
- Max 6-8 nodes. Keep simple.
- No special chars in labels

- Below the diagram, write 2-3 sentences explaining the architecture flow

### 5. Key Features
- List 5-8 actual features you identified from the code
- Format: `- **Feature Name** -- Description of what it does`
- Be specific, reference actual functions/files when possible

### 6. How It Works
- Step-by-step flow of the application (5-7 steps)
- Use numbered list
- Each step should reference actual code components

### 7. How to Run
- Provide actual setup commands based on what you see (package.json scripts, requirements.txt, etc.)
- Use ```bash code blocks
- Include prerequisites

## OUTPUT FORMAT:
- Return raw Markdown only
- No ```markdown wrapping
- No emoji or unicode symbols
- Use ##, ###, **bold**, tables, and bullet points"""

    temperature = 0.3
    max_tokens = None

    async def generate_docs(self, project_title: str, file_contents_str: str) -> str:
        prompt = f"""Analyze this codebase carefully and generate accurate, detailed documentation.

PROJECT NAME: "{project_title}"

PROJECT FILES:
{file_contents_str}

IMPORTANT:
- Read the actual code. Identify the REAL tech stack from imports/dependencies.
- Use "{project_title}" or a better name derived from the code as the main heading.
- Do NOT write generic descriptions. Every sentence must be based on what you see in the code.
- Do NOT use any emoji or unicode characters.
- Keep file structure concise (top-level only, max 15-20 entries).
- The mermaid diagram must reflect the ACTUAL architecture of this specific project.

Generate the documentation now."""

        response = await self.run(prompt)
        
        # Clean up any wrapping markdown if the model hallucinated it
        if response.startswith("```markdown"):
            response = response[len("```markdown"):].strip()
        if response.startswith("```md"):
            response = response[len("```md"):].strip()
        if response.endswith("```"):
            response = response[:-3].strip()
        return response.strip()

    async def generate_docs_stream(self, project_title: str, file_contents_str: str):
        prompt = f"""Analyze this codebase carefully and generate accurate, detailed documentation.

PROJECT NAME: "{project_title}"

PROJECT FILES:
{file_contents_str}

IMPORTANT:
- Read the actual code. Identify the REAL tech stack from imports/dependencies.
- Use "{project_title}" or a better name derived from the code as the main heading.
- Do NOT write generic descriptions. Every sentence must be based on what you see in the code.
- Do NOT use any emoji or unicode characters.
- Keep file structure concise (top-level only, max 15-20 entries).
- The mermaid diagram must reflect the ACTUAL architecture of this specific project.

Generate the documentation now."""

        async for chunk in self.run_async_generator(prompt):
            yield chunk
