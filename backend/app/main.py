"""
CDASB Backend – FastAPI application entry point.

Provides REST endpoints for project management and WebSocket
for real-time conflict loop streaming.
"""
from __future__ import annotations
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import get_db

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


from pydantic import BaseModel
import dotenv

class SettingsUpdate(BaseModel):
    models: dict[str, str] = {}
    max_conflict_rounds: int | None = None

# Known model fields (must match the field names in Settings class)
VALID_MODEL_KEYS = {
    'gatekeeper_model', 'planner_model', 'coder_model', 'critic_model',
    'judge_model', 'analyst_model', 'optimizer_model', 'simple_planner_model',
    'documenter_model', 'planning_critic_model', 'planning_optimizer_model',
    'planning_judge_model',
}

@app.put("/api/settings")
async def update_settings(update: SettingsUpdate):
    """Update backend AI models and limits in .env (no server restart)."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    # Ensure .env exists
    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            pass

    # Write each model override to .env (uppercase key format)
    for key, value in update.models.items():
        if key not in VALID_MODEL_KEYS:
            continue
        dotenv.set_key(env_path, key.upper(), value, quote_mode="never")

    # Write max_conflict_rounds
    if update.max_conflict_rounds is not None:
        dotenv.set_key(env_path, "MAX_CONFLICT_ROUNDS", str(update.max_conflict_rounds), quote_mode="never")

    # Clear the cached settings so the next pipeline run picks up changes
    from app.config import get_settings
    get_settings.cache_clear()

    return {"status": "success", "message": ".env updated — no restart needed"}


class EnvSettingsUpdate(BaseModel):
    nvidia_api_key: str | None = None
    workspace_dir: str | None = None

@app.put("/api/settings/env")
async def update_env_settings(update: EnvSettingsUpdate):
    """Update API key and workspace path in .env."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    if not os.path.exists(env_path):
        with open(env_path, "w") as f:
            pass

    if update.nvidia_api_key is not None and update.nvidia_api_key.strip():
        dotenv.set_key(env_path, "NVIDIA_API_KEY", update.nvidia_api_key.strip(), quote_mode="never")

    if update.workspace_dir is not None and update.workspace_dir.strip():
        dotenv.set_key(env_path, "WORKSPACE_DIR", update.workspace_dir.strip(), quote_mode="never")

    # Clear cached settings
    from app.config import get_settings
    get_settings.cache_clear()

    return {"status": "success", "message": "Environment settings updated"}

