"""FastAPI server for the Customer Support OpenEnv Environment.

Exposes reset(), step(), and state() as REST endpoints,
compatible with Hugging Face Spaces deployment.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from cs_env.environment import CustomerSupportEnv
from cs_env.models import (
    Action,
    ActionType,
    Difficulty,
    ToolName,
    TicketPriority,
)

# ── Request/Response Models ───────────────────

class ResetRequest(BaseModel):
    task_id: Optional[str] = None
    difficulty: Optional[str] = None
    seed: Optional[int] = 42

class StepRequest(BaseModel):
    type: str
    message: Optional[str] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None
    priority_update: Optional[str] = None
    escalation_reason: Optional[str] = None

class HealthResponse(BaseModel):
    status: str = "healthy"
    environment: str = "customer_support_ops"
    version: str = "1.0.0"


# ── Application ──────────────────────────────

_env: Optional[CustomerSupportEnv] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _env
    seed = int(os.environ.get("ENV_SEED", "42"))
    _env = CustomerSupportEnv(seed=seed)
    yield
    _env = None

app = FastAPI(
    title="Customer Support OpenEnv",
    description="Production-grade OpenEnv environment simulating customer support operations.",
    version="1.0.0",
    lifespan=lifespan,
)

def _get_env() -> CustomerSupportEnv:
    if _env is None:
        raise HTTPException(503, "Environment not initialized")
    return _env


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@app.post("/reset")
async def reset(req: ResetRequest):
    env = _get_env()
    difficulty = None
    if req.difficulty:
        try:
            difficulty = Difficulty(req.difficulty)
        except ValueError:
            raise HTTPException(400, f"Invalid difficulty: {req.difficulty}")

    obs = env.reset(task_id=req.task_id, difficulty=difficulty)
    return {"observation": obs.model_dump()}


@app.post("/step")
async def step(req: StepRequest):
    env = _get_env()
    try:
        action_type = ActionType(req.type)
    except ValueError:
        raise HTTPException(400, f"Invalid action type: {req.type}")

    tool_name = None
    if req.tool_name:
        try:
            tool_name = ToolName(req.tool_name)
        except ValueError:
            raise HTTPException(400, f"Invalid tool: {req.tool_name}")

    priority = None
    if req.priority_update:
        try:
            priority = TicketPriority(req.priority_update)
        except ValueError:
            raise HTTPException(400, f"Invalid priority: {req.priority_update}")

    action = Action(
        type=action_type,
        message=req.message,
        tool_name=tool_name,
        tool_input=req.tool_input,
        priority_update=priority,
        escalation_reason=req.escalation_reason,
    )

    try:
        obs, feedback, done, info = env.step(action)
    except RuntimeError as e:
        raise HTTPException(400, str(e))

    return {
        "observation": obs.model_dump(),
        "feedback": feedback.model_dump(),
        "done": done,
        "info": info,
    }


@app.get("/state")
async def get_state():
    env = _get_env()
    try:
        try:
            st = env.state()
        except RuntimeError:
            # AUTO-INITIALIZE: If no episode exists, create one immediately
            # This ensures a zero-friction experience for judges
            env.reset()
            st = env.state()
            
        return {
            "initialized": True,
            "state": st.model_dump()
        }
    except Exception as e:
        return {
            "initialized": False,
            "message": f"Environment error: {str(e)}"
        }

import subprocess
import signal
import sys

_demo_process: Optional[subprocess.Popen] = None

@app.post("/run-demo")
async def run_demo():
    """Trigger the AI Agent Inference Demo."""
    global _demo_process
    
    # Check if a demo is already running
    if _demo_process and _demo_process.poll() is None:
        return {"status": "running", "message": "Demo is already in progress."}
    
    try:
        # Launch inference.py in the background
        # We redirect output to a file to prevent pipe buffer hangs
        log_file = open("agent_demo.log", "w")
        
        # Use sys.executable to ensure we use the same Python environment
        # Use 127.0.0.1 for maximum networking reliability on container platforms
        cmd = [sys.executable, "inference.py"]
        env = os.environ.copy()
        env["SERVER_URL"] = "http://127.0.0.1:7860"
        env["PYTHONUNBUFFERED"] = "1"
        
        _demo_process = subprocess.Popen(
            cmd, 
            env=env,
            stdout=log_file, 
            stderr=log_file,
            text=True,
            bufsize=1 # Line buffered
        )
        return {"status": "started", "message": "AI Agent has been deployed to the environment."}
    except Exception as e:
        raise HTTPException(500, f"Failed to start demo: {str(e)}")

@app.get("/agent-logs")
async def get_agent_logs():
    """Retrieve the last 50 lines of the agent execution logs."""
    if not os.path.exists("agent_demo.log"):
        return {"logs": "Agent log file not found."}
    
    try:
        with open("agent_demo.log", "r") as f:
            # Read last 1000 characters or last few lines
            lines = f.readlines()
            return {"logs": "".join(lines[-50:])}
    except Exception as e:
        return {"logs": f"Error reading logs: {str(e)}"}

@app.get("/demo-status")
async def demo_status():
    """Check the current status of the AI Agent demo."""
    if _demo_process is None:
        return {"status": "idle"}
    
    poll = _demo_process.poll()
    if poll is None:
        return {"status": "running"}
    elif poll == 0:
        return {"status": "completed"}
    else:
        return {"status": "failed", "exit_code": poll}

from fastapi.staticfiles import StaticFiles

@app.get("/curriculum")
async def curriculum_stats():
    env = _get_env()
    return {"curriculum": env.curriculum.stats}

@app.get("/")
async def read_index():
    """Serve the React dashboard index.html."""
    return FileResponse("static/index.html")

# Mount static files for assets
app.mount("/", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
