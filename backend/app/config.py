"""Application configuration loaded from environment variables."""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # NVIDIA / OpenAI-compatible API/m
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Models - NVIDIA hosted (most powerful available)
    gatekeeper_model: str = "meta/llama-3.3-70b-instruct"
    planner_model: str = "openai/gpt-oss-120b"
    coder_model: str = "minimaxai/minimax-m2.7"
    critic_model: str = "z-ai/glm-5.1"
    judge_model: str = "meta/llama-3.3-70b-instruct"
    analyst_model: str = "mistralai/mistral-large-3-675b-instruct-2512"
    optimizer_model: str = "z-ai/glm-5.1"
    simple_planner_model: str = "meta/llama-3.3-70b-instruct"
    documenter_model: str = "minimaxai/minimax-m2.7"
    
    # Models - Planning Phase Overrides
    planning_critic_model: str = "z-ai/glm-5.1"
    planning_optimizer_model: str = "openai/gpt-oss-120b"
    planning_judge_model: str = "meta/llama-3.3-70b-instruct"

    # Database
    database_url: str = "sqlite+aiosqlite:///./cdasb.db"

    # App
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True

    # Workspace
    workspace_dir: str = "./workspaces"

    # Conflict loop
    max_conflict_rounds: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
