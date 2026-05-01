"""
CDASB Backend – FastAPI application entry point.

Provides REST endpoints for project management and WebSocket
for real-time conflict loop streaming.
"""
from __future__ import annotations
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database.models import init_db, async_session, Project, ProjectStatus, ConflictRound, ExecutionLog
from app.services.document_processor import process_uploaded_file
from app.orchestrator.pipeline import PipelineOrchestrator
import os

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="CDASB – Conflict-Driven Autonomous System Builder",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────────────────────────── REST ENDPOINTS ──────────────────────────


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "CDASB"}


@app.post("/api/projects")
async def create_project(
    prompt: str = Form(default=None),
    file: UploadFile | None = File(default=None),
):
    """Create a new project from a prompt or uploaded document."""
    if not prompt and not file:
        raise HTTPException(400, "Provide a prompt or upload a file.")

    input_text = prompt or ""

    # Process uploaded file
    if file:
        file_bytes = await file.read()
        extracted = process_uploaded_file(file.filename or "unknown", file_bytes)
        input_text = f"{input_text}\n\n--- DOCUMENT CONTENT ---\n{extracted}" if input_text else extracted

    # Create project record
    async with async_session() as session:
        project = Project(
            title=input_text[:100].strip(),
            original_input=input_text,
            status=ProjectStatus.CREATED,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        project_id = project.id

    return JSONResponse({
        "project_id": project_id,
        "status": "created",
        "message": "Project created. Connect to WebSocket to start planning.",
    })


@app.get("/api/projects")
async def list_projects():
    """List all projects, newest first."""
    from sqlalchemy import select
    async with async_session() as session:
        result = await session.execute(
            select(Project).order_by(Project.id.desc())
        )
        projects = result.scalars().all()
        return [
            {
                "id": p.id,
                "title": p.title,
                "status": p.status.value,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in projects
        ]


@app.get("/api/projects/{project_id}")
async def get_project(project_id: int):
    """Get project details."""
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        return {
            "id": project.id,
            "title": project.title,
            "status": project.status.value,
            "final_plan": project.final_plan,
            "parsed_requirements": project.parsed_requirements,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        }


@app.post("/api/projects/{project_id}/approve")
async def approve_project(project_id: int):
    """Approve the plan and allow execution to begin."""
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        if project.status != ProjectStatus.AWAITING_APPROVAL:
            raise HTTPException(400, f"Project is in '{project.status.value}' state, not awaiting approval.")
        # Status will be updated when execution starts via WebSocket
        return {"status": "approved", "message": "Connect to WebSocket to start execution."}


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: int):
    """Delete a project and its workspace."""
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        
        # Delete related records
        from sqlalchemy import delete as sa_delete
        await session.execute(sa_delete(ConflictRound).where(ConflictRound.project_id == project_id))
        await session.execute(sa_delete(ExecutionLog).where(ExecutionLog.project_id == project_id))
        await session.delete(project)
        await session.commit()

    # Clean up workspace files
    import shutil
    workspace_path = os.path.join(settings.workspace_dir, f"project_{project_id}")
    if os.path.exists(workspace_path):
        shutil.rmtree(workspace_path, ignore_errors=True)

    return {"status": "deleted", "message": f"Project {project_id} deleted."}


# ────────────────────────── WEBSOCKET ──────────────────────────


class ConnectionManager:
    """Manages active WebSocket connections per project."""

    def __init__(self):
        self.connections: dict[int, list[WebSocket]] = {}

    async def connect(self, project_id: int, ws: WebSocket):
        await ws.accept()
        self.connections.setdefault(project_id, []).append(ws)

    def disconnect(self, project_id: int, ws: WebSocket):
        if project_id in self.connections:
            self.connections[project_id] = [
                c for c in self.connections[project_id] if c != ws
            ]

    async def broadcast(self, project_id: int, data: dict):
        dead = []
        for ws in self.connections.get(project_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        # Clean up dead connections
        for ws in dead:
            self.disconnect(project_id, ws)


manager = ConnectionManager()

# ── Global state: event buffer & task tracker ──
# Events are buffered per project so reconnecting clients get the full feed.
# Tasks are tracked globally so they survive WebSocket disconnects.
_project_events: dict[int, list[dict]] = {}
_project_tasks: dict[int, asyncio.Task] = {}


async def _buffered_send(project_id: int, data: dict):
    """Buffer an event AND broadcast it to all connected clients."""
    _project_events.setdefault(project_id, []).append(data)
    # Cap buffer to prevent unbounded growth
    if len(_project_events[project_id]) > 500:
        _project_events[project_id] = _project_events[project_id][-500:]
    await manager.broadcast(project_id, data)


@app.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    """
    WebSocket endpoint for real-time project interaction.

    Client sends commands:
      {"action": "start_planning"}
      {"action": "approve"}
      {"action": "start_execution"}
      {"action": "ping"}  -- keepalive heartbeat
    
    Server streams conflict events and status updates.
    
    ARCHITECTURE:
    - Background tasks (planning, execution) are GLOBAL per project, not per connection.
    - Events are buffered globally so reconnecting clients get the full feed.
    - Disconnecting does NOT cancel background tasks.
    """
    await manager.connect(project_id, websocket)

    async def send_event(data: dict):
        """Buffer + broadcast. Used by orchestrator callbacks AND background tasks."""
        await _buffered_send(project_id, data)

    try:
        # ── Send initial status from DB ──
        async with async_session() as session:
            project = await session.get(Project, project_id)
            if not project:
                await websocket.send_json({"type": "error", "message": "Project not found"})
                return
            await websocket.send_json({
                "type": "connected",
                "project_id": project_id,
                "status": project.status.value.lower(),
                "title": project.title,
                "plan": project.final_plan.get("final_output", "") if project.final_plan else "",
                "rounds": project.final_plan.get("rounds", 0) if project.final_plan else 0,
                "completed_files": project.completed_files or [],
                "has_plan": bool(project.final_plan and project.final_plan.get("final_output")),
            })

        # ── Replay buffered events so reconnecting clients get the full feed ──
        for event in _project_events.get(project_id, []):
            try:
                await websocket.send_json({**event, "replayed": True})
            except Exception:
                break

        orchestrator = PipelineOrchestrator(project_id, on_event=send_event)

        # ── Background task wrappers ──
        # These use send_event() (buffer + broadcast) instead of websocket.send_json()
        # so they survive WebSocket disconnects.

        async def _run_planning_bg(user_input: str):
            """Run planning in background, send result when done."""
            try:
                plan_result = await orchestrator.run_planning(user_input)
                await send_event({
                    "type": "awaiting_approval",
                    "plan": plan_result["final_output"][:5000],
                    "rounds": plan_result["rounds"],
                })
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                import traceback
                traceback.print_exc()
                try:
                    await send_event({"type": "error", "message": str(exc)})
                except Exception:
                    pass

        async def _run_execution_bg(plan_text: str):
            """Run execution in background, send result when done."""
            try:
                result = await orchestrator.run_execution(plan_text)
                await send_event({
                    "type": "execution_complete",
                    "workspace": result.get("workspace", ""),
                    "files": result.get("files", []),
                })
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                import traceback
                traceback.print_exc()
                try:
                    await send_event({"type": "error", "message": str(exc)})
                except Exception:
                    pass

        # ── Main message loop (stays responsive for pings) ──

        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            action = msg.get("action", "")

            # ── Keepalive ping/pong ──
            if action == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if action == "start_planning":
                # Check if there's already a running task for this project
                existing = _project_tasks.get(project_id)
                if existing and not existing.done():
                    await websocket.send_json({"type": "info", "message": "Planning already in progress."})
                    continue

                # Fetch project input
                async with async_session() as session:
                    project = await session.get(Project, project_id)
                    if not project:
                        await websocket.send_json({"type": "error", "message": "Project not found"})
                        continue
                    
                    # [RESUMPTION SHORT-CIRCUIT]
                    if project.final_plan and project.final_plan.get("final_output"):
                        project.status = ProjectStatus.AWAITING_APPROVAL
                        await session.commit()
                        await websocket.send_json({
                            "type": "awaiting_approval",
                            "plan": project.final_plan.get("final_output", ""),
                            "rounds": project.final_plan.get("rounds", 0),
                        })
                        continue

                    user_input = project.original_input
                    project.status = ProjectStatus.PLANNING
                    await session.commit()

                # Clear event buffer for new planning session
                _project_events[project_id] = []
                task = asyncio.create_task(_run_planning_bg(user_input))
                _project_tasks[project_id] = task

            elif action == "approve":
                async with async_session() as session:
                    project = await session.get(Project, project_id)
                    if not project or not project.final_plan:
                        await websocket.send_json({"type": "error", "message": "No plan to approve"})
                        continue

                await websocket.send_json({
                    "type": "approved",
                    "message": "Plan approved. Send 'start_execution' to begin building.",
                })

            elif action == "start_execution":
                # Check if there's already a running task for this project
                existing = _project_tasks.get(project_id)
                if existing and not existing.done():
                    await websocket.send_json({"type": "error", "message": "Already executing. Ignored duplicate request."})
                    continue

                async with async_session() as session:
                    project = await session.get(Project, project_id)
                    if not project or not project.final_plan:
                        await websocket.send_json({"type": "error", "message": "No approved plan"})
                        continue

                    plan_text = json.dumps(project.final_plan)
                    project.status = ProjectStatus.EXECUTING
                    await session.commit()

                # Don't clear buffer — keep planning events for context
                task = asyncio.create_task(_run_execution_bg(plan_text))
                _project_tasks[project_id] = task

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        # *** DO NOT cancel background tasks — let them run to completion ***
        manager.disconnect(project_id, websocket)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # *** DO NOT cancel background tasks ***
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        manager.disconnect(project_id, websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
