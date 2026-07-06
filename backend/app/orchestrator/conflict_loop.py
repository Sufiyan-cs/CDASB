"""
Conflict Loop Engine – The heart of CDASB.

Implements the universal conflict resolution mechanism used across all phases:
  Generator -> Critic -> (if rejected) Optimizer -> Judge -> repeat

This module is phase-agnostic. It takes a generator agent, runs the output through
the Critic-Optimizer-Judge cycle, and streams events via a callback.
"""
from __future__ import annotations
import json
import asyncio
from typing import Callable, Awaitable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from app.agents.personas.critic import CriticAgent
from app.agents.personas.optimizer import OptimizerAgent
from app.agents.personas.judge import JudgeAgent
from app.config import get_settings

settings = get_settings()


class ConflictPhase(str, Enum):
    PLANNING = "planning"
    CODING = "coding"
    TESTING = "testing"


class EventType(str, Enum):
    PHASE_START = "phase_start"
    GENERATOR_START = "generator_start"
    GENERATOR_DONE = "generator_done"
    CRITIC_START = "critic_start"
    CRITIC_DONE = "critic_done"
    OPTIMIZER_START = "optimizer_start"
    OPTIMIZER_DONE = "optimizer_done"
    JUDGE_START = "judge_start"
    JUDGE_DONE = "judge_done"
    ROUND_COMPLETE = "round_complete"
    CONFLICT_RESOLVED = "conflict_resolved"
    CONFLICT_FAILED = "conflict_failed"
    TOKEN_STREAM = "token_stream"


@dataclass
class ConflictEvent:
    event_type: EventType
    phase: str
    round_number: int
    agent: str = ""
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d


# Type alias for the callback that streams events to WebSocket
EventCallback = Callable[[ConflictEvent], Awaitable[None]]