@app.post("/api/projects")
async def create_project(
    prompt: str = Form(default=None),
    file: UploadFile | None = File(default=None),
    owner_email: str = Form(default=None),
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
            owner_email=owner_email,
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
async def list_projects(owner: str | None = None):
    """List projects, optionally filtered by owner email."""
    from sqlalchemy import select
    async with async_session() as session:
        query = select(Project).order_by(Project.id.desc())
        if owner:
            query = query.where(Project.owner_email == owner)
        result = await session.execute(query)
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


@app.patch("/api/projects/{project_id}")
async def rename_project(project_id: int, body: dict):
    """Rename a project."""
    new_title = body.get("title", "").strip()
    if not new_title:
        raise HTTPException(400, "Title cannot be empty")
    async with async_session() as session:
        project = await session.get(Project, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        project.title = new_title
        await session.commit()
        return {"status": "success", "title": new_title}


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


# ────────────────────────── REPOSITORY ENDPOINTS ──────────────────────────


@app.get("/api/projects/{project_id}/files")
async def get_project_files(project_id: int):
    """Get the file tree for a project's workspace."""
    workspace_path = os.path.join(settings.workspace_dir, f"project_{project_id}")
    if not os.path.exists(workspace_path):
        return {"files": [], "total_size": 0}

    files = []
    total_size = 0
    for root, _dirs, filenames in os.walk(workspace_path):
        for filename in filenames:
            # Skip debug/internal files
            if filename.startswith("_debug") or filename.startswith("_test"):
                continue
            filepath = os.path.join(root, filename)
            rel_path = os.path.relpath(filepath, workspace_path).replace("\\", "/")
            size = os.path.getsize(filepath)
            total_size += size

            # Detect language from extension
            ext = os.path.splitext(filename)[1].lower()
            lang_map = {
                ".html": "html", ".css": "css", ".js": "javascript",
                ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx",
                ".py": "python", ".json": "json", ".md": "markdown",
                ".txt": "text", ".yml": "yaml", ".yaml": "yaml",
                ".sh": "bash", ".bat": "batch", ".sql": "sql",
                ".xml": "xml", ".svg": "svg", ".env": "text",
            }
            language = lang_map.get(ext, "text")

            # Read content (only text files, skip large files)
            content = ""
            if size < 500_000:  # Skip files > 500KB
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, IOError):
                    content = "[Binary file — cannot display]"

            files.append({
                "path": rel_path,
                "name": filename,
                "language": language,
                "size": size,
                "content": content,
            })

    # Sort: index.html first, then by path
    files.sort(key=lambda f: (0 if f["name"] == "index.html" else 1, f["path"]))

    return {"files": files, "total_size": total_size, "file_count": len(files)}


@app.get("/api/projects/{project_id}/preview/{file_path:path}")
async def preview_project_file(project_id: int, file_path: str):
    """Serve a project file for iframe preview."""
    from fastapi.responses import FileResponse
    workspace_path = os.path.join(settings.workspace_dir, f"project_{project_id}")
    full_path = os.path.join(workspace_path, file_path)

    # Security: ensure the path is within the workspace
    full_path = os.path.abspath(full_path)
    workspace_abs = os.path.abspath(workspace_path)
    if not full_path.startswith(workspace_abs):
        raise HTTPException(403, "Access denied")

    if not os.path.exists(full_path):
        raise HTTPException(404, "File not found")

    # Determine MIME type
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
        ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
        ".jpg": "image/jpeg", ".gif": "image/gif", ".ico": "image/x-icon",
        ".woff": "font/woff", ".woff2": "font/woff2", ".ttf": "font/ttf",
    }
    media_type = mime_map.get(ext, "text/plain")
    return FileResponse(full_path, media_type=media_type)


from pydantic import BaseModel

class DocResponse(BaseModel):
    markdown: str

@app.post("/api/projects/{project_id}/documentation", response_model=DocResponse)
async def generate_project_documentation(project_id: int, db: AsyncSession = Depends(get_db)):
    """Generate markdown documentation for an existing CDASB project workspace."""
    # 1. Fetch project info
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # 2. Read workspace files
    workspace_path = os.path.join(settings.workspace_dir, f"project_{project_id}")
    if not os.path.exists(workspace_path):
        raise HTTPException(404, "Workspace not found")

    file_contents = []
    for root, dirs, files in os.walk(workspace_path):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".next", "__pycache__")]
        for file in files:
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, workspace_path)
            # Skip large binaries
            if os.path.getsize(filepath) > 500_000:
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    file_contents.append(f"--- File: {rel_path} ---\n{content}\n")
            except (UnicodeDecodeError, IOError):
                pass
    
    if not file_contents:
        raise HTTPException(400, "No readable files found in workspace")

    files_str = "\n".join(file_contents)

    # 3. Generate documentation using Llama 3.3 70B
    from app.agents.personas.documenter import DocumenterAgent
    agent = DocumenterAgent()
    
    from fastapi.responses import StreamingResponse
    try:
        return StreamingResponse(
            agent.generate_docs_stream(project.title, files_str),
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(500, f"Error generating documentation: {str(e)}")

import tempfile
import zipfile
import shutil
from fastapi import UploadFile, File

@app.post("/api/generate-docs/external", response_model=DocResponse)
async def generate_external_documentation(file: UploadFile = File(...)):
    """Generate markdown documentation from an uploaded ZIP file."""
    if not file.filename.endswith('.zip'):
        raise HTTPException(400, "Only .zip files are supported")
        
    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, file.filename)
        
        # Save uploaded zip
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Extract zip
        extract_path = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_path, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        except zipfile.BadZipFile:
            raise HTTPException(400, "Invalid ZIP file")
            
        # Read files
        file_contents = []
        for root, dirs, files in os.walk(extract_path):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".next", "__pycache__", "venv")]
            for f in files:
                filepath = os.path.join(root, f)
                rel_path = os.path.relpath(filepath, extract_path)
                if os.path.getsize(filepath) > 500_000:
                    continue
                try:
                    with open(filepath, "r", encoding="utf-8") as f_obj:
                        content = f_obj.read()
                        file_contents.append(f"--- File: {rel_path} ---\n{content}\n")
                except (UnicodeDecodeError, IOError):
                    pass
                    
        if not file_contents:
            raise HTTPException(400, "No readable files found in ZIP")
            
        files_str = "\n".join(file_contents)
        
        # Limit total context size to prevent massive token overload
        # Roughly ~50k words -> ~65k tokens. Llama 3.3 handles 128k, but let's be safe.
        if len(files_str) > 300_000:
            files_str = files_str[:300_000] + "\n...[TRUNCATED DUE TO SIZE]..."

        from app.agents.personas.documenter import DocumenterAgent
        agent = DocumenterAgent()
        
        from fastapi.responses import StreamingResponse
        try:
            project_title = file.filename.replace('.zip', '')
            return StreamingResponse(
                agent.generate_docs_stream(project_title, files_str),
                media_type="text/plain"
            )
        except Exception as e:
            raise HTTPException(500, f"Error generating documentation: {str(e)}")


