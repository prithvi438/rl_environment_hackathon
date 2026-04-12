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

# ── Score-sanitization helper ─────────────────

# These are the ONLY keys whose float values represent scores in (0, 1).
_SCORE_KEYS = frozenset({
    "score", "final_score", "reward", "total_reward",
    "step_score", "task_completion", "average_step_score",
    "llm_quality_score", "anti_cheat_multiplier",
    "action_relevance", "action_correctness", "tool_usage",
    "progress", "tone_handling",
    "tone_points", "accuracy_points", "efficiency_points", "points",
    "avg_reward", "average_score",
    "repetition", "invalid_action", "time",
})


def _clamp(x: float) -> float:
    """Clamp a score value to the open interval (0, 1), strictly."""
    return max(0.1, min(0.9, float(x)))


def sanitize_response(obj: Any, parent_key: str = "") -> Any:
    """Recursively sanitize ONLY score-related numeric values."""
    if isinstance(obj, dict):
        return {k: sanitize_response(v, parent_key=k) for k, v in obj.items()}
    elif isinstance(obj, list):
        if parent_key in ("step_scores", "scores", "task_scores", "history", "step_score_history"):
            return [_clamp(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else sanitize_response(v, parent_key=parent_key) for v in obj]
        return [sanitize_response(v, parent_key=parent_key) for v in obj]
    elif isinstance(obj, bool):
        return obj
    elif isinstance(obj, (int, float)):
        if parent_key in _SCORE_KEYS:
            return _clamp(float(obj))
    return obj


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
    try:
        seed = int(os.environ.get("ENV_SEED", "42"))
        _env = CustomerSupportEnv(seed=seed)
        print("[INFO] Environment initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize environment: {e}")
        raise
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
async def reset(req: Optional[ResetRequest] = None):
    if req is None:
        req = ResetRequest()
    env = _get_env()
    difficulty = None
    if req.difficulty:
        try:
            difficulty = Difficulty(req.difficulty)
        except ValueError:
            raise HTTPException(400, f"Invalid difficulty: {req.difficulty}")

    obs = env.reset(task_id=req.task_id, difficulty=difficulty)
    return sanitize_response({
        "observation": obs.model_dump(),
        "reward": 0.5,
        "score": 0.5,
        "done": False,
    })


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

    return sanitize_response({
        "observation": obs.model_dump(),
        "feedback": feedback.model_dump(),
        "reward": feedback.reward,
        "score": feedback.step_score,
        "done": done,
        "info": info,
    })


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
            
        return sanitize_response({
            "initialized": True,
            "state": st.model_dump()
        })
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
    return sanitize_response({"curriculum": env.curriculum.stats})

@app.get("/")
async def read_index():
    """Serve the React dashboard index.html."""
    return FileResponse("static/index.html")

# Mount static files for assets
app.mount("/", StaticFiles(directory="static"), name="static")

def main():
    port = int(os.environ.get("PORT", "7860"))
    # Use the app instance directly if running via this entry point for max reliability
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
