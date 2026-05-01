"""
Native Sandbox Executor – Runs generated code locally using subprocess.

Creates isolated workspace directories, writes files, runs commands,
and captures stdout/stderr with timeouts.
"""
from __future__ import annotations
import asyncio
import os
import shutil
from pathlib import Path
from dataclasses import dataclass

from app.config import get_settings

settings = get_settings()


@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    success: bool

    def to_dict(self) -> dict:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "success": self.success,
        }


class NativeExecutor:
    """
    Manages workspace creation, file writing, and command execution
    for generated projects.
    """

    def __init__(self, project_id: int):
        self.project_id = project_id
        self.workspace_root = Path(settings.workspace_dir).resolve()
        self.project_dir = self.workspace_root / f"project_{project_id}"

    def setup_workspace(self):
        """Create the project workspace directory."""
        self.project_dir.mkdir(parents=True, exist_ok=True)
        return str(self.project_dir)

    def write_files(self, files: list[dict]):
        """
        Write generated files to the workspace (synchronous).

        Args:
            files: List of {"path": "relative/path", "content": "...", "language": "..."}
        """
        for file_info in files:
            rel_path = file_info["path"]
            content = file_info["content"]
            full_path = self.project_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

    async def write_files_async(self, files: list[dict]):
        """
        Write generated files to the workspace without blocking the async event loop.
        Uses asyncio.to_thread to offload synchronous I/O.
        """
        await asyncio.to_thread(self.write_files, files)

    def read_file(self, rel_path: str) -> str:
        """Read a file from the workspace."""
        full_path = self.project_dir / rel_path
        if full_path.exists():
            return full_path.read_text(encoding="utf-8")
        return ""

    async def execute_command(
        self, command: str, timeout: int = 300, cwd: str | None = None
    ) -> ExecutionResult:
        """
        Execute a shell command in the project workspace.

        Args:
            command: The command to run (e.g., "pip install -r requirements.txt")
            timeout: Max seconds before killing the process
            cwd: Working directory override (defaults to project_dir)
        """
        work_dir = cwd or str(self.project_dir)

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return ExecutionResult(
                    exit_code=-1,
                    stdout="",
                    stderr=f"Command timed out after {timeout} seconds",
                    success=False,
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = process.returncode or 0

            return ExecutionResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                success=exit_code == 0,
            )

        except Exception as e:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                success=False,
            )

    async def run_setup(self, commands: list[str]) -> list[ExecutionResult]:
        """Run a sequence of setup commands (e.g., pip install, npm install)."""
        results = []
        for cmd in commands:
            result = await self.execute_command(cmd)
            results.append(result)
            if not result.success:
                break  # Stop on first failure
        return results

    async def run_project(self, run_command: str) -> ExecutionResult:
        """Execute the project's main run command."""
        return await self.execute_command(run_command, timeout=60)

    def cleanup(self):
        """Remove the workspace directory."""
        if self.project_dir.exists():
            shutil.rmtree(self.project_dir, ignore_errors=True)

    def list_files(self) -> list[str]:
        """List all files in the workspace."""
        if not self.project_dir.exists():
            return []
        return [
            str(p.relative_to(self.project_dir))
            for p in self.project_dir.rglob("*")
            if p.is_file()
        ]