class PDFRequest(BaseModel):
    markdown: str
    title: str = "Documentation"

@app.post("/api/documentation/pdf")
async def generate_pdf_from_markdown(request: PDFRequest):
    """Convert markdown to a beautifully styled PDF using xhtml2pdf."""
    from fastapi.responses import Response
    import markdown as md
    from xhtml2pdf import pisa
    import io
    import re

    # Convert markdown to HTML
    html_body = md.markdown(
        request.markdown,
        extensions=["tables", "fenced_code", "toc", "sane_lists"]
    )

    # Post-process: Replace raw mermaid code blocks with a styled "Architecture Diagram" box
    # The markdown converter outputs mermaid blocks in various formats depending on extensions.
    import html as html_module

    def format_mermaid_content(raw_text):
        """Convert raw mermaid text into an actual image via mermaid.ink API."""
        raw_text = html_module.unescape(raw_text).strip()
        
        # Base64 encode the mermaid string for the URL
        import base64
        # Convert to bytes, base64 encode, and convert back to string
        b64_mermaid = base64.b64encode(raw_text.encode('utf-8')).decode('utf-8')
        img_url = f"https://mermaid.ink/img/{b64_mermaid}"
        
        return f"""<div style="border: 2px solid #4361ee; padding: 18px 22px; margin: 16px 0; background-color: #f0f3ff; text-align: center;">
            <div style="font-weight: bold; font-size: 12pt; color: #4361ee; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 2px solid #c5ceff; letter-spacing: 0.5px; text-align: left;">SYSTEM ARCHITECTURE FLOW</div>
            <img src="{img_url}" style="zoom: 60%;" />
        </div>"""

    # Try multiple mermaid patterns - use [\r\n]+ to handle Windows line endings
    mermaid_patterns = [
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        r'<pre><code>mermaid[\r\n]+(.*?)</code></pre>',
        r'<p><code>mermaid[\r\n]+(.*?)</code></p>',
        r'<code>mermaid[\r\n]+(.*?)</code>',
    ]
    for pattern in mermaid_patterns:
        html_body = re.sub(pattern, lambda m: format_mermaid_content(m.group(1)), html_body, flags=re.DOTALL)

    # Post-process: Style h2 headings as colored section headers
    section_colors = ['#4361ee', '#7c3aed', '#059669', '#d97706', '#dc2626', '#0891b2', '#6366f1', '#be185d']
    h2_count = [0]
    def style_h2(match):
        text = match.group(1)
        color = section_colors[h2_count[0] % len(section_colors)]
        h2_count[0] += 1
        return f"""<div style="margin-top: 30px; margin-bottom: 14px;">
            <div style="background-color: {color}; color: white; font-size: 14pt; font-weight: bold; padding: 10px 18px; letter-spacing: 0.5px;">{text}</div>
        </div>"""
    
    html_body = re.sub(r'<h2[^>]*>(.*?)</h2>', style_h2, html_body)

    # Get current date for cover
    from datetime import datetime
    gen_date = datetime.now().strftime("%B %d, %Y")

    styled_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{request.title}</title>
<style>
body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.65;
    color: #2d2d3d;
    padding: 0;
    background: white;
}}

