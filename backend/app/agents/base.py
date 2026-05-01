"""Base Agent class – wraps the OpenAI-compatible NVIDIA NIM API."""
from __future__ import annotations
import json
import re
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()

client = AsyncOpenAI(
    base_url=settings.nvidia_base_url,
    api_key=settings.nvidia_api_key,
    timeout=600.0,
)


class BaseAgent:
    """
    A thin wrapper around the NVIDIA NIM chat completions endpoint.
    Each persona subclass sets its own system_prompt and default model.
    """

    name: str = "BaseAgent"
    system_prompt: str = "You are a helpful AI assistant."
    model: str = settings.planner_model
    temperature: float = 0.6
    max_tokens: int = 8192

    async def run(self, user_message: str, context: str = "") -> str:
        """Send a single prompt and return the assistant's text response."""
        system_msg = self.system_prompt + "\n\nCRITICAL: Do not overthink. Keep your reasoning brief and extremely concise."
        messages = [{"role": "system", "content": system_msg}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": user_message})

        import openai
        import asyncio
        # Direct API call - timeout is controlled by the client-level config (300s)
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens
        response = await client.chat.completions.create(**kwargs)

        msg = response.choices[0].message
        raw = msg.content or ""
        # 1. Strip properly closed reasoning blocks
        import re
        raw = re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL | re.IGNORECASE)
        
        # 2. Handle malformed closing tags
        if "</think>" in raw.lower():
            # Just split and take the last part
            parts = re.split(r"</think>\s*", raw, flags=re.IGNORECASE)
            raw = parts[-1]
            
        # 3. Handle models (like Kimi) that frequently open <think> but forget to close it
        if "<think>" in raw.lower():
            # Look for where the actual markdown output starts (e.g. ## Verdict or ```json)
            # This skips over the trailing thought stream.
            match = re.search(r"(##\s+|```(?:json|python|html|js|css)?|#+\s+[Vv]erdict|<<<<\s*SEARCH)", raw, re.IGNORECASE)
            if match:
                raw = raw[match.start():] # Keep everything from the header onwards
            else:
                # If we can't find a clean breakpoint, just physically delete the <think> tag
                # so it doesn't break JSON parsing, even if the thought text remains.
                raw = re.sub(r"<think>\s*", "", raw, flags=re.IGNORECASE)

        cleaned = raw.strip()
        
        # 4. If the API returns reasoning in a separate field but the main content was empty
        if not cleaned and getattr(msg, "reasoning_content", None):
            reasoning = msg.reasoning_content.strip()
            # Still strip tags from it natively just in case
            reasoning = re.sub(r"</?think>", "", reasoning, flags=re.IGNORECASE).strip()
            return reasoning

        return cleaned

    async def run_json(self, user_message: str, context: str = "") -> dict:
        """Same as run() but attempts to parse the response as JSON."""
        text = await self.run(user_message, context)
        # Try to extract JSON from markdown code fences
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text}
