"""
Pipeline Orchestrator – Coordinates the full CDASB workflow.

Workflow: Input -> Analyze -> Plan -> Conflict(Plan) -> User Approval ->
          Build -> Conflict(Code) -> Execute -> Test -> Conflict(Test) -> Deliver
"""
from __future__ import annotations
import json
import os
from typing import Callable, Awaitable

from app.agents.personas.planner import PlannerAgent
from app.agents.personas.analyst import AnalystAgent
from app.agents.personas.builder import BuilderAgent
from app.agents.personas.gatekeeper import GatekeeperAgent
from app.orchestrator.conflict_loop import ConflictLoop, ConflictEvent, EventType
from app.sandbox.executor import NativeExecutor
from app.database.models import async_session, Project, ProjectStatus, ConflictRound, ExecutionLog
from sqlalchemy.orm.attributes import flag_modified


class PipelineOrchestrator:
    """
    Full end-to-end pipeline manager.
    Drives the project through Planning -> Approval -> Execution phases,
    streaming all events via a callback (typically a WebSocket sender).
    """

    def __init__(self, project_id: int, on_event: Callable[[dict], Awaitable[None]]):
        self.project_id = project_id
        self.on_event = on_event
        self.planner = PlannerAgent()
        self.analyst = AnalystAgent()
        self.builder = BuilderAgent()
        self.gatekeeper = GatekeeperAgent()

    async def _emit(self, event_type: str, data: dict):
        await self.on_event({"type": event_type, "project_id": self.project_id, **data})

    async def _conflict_event_handler(self, event: ConflictEvent):
        """Bridge ConflictLoop events to the WebSocket stream."""
        await self.on_event({
            "type": "conflict_event",
            "project_id": self.project_id,
            **event.to_dict(),
        })

    async def _token_emitter(self, payload: dict):
        """Relay live token streaming events to the WebSocket."""
        await self.on_event({
            "type": "token_stream",
            "project_id": self.project_id,
            **payload,
        })

    # ──────────────────────────── PHASE 1: PLANNING ────────────────────────────

    async def run_planning(self, user_input: str) -> dict:
        """
        Phase 1: Analyze input and produce a conflict-refined plan.
        Returns the final approved plan dict.
        """
        await self._emit("status", {"phase": "planning", "message": "Starting planning phase..."})

        # Gatekeeper Triage
        has_document = "--- DOCUMENT CONTENT ---" in user_input
        project_name = None
        if has_document:
            complexity = "COMPLEX"
            domain = "FULLSTACK"
            await self._emit("agent_action", {"agent": "Gatekeeper", "action": "Document detected. Bypassing triage -> COMPLEX"})
        else:
            await self._emit("agent_action", {"agent": "Gatekeeper", "action": "Analyzing complexity..."})
            triage_result = await self.gatekeeper.run_json(user_input, on_token=self._token_emitter)
            complexity = triage_result.get("complexity", "COMPLEX").upper()
            domain = triage_result.get("domain", "FULLSTACK").upper()
            project_name = triage_result.get("project_name", "").strip()
            await self._emit("agent_action", {"agent": "Gatekeeper", "action": f"Triage complete: {complexity} {domain}"})

        # Update project title with gatekeeper's chosen name
        if project_name:
            async with async_session() as session:
                project = await session.get(Project, self.project_id)
                if project:
                    project.title = project_name
                    await session.commit()
            await self._emit("project_named", {"name": project_name})

        if complexity == "SIMPLE":
            # Run SimplePlanner to generate an actual blueprint for user review
            from app.agents.personas.simple_planner import SimplePlannerAgent

            await self._emit("agent_action", {"agent": "SimplePlanner", "action": "Drafting blueprint..."})
            await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_START, phase="simple-planning", round_number=1, agent="SimplePlanner"))

            simple_planner = SimplePlannerAgent()
            if domain == "WEB":
                planner_detail = "Include DOM structure, CSS specifications, and JavaScript logic."
            else:
                planner_detail = "Include program structure, compilation/build instructions, and core logic. Use the language the user requested."

            blueprint = await simple_planner.run_stream(
                f"Create a blueprint for: {user_input}\nDomain: {domain}\nThis is a SIMPLE project — generate a clear, complete blueprint with exact file list and integration map.\n{planner_detail}",
                on_token=self._token_emitter,
            )

            await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_DONE, phase="simple-planning", round_number=1, agent="SimplePlanner", data={"output_preview": blueprint[:500]}))
            await self._emit("agent_action", {"agent": "SimplePlanner", "action": "Blueprint complete"})

            rapid_plan = {
                "final_output": blueprint,
                "rounds": 0,
                "approved": True,
                "complexity": "SIMPLE",
                "domain": domain,
                "raw_prompt": user_input[:500],
                "blueprint": blueprint,
            }
            # Save to database
            async with async_session() as session:
                project = await session.get(Project, self.project_id)
                if project:
                    project.parsed_requirements = {"type": "rapid", "domain": domain}
                    project.final_plan = rapid_plan
                    project.status = ProjectStatus.AWAITING_APPROVAL
                    await session.commit()

            await self._emit("planning_complete", {
                "plan": blueprint[:2000],
                "rounds": 0,
                "approved_by_agents": True,
            })
            return rapid_plan

        # Step 1: Analyst extracts requirements
        await self._emit("agent_action", {"agent": "Analyst", "action": "Extracting requirements..."})
        requirements = await self.analyst.run_stream(
            f"Extract structured requirements from the following input:\n\n{user_input}",
            on_token=self._token_emitter,
        )
        await self._emit("agent_action", {"agent": "Analyst", "action": "Requirements extracted", "preview": requirements[:300]})

        # Step 2: Planner designs architecture (goes through conflict loop)
        planning_prompt = (
            f"Design a complete system architecture based on these requirements:\n\n"
            f"--- REQUIREMENTS ---\n{requirements}\n--- END ---\n\n"
            f"--- ORIGINAL USER INPUT ---\n{user_input}\n--- END ---"
        )

        from app.agents.personas.planning_critic import PlanningCriticAgent
        from app.agents.personas.planning_optimizer import PlanningOptimizerAgent
        from app.agents.personas.planning_judge import PlanningJudgeAgent

        conflict = ConflictLoop(
            phase="planning", 
            on_event=self._conflict_event_handler,
            critic_agent=PlanningCriticAgent(),
            optimizer_agent=PlanningOptimizerAgent(),
            judge_agent=PlanningJudgeAgent()
        )
        plan_result = await conflict.run(self.planner, planning_prompt)

        # Save to database
        async with async_session() as session:
            project = await session.get(Project, self.project_id)
            if project:
                project.parsed_requirements = {"raw_text": requirements}
                project.final_plan = plan_result
                project.status = ProjectStatus.AWAITING_APPROVAL
                await session.commit()

        # Save conflict rounds
        await self._save_conflict_history("planning", conflict.history)

        await self._emit("planning_complete", {
            "plan": plan_result["final_output"][:2000],
            "rounds": plan_result["rounds"],
            "approved_by_agents": plan_result["approved"],
        })

        return plan_result

    # ──────────────────────── SIMPLE PROJECT FAST-PATH ────────────────────────

    async def _run_simple_execution(self, plan: str, plan_dict: dict, executor: NativeExecutor) -> dict:
        """
        Fast execution path for SIMPLE projects.
        
        Flow: Builder (all files, one shot) → Write → Integration check
        Blueprint is already generated during planning phase.
        
        No decomposer, no conflict loop, no chunk iteration.
        Typically completes in 1 API call (~15-20 seconds).
        """
        domain = plan_dict.get("domain", "WEB")
        raw_prompt = plan_dict.get("raw_prompt", plan)
        workspace_path = str(executor.project_dir)

        # ── Step 1: Use existing blueprint from planning phase, or generate if missing ──
        blueprint = plan_dict.get("blueprint", "")

        if not blueprint:
            # Fallback: blueprint wasn't generated during planning (e.g. legacy project)
            from app.agents.personas.simple_planner import SimplePlannerAgent

            await self._emit("execution_update", {"message": "Simple Planner drafting blueprint..."})
            await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_START, phase="simple-planning", round_number=1, agent="SimplePlanner"))

            simple_planner = SimplePlannerAgent()
            if domain == "WEB":
                planner_detail = "Include DOM structure, CSS specifications, and JavaScript logic."
            else:
                planner_detail = "Include program structure, compilation/build instructions, and core logic. Use the language the user requested."
            blueprint = await simple_planner.run_stream(
                f"Create a blueprint for: {raw_prompt}\nDomain: {domain}\nThis is a SIMPLE project — generate a clear, complete blueprint with exact file list and integration map.\n{planner_detail}",
                on_token=self._token_emitter,
            )

            await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_DONE, phase="simple-planning", round_number=1, agent="SimplePlanner", data={"output_preview": blueprint[:500]}))
        else:
            await self._emit("execution_update", {"message": "Using blueprint from planning phase."})

        await self._emit("execution_update", {"message": "Blueprint ready. Building all files..."})

        # ── Step 2: Builder generates ALL files in one shot ──
        await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_START, phase="simple-building", round_number=1, agent="Builder"))

        if domain == "WEB":
            coherence_note = "All files must be coherent — HTML must link CSS/JS, JS must target DOM IDs from the HTML."
        else:
            coherence_note = "All files must be coherent — headers/imports must be correct, modules must connect properly, and the build/run process must work. Use the EXACT language specified in the blueprint."

        build_prompt = (
            f"Generate the COMPLETE project based on this blueprint.\n\n"
            f"--- BLUEPRINT ---\n{blueprint}\n--- END BLUEPRINT ---\n\n"
            f"--- ORIGINAL REQUEST ---\n{raw_prompt}\n--- END ---\n\n"
            f"IMPORTANT: Generate ALL files listed in the blueprint in a SINGLE response.\n"
            f"{coherence_note}\n"
            f"This is a {domain} project. Make it polished and complete."
        )

        build_result_text = await self.builder.run_stream(build_prompt, on_token=self._token_emitter)
        await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_DONE, phase="simple-building", round_number=1, agent="Builder", data={"output_preview": build_result_text[:500]}))

        # Parse all files from the Builder's response
        code_data = self._safe_parse(build_result_text)
        files = code_data.get("files", [])

        if not files:
            # Save raw output to debug file so we can inspect what went wrong
            debug_path = os.path.join(workspace_path, "_debug_raw_builder_output.txt")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(build_result_text)
            preview = build_result_text[:300].replace("\n", " ")
            await self._emit("execution_update", {"message": f"⚠️ Builder returned no parseable files. Raw output saved to _debug_raw_builder_output.txt. Preview: {preview}"})
            
            # Mark project completed (with 0 files) so user isn't stuck
            async with async_session() as session:
                project = await session.get(Project, self.project_id)
                if project:
                    project.status = ProjectStatus.COMPLETED
                    await session.commit()
            
            return {"workspace": workspace_path, "files": []}

        # ── Step 3: Write all files to disk ──
        await self._emit("execution_update", {"message": f"Writing {len(files)} files to workspace..."})
        await executor.write_files_async(files)

        # Track completed files in DB
        file_paths = [f["path"] for f in files]
        async with async_session() as session:
            project = await session.get(Project, self.project_id)
            if project:
                project.completed_files = file_paths
                flag_modified(project, "completed_files")
                await session.commit()

        for f in files:
            await self._emit("execution_update", {"message": f"✅ Wrote: {f['path']}"})

        # ── Step 4: Automated integration check for WEB projects ──
        if domain == "WEB":
            await self._run_integration_check(executor, files)

        # ── Step 5: Run setup commands if any ──
        setup_commands = code_data.get("setup_commands", [])
        run_command = code_data.get("run_command", "")

        if setup_commands:
            await self._emit("execution_update", {"message": "Running setup commands..."})
            await executor.run_setup(setup_commands)

        # Mark project as completed
        async with async_session() as session:
            project = await session.get(Project, self.project_id)
            if project:
                project.status = ProjectStatus.COMPLETED
                await session.commit()

        await self._emit("execution_update", {"message": f"🎉 Simple project complete! {len(files)} files built."})

        return {
            "workspace": workspace_path,
            "files": file_paths,
            "setup_commands": setup_commands,
            "run_command": run_command,
        }

    async def _run_integration_check(self, executor: NativeExecutor, files: list[dict]):
        """
        Zero-cost automated check (no LLM): verify HTML files reference all CSS/JS in the workspace.
        If broken, make ONE corrective Builder call.
        """
        import re as _re

        html_files = [f for f in files if f["path"].endswith(".html")]
        css_files = [f["path"] for f in files if f["path"].endswith(".css")]
        js_files = [f["path"] for f in files if f["path"].endswith(".js")]

        if not html_files:
            return

        for html_file in html_files:
            content = html_file.get("content", "")
            html_dir = os.path.dirname(html_file["path"]) or "."
            html_basename = os.path.splitext(os.path.basename(html_file["path"]))[0]

            # Smart matching: only inject assets that share the same directory
            # or have a matching basename (e.g., admin.html ↔ admin.css/admin.js)
            relevant_css = [
                css for css in css_files
                if css not in content and (
                    (os.path.dirname(css) or ".") == html_dir  # same directory
                    or os.path.splitext(os.path.basename(css))[0] in (html_basename, "style", "styles", "main", "index")
                )
            ]
            relevant_js = [
                js for js in js_files
                if js not in content and (
                    (os.path.dirname(js) or ".") == html_dir
                    or os.path.splitext(os.path.basename(js))[0] in (html_basename, "script", "scripts", "main", "index", "app")
                )
            ]

            if relevant_css or relevant_js:
                await self._emit("execution_update", {"message": f"⚠️ Integration issue: {html_file['path']} missing references to {relevant_css + relevant_js}. Auto-fixing..."})

                fixed_content = content

                for css in relevant_css:
                    link_tag = f'  <link rel="stylesheet" href="{css}">\n'
                    if _re.search(r'</head>', fixed_content, _re.IGNORECASE):
                        fixed_content = _re.sub(r'(</head>)', f'{link_tag}\\1', fixed_content, count=1, flags=_re.IGNORECASE)
                    else:
                        fixed_content = link_tag + fixed_content

                for js in relevant_js:
                    script_tag = f'  <script src="{js}"></script>\n'
                    if _re.search(r'</body>', fixed_content, _re.IGNORECASE):
                        fixed_content = _re.sub(r'(</body>)', f'{script_tag}\\1', fixed_content, count=1, flags=_re.IGNORECASE)
                    else:
                        fixed_content = fixed_content + script_tag

                html_file["content"] = fixed_content
                await executor.write_files_async([html_file])
                await self._emit("execution_update", {"message": f"✅ Fixed: {html_file['path']} now links relevant CSS/JS files"})
            else:
                await self._emit("execution_update", {"message": f"✅ Integration check passed: {html_file['path']}"})

    # ──────────────────────────── PHASE 2: EXECUTION ─────────────────────────

    async def run_execution(self, plan: str) -> dict:
        """
        Phase 2: Build, test, and refine the system through iterative conflict loops.
        Supports crash-resilient resumption via cached decomposition and file checkpoints.
        """
        await self._emit("status", {"phase": "execution", "message": "Starting execution phase..."})

        executor = NativeExecutor(self.project_id)
        workspace_path = executor.setup_workspace()
        
        plan_dict = self._safe_parse(plan)

        # ── Determine project complexity ──
        complexity = plan_dict.get("complexity", "COMPLEX")
        domain = plan_dict.get("domain", "FULLSTACK")

        # ══════════════════════════════════════════════════════════════════
        # SIMPLE PROJECT FAST-PATH
        # Simple Planner → Builder (all files, one shot) → Write to disk
        # No decomposer, no conflict loop, no chunk iteration
        # ══════════════════════════════════════════════════════════════════
        if complexity == "SIMPLE":
            return await self._run_simple_execution(plan, plan_dict, executor)

        # ══════════════════════════════════════════════════════════════════
        # COMPLEX PROJECT FULL PIPELINE (unchanged)
        # Decomposer → Per-chunk Builder → Per-file Conflict Loop
        # ══════════════════════════════════════════════════════════════════

        # ── Step 1: Decompose (or reload cached decomposition) ──
        # We cache chunks inside final_plan so resumes replay the exact same file list.
        cached_chunks = None
        async with async_session() as session:
            project = await session.get(Project, self.project_id)
            if project and project.final_plan:
                cached_chunks = project.final_plan.get("_cached_chunks")

        if cached_chunks:
            await self._emit("execution_update", {"message": "Loaded cached decomposition from previous session..."})
            chunks = cached_chunks
        else:
            await self._emit("agent_action", {"agent": "Decomposer", "action": "Decomposing plan into iterative chunks..."})
            from app.agents.personas.task_decomposer import TaskDecomposerAgent
            decomposer = TaskDecomposerAgent()
            decomp_result = await decomposer.run_json(plan, on_token=self._token_emitter)
            chunks = decomp_result.get("chunks", [])
            await self._emit("agent_action", {"agent": "Decomposer", "action": f"Decomposition complete: {len(chunks)} chunks generated"})

            if not chunks:
                chunks = [{"type": "feature", "name": "Monolithic Fallback", "description": "Generate everything"}]

            # Cache chunks into final_plan for resumption
            async with async_session() as session:
                project = await session.get(Project, self.project_id)
                if project and project.final_plan:
                    project.final_plan["_cached_chunks"] = chunks

                    flag_modified(project, "final_plan")
                    await session.commit()

        critic_persona = "Principal Systems Architect. Do not overthink. Keep your reasoning sequence brief. Focus ONLY on fatal bugs or syntax errors. If the file integrates well with the architecture, output approved immediately."

        # Iterative Execution State
        workspace_context = {}  # Store generated files
        all_setup_commands = []
        final_run_command = ""
        full_code_result = {"files": [], "setup_commands": [], "run_command": ""}

        # Pre-load already-completed files into workspace_context from disk
        async with async_session() as session:
            proj = await session.get(Project, self.project_id)
            completed_files_cache = proj.completed_files if proj else []
        
        if completed_files_cache:
            await self._emit("execution_update", {"message": f"Resuming: {len(completed_files_cache)} files already completed, loading from disk..."})
            for fpath in completed_files_cache:
                content = executor.read_file(fpath)
                if content:
                    workspace_context[fpath] = content
                    full_code_result["files"].append({"path": fpath, "content": content})

        # Step 2: Loop over chunks
        for i, chunk in enumerate(chunks):
            chunk_name = chunk.get("name", f"Chunk {i+1}")
            chunk_cache_key = f"_chunk_{i}_files"
            
            # Check if this chunk's builder output was already cached from a previous run
            cached_chunk_files = None
            async with async_session() as session:
                project = await session.get(Project, self.project_id)
                if project and project.final_plan:
                    cached_chunk_files = project.final_plan.get(chunk_cache_key)

            # Validate cached chunks have actual file data (guard against corrupt/empty caches)
            if cached_chunk_files and isinstance(cached_chunk_files, list) and all(
                isinstance(f, dict) and "path" in f and "content" in f for f in cached_chunk_files
            ):
                # We have valid cached builder output for this chunk
                chunk_files = cached_chunk_files
                chunk_setup = chunk.get("_setup_commands", [])
                chunk_run = chunk.get("_run_command", "")
                
                # Check if ALL files in this chunk are completed
                all_done = all(f["path"] in completed_files_cache for f in chunk_files)
                if all_done:
                    await self._emit("execution_update", {"message": f"Skipping {chunk_name} ({i+1}/{len(chunks)}) — all files already built ✓"})
                    # Still collect setup/run commands
                    if chunk_setup:
                        all_setup_commands.extend(chunk_setup)
                    if chunk_run:
                        final_run_command = chunk_run
                    continue
                else:
                    await self._emit("execution_update", {"message": f"Resuming {chunk_name} ({i+1}/{len(chunks)}) — partially complete..."})
            
            # Build prompt is needed for both cached (partial) and fresh chunks
            # Cap workspace context to prevent prompt bloat (path + 200-char preview only)
            context_summary = {}
            for ctx_path, ctx_content in workspace_context.items():
                context_summary[ctx_path] = ctx_content[:200] + ("..." if len(ctx_content) > 200 else "")
            
            build_prompt = (
                f"We are building chunk: {chunk_name}\n"
                f"Description: {chunk.get('description', '')}\n\n"
                f"--- OVERALL ARCHITECTURE PLAN ---\n{plan}\n--- END ---\n\n"
                f"--- WORKSPACE CONTEXT (Files already built — showing path + preview) ---\n"
                f"{json.dumps(context_summary, indent=2)}\n--- END ---\n\n"
                f"Generate ONLY the files required for this specific chunk, ensuring they integrate with the Workspace Context."
            )

            if not cached_chunk_files:
                # Fresh chunk — call Builder
                await self._emit("execution_update", {"message": f"Drafting {chunk_name} ({i+1}/{len(chunks)})..."})
                await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_START, phase=f"drafting-{chunk_name}", round_number=1, agent="Builder"))
                build_result_text = await self.builder.run_stream(build_prompt, on_token=self._token_emitter)
                await self._conflict_event_handler(ConflictEvent(EventType.GENERATOR_DONE, phase=f"drafting-{chunk_name}", round_number=1, agent="Builder", data={"output_preview": build_result_text[:500]}))
                
                # Parse drafted files from this chunk
                code_data = self._safe_parse(build_result_text)
                chunk_files = code_data.get("files", [])
                chunk_setup = code_data.get("setup_commands", [])
                chunk_run = code_data.get("run_command", "")

                # Cache this chunk's builder output for resumption
                async with async_session() as session:
                    project = await session.get(Project, self.project_id)
                    if project and project.final_plan:
                        project.final_plan[chunk_cache_key] = chunk_files
    
                        flag_modified(project, "final_plan")
                        await session.commit()

            # Fetch current state checkpoint from DB
            async with async_session() as session:
                proj_record = await session.get(Project, self.project_id)
                if proj_record and not proj_record.completed_files:
                    proj_record.completed_files = []

                    flag_modified(proj_record, "completed_files")
                    await session.commit()
                completed_files_cache = proj_record.completed_files if proj_record else []

            # 2. Filter out already-completed files, write remaining drafts to disk
            pending_files = []
            for f in chunk_files:
                file_path = f["path"]
                if file_path in completed_files_cache:
                    await self._emit("execution_update", {"message": f"Resuming: Skipping {file_path} (already completed)..."})
                    content = executor.read_file(file_path)
                    if content:
                        f["content"] = content
                    workspace_context[file_path] = f["content"]
                    full_code_result["files"].append(f)
                else:
                    pending_files.append(f)

            if not pending_files:
                # All files in this chunk already done
                if chunk_setup:
                    all_setup_commands.extend(chunk_setup)
                if chunk_run:
                    final_run_command = chunk_run
                continue

            # Write all draft files to disk first
            await executor.write_files_async(pending_files)
            await self._emit("execution_update", {"message": f"Wrote {len(pending_files)} draft files. Starting chunk review..."})

            # 3. CHUNK-LEVEL Conflict Loop — review all files together in one pass
            # Concatenate all file contents for batch review
            chunk_content_for_review = "\n\n".join(
                f"=== FILE: {f['path']} ===\n{f['content']}" for f in pending_files
            )

            conflict = ConflictLoop(
                phase=f"coding-{chunk_name}",
                on_event=self._conflict_event_handler,
                max_rounds=1,  # Plan already got 3 rounds; execution gets 1 focused pass
                critic_persona=critic_persona,
            )
            chunk_result = await conflict.run_file(
                f"chunk:{chunk_name} ({len(pending_files)} files)",
                chunk_content_for_review,
                build_prompt,
            )

            await self._save_conflict_history(f"built_{chunk_name}", conflict.history)

            # Parse the optimized output back into individual files
            optimized_output = chunk_result["final_output"]

            # Try to split the optimized output back into per-file sections
            import re as _re
            file_sections = _re.split(r"===\s*FILE:\s*(.+?)\s*===", optimized_output)
            
            if len(file_sections) > 1:
                # Rebuild files from optimized sections: [preamble, path1, content1, path2, content2, ...]
                for j in range(1, len(file_sections), 2):
                    opt_path = file_sections[j].strip()
                    opt_content = file_sections[j + 1].strip() if j + 1 < len(file_sections) else ""
                    # Match back to pending files
                    for f in pending_files:
                        if f["path"] == opt_path:
                            f["content"] = opt_content
                            break
            # else: optimizer didn't preserve the format — keep original builder drafts

            # Write final optimized files to disk and checkpoint in ONE transaction
            await executor.write_files_async(pending_files)
            newly_completed = []
            for f in pending_files:
                workspace_context[f["path"]] = f["content"]
                full_code_result["files"].append(f)
                newly_completed.append(f["path"])
                await self._emit("execution_update", {"message": f"Successfully built and wrote: {f['path']}"})

            # Single DB checkpoint for entire chunk
            async with async_session() as session:
                p = await session.get(Project, self.project_id)
                curr = p.completed_files or []
                for path in newly_completed:
                    if path not in curr:
                        curr.append(path)
                p.completed_files = curr
                flag_modified(p, "completed_files")
                await session.commit()
                completed_files_cache = curr

            if chunk_setup:
                all_setup_commands.extend(chunk_setup)
            if chunk_run:
                final_run_command = chunk_run

        full_code_result["setup_commands"] = all_setup_commands
        full_code_result["run_command"] = final_run_command

        # Step 3: Run setup commands
        if all_setup_commands:
            await self._emit("execution_update", {"message": "Running setup commands..."})
            setup_results = await executor.run_setup(all_setup_commands)
            for i, result in enumerate(setup_results):
                log_data = result.to_dict()
                log_data["command"] = all_setup_commands[i] if i < len(all_setup_commands) else "unknown"
                await self._emit("execution_log", log_data)

                async with async_session() as session:
                    log = ExecutionLog(
                        project_id=self.project_id,
                        step=f"setup_{i}",
                        stdout=result.stdout[:5000],
                        stderr=result.stderr[:5000],
                        exit_code=result.exit_code,
                    )
                    session.add(log)
                    await session.commit()

        # Step 4: Run the project
        if final_run_command:
            await self._emit("execution_update", {"message": f"Running: {final_run_command}"})
            run_result = await executor.run_project(final_run_command)
            await self._emit("execution_log", {**run_result.to_dict(), "command": final_run_command})

            async with async_session() as session:
                log = ExecutionLog(
                    project_id=self.project_id,
                    step="run",
                    stdout=run_result.stdout[:5000],
                    stderr=run_result.stderr[:5000],
                    exit_code=run_result.exit_code,
                )
                session.add(log)
                await session.commit()

        # Update project status
        async with async_session() as session:
            project = await session.get(Project, self.project_id)
            if project:
                project.status = ProjectStatus.COMPLETED
                await session.commit()

        await self._emit("build_complete", {
            "message": "Iterative System Build Completed!",
            "workspace": workspace_path,
            "files": executor.list_files(),
        })

        return {
            "workspace": workspace_path,
            "files": executor.list_files(),
            "code_result": full_code_result,
        }

    # ──────────────────────────── HELPERS ────────────────────────────────────

    async def _save_conflict_history(self, phase: str, history: list[dict]):
        async with async_session() as session:
            for entry in history:
                record = ConflictRound(
                    project_id=self.project_id,
                    phase=phase,
                    round_number=entry.get("round", 0),
                    critic_output=(entry.get("critic", ""))[:5000],
                    optimizer_output=(entry.get("optimizer", ""))[:5000],
                    judge_verdict=entry.get("verdict", "unknown"),
                )
                session.add(record)
            await session.commit()

    @staticmethod
    def _safe_parse(text: str) -> dict:
        """
        Robust JSON extraction with multi-layer fallback.
        Handles: fenced JSON, unfenced JSON, raw JSON, file-pattern scanning,
        and broken JSON from LLMs (unescaped quotes inside strings).
        """
        import re
        if isinstance(text, dict):
            return text
        if not isinstance(text, str) or not text.strip():
            return {"raw_text": str(text)}

        def _try_parse(s: str) -> dict | None:
            """Try json.loads, then try repairing common LLM JSON errors."""
            s = s.strip()
            if not s:
                return None
            # Attempt 1: Direct parse
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass
            # Attempt 2: Fix unescaped newlines/tabs inside strings
            try:
                # Replace literal control chars that aren't properly escaped
                fixed = s.replace('\r\n', '\\n').replace('\r', '\\n')
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
            # Attempt 2.5: Fix stray backslashes (e.g. `\ ` or `\;` that aren't valid JSON escapes)
            try:
                # Replace \X where X is not a valid JSON escape char (", \, /, b, f, n, r, t, u)
                fixed_bs = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)
                return json.loads(fixed_bs)
            except json.JSONDecodeError:
                pass
            # Attempt 3: Use a character-walk to re-escape broken strings
            try:
                repaired = PipelineOrchestrator._repair_json(s)
                return json.loads(repaired)
            except (json.JSONDecodeError, Exception):
                pass
            return None

        # Layer 1: Try ```json ... ``` fenced block
        json_match = re.search(r"```json\s*\r?\n?(.*?)```", text, re.DOTALL)
        if json_match:
            result = _try_parse(json_match.group(1))
            if result:
                return result

        # Layer 2: Try ``` ... ``` without language hint
        fence_match = re.search(r"```\s*\r?\n?(.*?)```", text, re.DOTALL)
        if fence_match:
            result = _try_parse(fence_match.group(1))
            if result:
                return result

        # Layer 3: Try raw JSON parse on the full text
        result = _try_parse(text)
        if result:
            return result

        # Layer 4: Find "files" key using simple string search (NO dangerous regex)
        files_idx = text.find('"files"')
        if files_idx != -1:
            # Walk backwards to find the opening { 
            brace_start = text.rfind('{', 0, files_idx)
            if brace_start != -1:
                depth = 0
                in_string = False
                escape = False
                for k in range(brace_start, len(text)):
                    char = text[k]
                    if not in_string:
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                        elif char == '"':
                            in_string = True
                    else:
                        if escape:
                            escape = False
                        elif char == '\\':
                            escape = True
                        elif char == '"':
                            in_string = False
                            
                    if depth == 0 and not in_string:
                        result = _try_parse(text[brace_start:k+1])
                        if result:
                            return result
                        break

        # Final fallback
        return {"raw_text": str(text)}

    @staticmethod
    def _repair_json(s: str) -> str:
        """
        Attempt to repair JSON where LLMs have placed unescaped quotes
        inside string values (e.g. in code comments like: // the "tech" look).
        
        Strategy: Walk character-by-character. When inside a JSON string,
        if we hit a `"` that doesn't look like a proper string terminator
        (next char is not , : ] } or whitespace followed by those), escape it.
        """
        result = []
        i = 0
        in_string = False
        
        while i < len(s):
            c = s[i]
            
            if not in_string:
                result.append(c)
                if c == '"':
                    in_string = True
            else:
                if c == '\\':
                    # Escaped character — take it and the next char as-is
                    result.append(c)
                    if i + 1 < len(s):
                        i += 1
                        result.append(s[i])
                elif c == '"':
                    # Is this the real end of the string?
                    # Look ahead: skip whitespace, then check for structural chars
                    rest = s[i+1:].lstrip()
                    if not rest or rest[0] in (',', ':', ']', '}', '\n', '\r'):
                        # Legit string terminator
                        result.append(c)
                        in_string = False
                    else:
                        # Unescaped quote inside string — escape it
                        result.append('\\"')
                elif c == '\n':
                    result.append('\\n')
                elif c == '\r':
                    result.append('\\r')
                elif c == '\t':
                    result.append('\\t')
                else:
                    result.append(c)
            i += 1
        
        return ''.join(result)