h1 {{
    font-size: 26pt;
    font-weight: bold;
    color: #1a1a2e;
    margin: 0 0 16px 0;
    padding: 0;
    border-bottom: 2px solid #e0e0e0;
    padding-bottom: 8px;
}}

h2 {{
    font-size: 15pt;
    font-weight: bold;
    color: #1a1a2e;
    margin-top: 26px;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 2px solid #4361ee;
}}

h3 {{
    font-size: 12pt;
    font-weight: bold;
    color: #4361ee;
    margin-top: 16px;
    margin-bottom: 6px;
}}

p {{
    margin-bottom: 8px;
    color: #3a3a4a;
    text-align: justify;
}}

ul, ol {{
    margin-left: 18px;
    margin-bottom: 10px;
}}

li {{
    margin-bottom: 4px;
    color: #3a3a4a;
}}

strong {{
    font-weight: bold;
    color: #1a1a2e;
}}

code {{
    font-family: Courier, monospace;
    font-size: 8.5pt;
    background-color: #eef0ff;
    color: #4361ee;
    padding: 1px 4px;
}}

pre {{
    background-color: #1e2233;
    color: #e4e7f1;
    padding: 14px 18px;
    font-family: Courier, monospace;
    font-size: 8pt;
    line-height: 1.5;
    margin: 12px 0;
    border-left: 4px solid #4361ee;
}}

pre code {{
    background-color: transparent;
    color: #e4e7f1;
    padding: 0;
    font-size: 8pt;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9.5pt;
}}

th {{
    background-color: #4361ee;
    color: white;
    font-weight: bold;
    text-align: left;
    padding: 9px 14px;
    border: 1px solid #3451de;
}}

td {{
    padding: 8px 14px;
    border: 1px solid #dde0e8;
    color: #3a3a4a;
}}

tr:nth-child(even) td {{
    background-color: #f5f6ff;
}}

blockquote {{
    border-left: 4px solid #4361ee;
    padding: 10px 18px;
    margin: 12px 0;
    background-color: #f0f3ff;
    color: #555;
}}

hr {{
    border: none;
    border-top: 2px solid #e8e8ee;
    margin: 18px 0;
}}

@page {{
    size: A4;
    margin: 1.5cm 2cm 2.5cm 2cm;
    @frame footer {{
        -pdf-frame-content: footerContent;
        bottom: 0.3cm;
        margin-left: 1cm;
        margin-right: 1cm;
        height: 1.2cm;
    }}
}}
</style>
</head>
<body>

<!-- Document Header -->
<h1>{request.title}</h1>

<div style="margin-top: 16px;">
{html_body}
</div>

<!-- Footer -->
<div id="footerContent" style="text-align: center; font-size: 8pt; color: #888888; border-top: 1px solid #e0e0e0; padding-top: 4px;">
    {request.title} | Generated by CDASB on {gen_date} | Page <pdf:pagenumber /> of <pdf:pagecount />
</div>
</body>
</html>"""

    try:
        result = io.BytesIO()
        pisa_status = pisa.CreatePDF(io.StringIO(styled_html), dest=result)
        
        if pisa_status.err:
            raise HTTPException(500, "PDF rendering failed")
        
        pdf_bytes = result.getvalue()
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{request.title}.pdf"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"PDF generation failed: {str(e)}")


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
    # Token stream events are high-frequency ephemeral updates.
    # Don't buffer them — they'd flood the replay buffer with hundreds of entries.
    if data.get("type") == "token_stream" or (
        data.get("type") == "conflict_event" and data.get("event_type") == "token_stream"
    ):
        await manager.broadcast(project_id, data)
        return
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

            if action == "reject_plan":
                async with async_session() as session:
                    project = await session.get(Project, project_id)
                    if project:
                        project.final_plan = None
                        project.status = ProjectStatus.PLANNING
                        await session.commit()
                        user_input = project.original_input
                
                if project_id in _project_events:
                    _project_events[project_id].clear()
                
                await send_event({"type": "status", "phase": "planning", "status": "running"})
                task = asyncio.create_task(_run_planning_bg(user_input))
                _project_tasks[project_id] = task
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

                    # Extract only the final plan text, not the entire conflict history
                    final_plan = project.final_plan
                    if isinstance(final_plan, dict):
                        plan_text = json.dumps(final_plan)
                    else:
                        plan_text = str(final_plan)
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
