"""Base Agent class – wraps the OpenAI-compatible NVIDIA NIM API."""
from __future__ import annotations
import json
import re
import time
from typing import AsyncIterator, Callable, Awaitable
from openai import AsyncOpenAI
from app.config import get_settings

_client_cache: dict[float, AsyncOpenAI] = {}  # timeout -> client
_client_key: str | None = None  # track which API key the client was built with

def _get_client(timeout: float = 120.0) -> AsyncOpenAI:
    """Return an OpenAI client with the specified timeout, re-creating if API key changed."""
    global _client_cache, _client_key
    s = get_settings()
    # If the API key changed, invalidate all cached clients
    if _client_key != s.nvidia_api_key:
        _client_cache.clear()
        _client_key = s.nvidia_api_key
    # Return or create a client for this timeout value
    if timeout not in _client_cache:
        _client_cache[timeout] = AsyncOpenAI(
            base_url=s.nvidia_base_url,
            api_key=s.nvidia_api_key,
            timeout=timeout,
        )
    return _client_cache[timeout]


MAX_RETRIES = 3


class BaseAgent:
    """
    A thin wrapper around the NVIDIA NIM chat completions endpoint.
    Each persona subclass sets its own system_prompt and default model.
    
    NOTE: `model` is the *config key name* (e.g. 'planner_model').
    At runtime we resolve it to the actual model string via get_settings().
    For backward compat, if it looks like a model ID (contains '/'), we use it directly.
    """

    name: str = "BaseAgent"
    system_prompt: str = "You are a helpful AI assistant."
    model: str = "planner_model"  # config key, resolved at runtime
    temperature: float = 0.6
    max_tokens: int = 8192

    def _resolve_model(self) -> str:
        """Resolve the model string dynamically from current settings."""
        m = self.model
        # If it already looks like a model ID (e.g. 'meta/llama-3.3-70b'), use it directly
        if '/' in m:
            return m
        # Otherwise treat it as a config key name and look it up
        s = get_settings()
        return getattr(s, m, m)

    def _get_timeout(self) -> float:
        """Pick a timeout based on expected response size."""
        if self.max_tokens and self.max_tokens <= 256:
            return 60.0   # Small responses (Gatekeeper, Judge): 60s
        elif self.max_tokens and self.max_tokens <= 2048:
            return 120.0  # Medium responses: 2 min
        else:
            return 180.0  # Large generation (Builder, Planner): 3 min

    async def run(self, user_message: str, context: str = "") -> str:
        """Send a single prompt and return the assistant's text response."""
        system_msg = self.system_prompt + "\n\nCRITICAL: Do not overthink. Keep your reasoning brief and extremely concise."
        messages = [{"role": "system", "content": system_msg}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": user_message})

        import openai
        import asyncio
        kwargs = dict(
            model=self._resolve_model(),
            messages=messages,
            temperature=self.temperature,
        )
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens

        timeout = self._get_timeout()
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await _get_client(timeout).chat.completions.create(**kwargs)
                break
            except (openai.APIError, openai.APITimeoutError, openai.APIConnectionError) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt  # 2s, 4s
                    print(f"[{self.name}] API error (attempt {attempt}/{MAX_RETRIES}): {exc}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise last_exc

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

    async def run_stream(
        self,
        user_message: str,
        context: str = "",
        on_token: Callable[[dict], Awaitable[None]] | None = None,
    ) -> str:
        """
        Stream tokens from the LLM one-by-one.
        Calls on_token(payload) for each chunk so the pipeline can
        relay it to the WebSocket in real-time.
        Returns the full accumulated text (cleaned) when done.
        """
        system_msg = self.system_prompt + "\n\nCRITICAL: Do not overthink. Keep your reasoning brief and extremely concise."
        messages = [{"role": "system", "content": system_msg}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": user_message})

        kwargs = dict(
            model=self._resolve_model(),
            messages=messages,
            temperature=self.temperature,
            stream=True,
        )
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens

        import openai
        import asyncio
        timeout = self._get_timeout()
        last_exc = None
        stream = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                stream = await _get_client(timeout).chat.completions.create(**kwargs)
                break
            except (openai.APIError, openai.APITimeoutError, openai.APIConnectionError) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    print(f"[{self.name}] Stream API error (attempt {attempt}/{MAX_RETRIES}): {exc}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise last_exc

        accumulated = ""
        token_count = 0
        start_time = time.time()
        last_emit = 0.0  # throttle: emit at most every 150ms

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                accumulated += delta.content
                token_count += 1

                now = time.time()
                if on_token and (now - last_emit >= 0.15):
                    last_emit = now
                    await on_token({
                        "token_count": token_count,
                        "elapsed": round(now - start_time, 1),
                        "preview": accumulated[-120:],  # last 120 chars
                        "agent": self.name,
                    })

        # Final emit with complete stats
        if on_token:
            await on_token({
                "token_count": token_count,
                "elapsed": round(time.time() - start_time, 1),
                "preview": accumulated[-200:],
                "agent": self.name,
                "done": True,
            })

        # Apply the same <think> cleanup as run()
        raw = accumulated
        raw = re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL | re.IGNORECASE)
        if "</think>" in raw.lower():
            parts = re.split(r"</think>\s*", raw, flags=re.IGNORECASE)
            raw = parts[-1]
        if "<think>" in raw.lower():
            match = re.search(r"(##\s+|```(?:json|python|html|js|css)?|#+\s+[Vv]erdict|<<<<\s*SEARCH)", raw, re.IGNORECASE)
            if match:
                raw = raw[match.start():]
            else:
                raw = re.sub(r"<think>\s*", "", raw, flags=re.IGNORECASE)

        return raw.strip()

    async def run_json(
        self,
        user_message: str,
        context: str = "",
        on_token: Callable[[dict], Awaitable[None]] | None = None,
    ) -> dict:
        """Same as run() but attempts to parse the response as JSON.
        Optionally streams tokens via on_token callback.
        """
        if on_token:
            text = await self.run_stream(user_message, context, on_token=on_token)
        else:
            text = await self.run(user_message, context)
        # Try to extract JSON from markdown code fences
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text}

    async def run_async_generator(self, user_message: str, context: str = "") -> AsyncIterator[str]:
        """
        Yields tokens one by one as they arrive from the LLM.
        Useful for FastAPI StreamingResponse (Server-Sent Events).
        """
        system_msg = self.system_prompt + "\n\nCRITICAL: Do not overthink. Keep your reasoning brief and extremely concise."
        messages = [{"role": "system", "content": system_msg}]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": user_message})

        kwargs = dict(
            model=self._resolve_model(),
            messages=messages,
            temperature=self.temperature,
            stream=True,
        )
        if self.max_tokens is not None:
            kwargs["max_tokens"] = self.max_tokens

        import openai
        import asyncio
        timeout = self._get_timeout()
        last_exc = None
        stream = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                stream = await _get_client(timeout).chat.completions.create(**kwargs)
                break
            except (openai.APIError, openai.APITimeoutError, openai.APIConnectionError) as exc:
                last_exc = exc
                if attempt < MAX_RETRIES:
                    wait = 2 ** attempt
                    print(f"[{self.name}] AsyncGen API error (attempt {attempt}/{MAX_RETRIES}): {exc}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise last_exc

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content