class ConflictLoop:
    """
    Runs the universal conflict loop for any phase.

    Usage:
        loop = ConflictLoop(phase="planning", on_event=ws_send)
        result = await loop.run(generator_agent, prompt, context)
    """

    def __init__(
        self,
        phase: str,
        on_event: EventCallback | None = None,
        max_rounds: int | None = None,
        critic_persona: str | None = None,
        critic_agent=None,
        optimizer_agent=None,
        judge_agent=None,
    ):
        self.phase = phase
        self.on_event = on_event or self._noop
        self.max_rounds = max_rounds or settings.max_conflict_rounds
        self.critic = critic_agent or CriticAgent(persona_override=critic_persona)
        self.optimizer = optimizer_agent or OptimizerAgent()
        self.judge = judge_agent or JudgeAgent()
        self.history: list[dict] = []

    @staticmethod
    async def _noop(event: ConflictEvent):
        pass

    async def _emit(self, event_type: EventType, round_num: int, agent: str = "", data: dict | None = None):
        event = ConflictEvent(
            event_type=event_type,
            phase=self.phase,
            round_number=round_num,
            agent=agent,
            data=data or {},
        )
        await self.on_event(event)

    def _make_token_cb(self, round_num: int):
        """Create a token streaming callback for an agent call."""
        async def _cb(payload: dict):
            await self._emit(
                EventType.TOKEN_STREAM, round_num,
                agent=payload.get("agent", ""),
                data=payload,
            )
        return _cb

    async def run(self, generator_agent, prompt: str, context: str = "") -> dict:
        """
        Execute the full conflict loop.

        Returns:
            {
                "final_output": str,
                "rounds": int,
                "approved": bool,
                "history": [...]
            }
        """
        await self._emit(EventType.PHASE_START, 0, data={"phase": self.phase})

        # Step 1: Generator produces initial output
        await self._emit(EventType.GENERATOR_START, 1, agent=generator_agent.name)
        current_output = await generator_agent.run_stream(prompt, context, on_token=self._make_token_cb(1))
        await self._emit(
            EventType.GENERATOR_DONE, 1,
            agent=generator_agent.name,
            data={"output_preview": current_output[:500], "full_output": current_output}
        )

        # Step 2: Conflict rounds
        for round_num in range(1, self.max_rounds + 1):
            round_record = {"round": round_num}

            # --- Critic ---
            await self._emit(EventType.CRITIC_START, round_num, agent="Critic")
            critic_prompt = (
                f"Review the following {self.phase} output and provide your critique.\n\n"
                f"--- OUTPUT TO REVIEW ---\n{current_output}\n--- END ---"
            )
            critic_response = await self.critic.run_stream(critic_prompt, on_token=self._make_token_cb(round_num))
            await self._emit(
                EventType.CRITIC_DONE, round_num,
                agent="Critic",
                data={"output_preview": critic_response[:500], "full_output": critic_response}
            )
            round_record["critic"] = critic_response

            # Parse critic verdict
            critic_data = self._safe_parse(critic_response)
            verdict = critic_data.get("verdict", "rejected")

            if verdict == "approved":
                await self._emit(
                    EventType.CONFLICT_RESOLVED, round_num,
                    data={"message": f"Critic approved on round {round_num}"}
                )
                round_record["verdict"] = "approved"
                self.history.append(round_record)
                return {
                    "final_output": current_output,
                    "rounds": round_num,
                    "approved": True,
                    "history": self.history,
                }

            # --- Optimizer ---
            await self._emit(EventType.OPTIMIZER_START, round_num, agent="Optimizer")
            # Truncate inputs to prevent timeout on large outputs, but keep it huge for planning
            max_out_len = 20000 if self.phase == "planning" else 5000
            truncated_output = current_output[:max_out_len] + ("\n...[truncated]" if len(current_output) > max_out_len else "")
            truncated_critic = critic_response[:3000] + ("\n...[truncated]" if len(critic_response) > 3000 else "")
            optimizer_prompt = (
                f"Improve the following {self.phase} output based on the critic's feedback. Be concise and direct.\n\n"
                f"--- ORIGINAL OUTPUT ---\n{truncated_output}\n--- END ---\n\n"
                f"--- CRITIC FEEDBACK ---\n{truncated_critic}\n--- END ---"
            )
            optimizer_response = await self.optimizer.run_stream(optimizer_prompt, on_token=self._make_token_cb(round_num))
            await self._emit(
                EventType.OPTIMIZER_DONE, round_num,
                agent="Optimizer",
                data={"output_preview": optimizer_response[:500], "full_output": optimizer_response}
            )
            round_record["optimizer"] = optimizer_response

            if self.phase == "planning":
                # Planning Optimizer rewrites the FULL markdown document directly
                improved = optimizer_response
            else:
                # Apply SEARCH/REPLACE diffs if the optimizer used that format for code
                improved = self._apply_diffs(current_output, optimizer_response)

            # --- Judge ---
            await self._emit(EventType.JUDGE_START, round_num, agent="Judge")
            # Truncate: Judge only needs critic issues + optimizer summary, not full files
            judge_critic = critic_response[:1500] + ("\n...[truncated]" if len(critic_response) > 1500 else "")
            judge_improved_preview = improved[:1500] + ("\n...[truncated]" if len(improved) > 1500 else "")
            judge_prompt = (
                f"Evaluate whether the optimizer adequately fixed the critic's issues.\n\n"
                f"--- CRITIC ISSUES ---\n{judge_critic}\n--- END ---\n\n"
                f"--- IMPROVED VERSION (preview) ---\n{judge_improved_preview}\n--- END ---"
            )
            judge_response = await self.judge.run_stream(judge_prompt, on_token=self._make_token_cb(round_num))
            await self._emit(
                EventType.JUDGE_DONE, round_num,
                agent="Judge",
                data={"output_preview": judge_response[:500], "full_output": judge_response}
            )
            round_record["judge"] = judge_response

            judge_data = self._safe_parse(judge_response)
            judge_verdict = judge_data.get("verdict", "rejected")
            round_record["verdict"] = judge_verdict

            self.history.append(round_record)
            await self._emit(
                EventType.ROUND_COMPLETE, round_num,
                data={"verdict": judge_verdict, "quality_score": judge_data.get("quality_score", 0)}
            )

            if judge_verdict == "approved":
                await self._emit(
                    EventType.CONFLICT_RESOLVED, round_num,
                    data={"message": f"Judge approved on round {round_num}"}
                )
                return {
                    "final_output": improved,
                    "rounds": round_num,
                    "approved": True,
                    "history": self.history,
                }

            # Use improved version as input for next round
            current_output = improved if isinstance(improved, str) else json.dumps(improved)

        # Max rounds exhausted
        await self._emit(
            EventType.CONFLICT_FAILED, self.max_rounds,
            data={"message": f"Max conflict rounds ({self.max_rounds}) reached without resolution"}
        )
        return {
            "final_output": current_output,
            "rounds": self.max_rounds,
            "approved": False,
            "history": self.history,
        }

    async def run_file(self, file_path: str, physical_content: str, builder_prompt: str) -> dict:
        """
        Execute the conflict loop tailored strictly to raw physical file content.
        This strips JSON wrappers and iterates solely on raw code.
        """
        await self._emit(EventType.PHASE_START, 0, data={"phase": self.phase})
        
        current_content = physical_content
        
        # Step 2: Conflict rounds
        for round_num in range(1, self.max_rounds + 1):
            round_record = {"round": round_num}

            # --- Critic ---
            await self._emit(EventType.CRITIC_START, round_num, agent="Critic")
            critic_prompt = (
                f"Review the following physical file ({file_path}) and provide your critique.\n"
                f"Focus on strict syntax, correctness, and clean logic.\n\n"
                f"--- {file_path} CONTENT ---\n{current_content}\n--- END ---"
            )
            critic_response = await self.critic.run_stream(critic_prompt, on_token=self._make_token_cb(round_num))
            await self._emit(
                EventType.CRITIC_DONE, round_num,
                agent="Critic",
                data={"output_preview": critic_response[:500], "full_output": critic_response}
            )
            round_record["critic"] = critic_response

            critic_data = self._safe_parse(critic_response)
            verdict = critic_data.get("verdict", "rejected")

            if verdict == "approved":
                await self._emit(EventType.CONFLICT_RESOLVED, round_num, data={"message": f"Critic approved on round {round_num}"})
                round_record["verdict"] = "approved"
                self.history.append(round_record)
                return {"final_output": current_content, "rounds": round_num, "approved": True, "history": self.history}

            # --- Optimizer ---
            await self._emit(EventType.OPTIMIZER_START, round_num, agent="Optimizer")
            truncated_critic = critic_response[:2000] + ("\n...[truncated]" if len(critic_response) > 2000 else "")
            optimizer_prompt = (
                f"Fix the issues in the following code based on critic feedback.\n\n"
                f"--- ORIGINAL {file_path} ---\n{current_content}\n--- END ---\n\n"
                f"--- CRITIC FEEDBACK ---\n{truncated_critic}\n--- END ---"
            )
            optimizer_response = await self.optimizer.run_stream(optimizer_prompt, on_token=self._make_token_cb(round_num))
            
            # Apply SEARCH/REPLACE diffs from optimizer
            improved = self._apply_diffs(current_content, optimizer_response)

            await self._emit(
                EventType.OPTIMIZER_DONE, round_num,
                agent="Optimizer",
                data={"output_preview": improved[:500], "full_output": improved}
            )
            round_record["optimizer"] = improved

            # --- Judge ---
            await self._emit(EventType.JUDGE_START, round_num, agent="Judge")
            judge_critic = critic_response[:1500] + ("\n...[truncated]" if len(critic_response) > 1500 else "")
            judge_improved_preview = improved[:1500] + ("\n...[truncated]" if len(improved) > 1500 else "")
            judge_prompt = (
                f"Evaluate whether the optimizer adequately fixed the critic's issues.\n\n"
                f"--- CRITIC ISSUES ---\n{judge_critic}\n--- END ---\n\n"
                f"--- IMPROVED VERSION (preview) ---\n{judge_improved_preview}\n--- END ---"
            )
            judge_response = await self.judge.run_stream(judge_prompt, on_token=self._make_token_cb(round_num))
            await self._emit(
                EventType.JUDGE_DONE, round_num,
                agent="Judge",
                data={"output_preview": judge_response[:500], "full_output": judge_response}
            )
            round_record["judge"] = judge_response

            judge_data = self._safe_parse(judge_response)
            judge_verdict = judge_data.get("verdict", "rejected")
            round_record["verdict"] = judge_verdict

            self.history.append(round_record)
            await self._emit(EventType.ROUND_COMPLETE, round_num, data={"verdict": judge_verdict, "quality_score": judge_data.get("quality_score", 0)})

            if judge_verdict == "approved":
                await self._emit(EventType.CONFLICT_RESOLVED, round_num, data={"message": f"Judge approved on round {round_num}"})
                return {"final_output": improved, "rounds": round_num, "approved": True, "history": self.history}

            current_content = improved

        await self._emit(EventType.CONFLICT_FAILED, self.max_rounds, data={"message": "Max conflict rounds reached."})
        return {"final_output": current_content, "rounds": self.max_rounds, "approved": False, "history": self.history}

    @staticmethod
    def _apply_diffs(original: str, optimizer_response: str) -> str:
        """
        Apply SEARCH/REPLACE diff blocks from the optimizer to the original content.
        Falls back to raw replacement if no diff blocks are found.
        
        Format expected:
            <<<< SEARCH
            original lines
            ====
            replacement lines
            >>>> REPLACE
        """
        import re

        # Check for NO_CHANGES_NEEDED
        if "NO_CHANGES_NEEDED" in optimizer_response:
            return original

        # Extract SEARCH/REPLACE blocks
        diff_pattern = re.compile(
            r"<<<<\s*SEARCH\s*\n(.*?)\n====\n(.*?)\n>>>>\s*REPLACE",
            re.DOTALL
        )
        diffs = diff_pattern.findall(optimizer_response)

        if diffs:
            result = original
            applied = 0
            for search_block, replace_block in diffs:
                search_text = search_block.strip()
                replace_text = replace_block.strip()
                if search_text in result:
                    result = result.replace(search_text, replace_text, 1)
                    applied += 1
                else:
                    # Fuzzy match: ignore all leading/trailing whitespace variations per line
                    lines = [re.escape(line.strip()) for line in search_text.split('\n') if line.strip()]
                    if lines:
                        # Allow any amount of whitespace (including newlines) between lines
                        pattern = r'\s*'.join(lines)
                        match = re.search(pattern, result)
                        if match:
                            result = result[:match.start()] + "\n" + replace_text + "\n" + result[match.end():]
                            applied += 1
            # If we applied at least one diff, return the result
            if applied > 0:
                return result
            # If none matched (LLM hallucinated the search blocks or whitespace mismatch),
            # DO NOT fall through! Returning the raw diffs would corrupt the file.
            return original

        # Fallback: check if response contains markdown code blocks
        all_blocks = re.findall(r"```[a-z]*\n(.*?)```", optimizer_response, re.DOTALL)
        if all_blocks:
            # Check if output contains chunk separators
            if "=== FILE:" in optimizer_response:
                # Preserve chunk structure, strip outermost fence
                result = optimizer_response.strip()
                result = re.sub(r"^```[a-z]*\n", "", result)
                result = re.sub(r"\n```\s*$", "", result)
                return result
            else:
                return "\n\n".join(block.strip() for block in all_blocks)

        # Final fallback: treat entire response as the improved content
        return optimizer_response.strip()

    @staticmethod
    def _safe_parse(text: str) -> dict:
        """Attempt to parse JSON from agent response."""
        import re
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1).strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {"raw_text": text}
