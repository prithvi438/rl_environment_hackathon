"""Inference script for the Customer Support OpenEnv Environment.

Runs the environment with an LLM agent and computes the final score.
Uses the server's REST API to enable live dashboard updates.

Environment Variables:
  API_BASE_URL  — OpenAI-compatible API base URL
  MODEL_NAME    — Model identifier
  GROQ_API_KEY  — Groq API key
  SERVER_URL    — Dashboard server URL (default: http://localhost:7860)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any

import httpx
from openai import OpenAI

from cs_env.models import (
    Action,
    ActionType,
    Difficulty,
    ToolName,
    Observation,
    StepFeedback,
)

# ── Configuration ─────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL") or "https://api.groq.com/openai/v1"
MODEL_NAME = os.environ.get("MODEL_NAME") or "llama-3.3-70b-versatile"
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("GROQ_API_KEY")

if not HF_TOKEN:
    log.warning("[WARNING] HF_TOKEN / GROQ_API_KEY environment variable is not set. The evaluation system must provide it.")


ENV_SEED = int(os.environ.get("ENV_SEED", "42"))
MAX_EPISODES = int(os.environ.get("MAX_EPISODES", "8"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "5"))
SLEEP_RETRIES = 1.0
SLEEP_BETWEEN_EPISODES = float(os.environ.get("SLEEP_BETWEEN_EPISODES", "2.0"))
MIN_INTER_CALL_DELAY = 1.0  # Seconds
SERVER_URL = os.environ.get("SERVER_URL", "http://localhost:7860")

_LAST_CALL_TIME = 0.0

class RemoteEnv:
    """Proxy for the CustomerSupportEnv exposed via REST API."""
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=30.0)

    def reset(self, task_id: str | None = None, difficulty: Difficulty | None = None) -> Observation:
        resp = self._client.post(f"{self.base_url}/reset", json={
            "task_id": task_id,
            "difficulty": difficulty.value if difficulty else None,
            "seed": ENV_SEED
        })
        resp.raise_for_status()
        return Observation(**resp.json()["observation"])

    def step(self, action: Action) -> tuple[Observation, StepFeedback, bool, dict[str, Any]]:
        payload = {
            "type": action.type.value,
            "message": action.message,
            "tool_name": action.tool_name.value if action.tool_name else None,
            "tool_input": action.tool_input,
            "priority_update": action.priority_update.value if action.priority_update else None,
            "escalation_reason": action.escalation_reason
        }
        resp = self._client.post(f"{self.base_url}/step", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return (
            Observation(**data["observation"]),
            StepFeedback(**data["feedback"]),
            data["done"],
            data["info"]
        )

    def state(self):
        resp = self._client.get(f"{self.base_url}/state")
        resp.raise_for_status()
        return resp.json()["state"]

    @property
    def curriculum(self):
        resp = self._client.get(f"{self.base_url}/curriculum")
        resp.raise_for_status()
        class Stats:
            def __init__(self, d): self.stats = d
        return Stats(resp.json()["curriculum"])

def rate_limit_delay():
    global _LAST_CALL_TIME
    elapsed = time.time() - _LAST_CALL_TIME
    if elapsed < MIN_INTER_CALL_DELAY:
        time.sleep(MIN_INTER_CALL_DELAY - elapsed)
    _LAST_CALL_TIME = time.time()


def retry_with_backoff(max_retries=5, initial_delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            for i in range(max_retries):
                try:
                    rate_limit_delay()
                    return func(*args, **kwargs)
                except KeyboardInterrupt:
                    log.error("\n[INTERRUPTED] User stopped the script.")
                    sys.exit(130)
                except Exception as e:
                    err_msg = str(e)
                    if "tokens per day (tpd)" in err_msg.lower():
                        log.error("[FATAL] Tokens Per Day (TPD) limit reached.")
                        sys.exit(1)
                    
                    if "429" in err_msg or "too many requests" in err_msg.lower():
                        if i == max_retries - 1:
                            raise
                        log.info("[RETRY] Rate limited. Retrying in %ds...", delay)
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise
            return None
        return wrapper
    return decorator

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("inference")


def build_system_prompt(obs_dict: dict) -> str:
    """Build the system prompt for the LLM agent."""
    return f"""You are a professional AI customer support agent.
Handle tickets using structured JSON actions.

### RULES:
1. Always be polite and empathetic.
2. Use tools to verify data before answering.
3. Respond ONLY with exactly one JSON object.

### AVAILABLE ACTIONS:
- {{"type": "reply", "message": "..."}}
- {{"type": "lookup", "tool_name": "...", "tool_input": {{...}}}}
- {{"type": "refund", "tool_input": {{"order_id": "...", "amount": ...}}}}
- {{"type": "escalate", "escalation_reason": "..."}}
- {{"type": "close"}}

### CONTEXT:
Ticket: {json.dumps(obs_dict.get('ticket', {}), indent=1)}
Available Tools: {", ".join([t.value for t in obs_dict.get('available_tools', [])])}
Recent History: {json.dumps(obs_dict.get('conversation_history', []), indent=1)}
Tool Results: {json.dumps(obs_dict.get('tool_results', []), indent=1)}
Step: {obs_dict.get('step_number')} / {obs_dict.get('max_steps')}

Take your next action. Output JSON only.
"""


def parse_action(response_text: str) -> Action:
    """Parse LLM response into an Action."""
    text = response_text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return Action(type=ActionType.REPLY, message=response_text[:500])

    action_type = data.get("type", "reply")
    try:
        at = ActionType(action_type)
    except ValueError:
        at = ActionType.REPLY

    tool_name = None
    if data.get("tool_name"):
        try:
            tool_name = ToolName(data["tool_name"])
        except ValueError:
            pass

    try:
        return Action(
            type=at,
            message=data.get("message"),
            tool_name=tool_name,
            tool_input=data.get("tool_input"),
            priority_update=data.get("priority_update"),
            escalation_reason=data.get("escalation_reason"),
        )
    except Exception:
        return Action(
            type=ActionType.REPLY,
            message=f"Processing request... (Format error: {at.value})"
        )


def run_episode(
    client: OpenAI,
    env: RemoteEnv,
    task_id: str | None = None,
    difficulty: Difficulty | None = None,
) -> dict[str, Any]:
    """Run a single episode and return the grade."""
    obs = env.reset(task_id=task_id, difficulty=difficulty)
    obs_dict = obs.model_dump()
    actual_task_id = env.state().get("task_id", "cs_task_default")

    print(f"[START] task={actual_task_id} env=CustomerSupport model={MODEL_NAME}", flush=True)

    episode_start = time.time()
    step_count = 0
    rewards: list[float] = []
    info: dict[str, Any] = {}

    try:
        while True:
            prompt = build_system_prompt(obs_dict)

            @retry_with_backoff(max_retries=MAX_RETRIES)
            def get_action():
                return client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=256,
                    response_format={"type": "json_object"}
                )

            try:
                response = get_action()
                reply = response.choices[0].message.content or ""
            except SystemExit:
                reply = '{"type": "close"}'
                done = True
                break
            except Exception as e:
                log.error("[DEBUG] LLM error: %s", e)
                reply = '{"type": "close"}'
                
            action = parse_action(reply)
            obs, feedback, done, info = env.step(action)
            obs_dict = obs.model_dump()
            step_count += 1
            
            reward = feedback.reward or 0.0
            rewards.append(reward)
            
            error_val = info.get("error", None) or "null"
            done_val = str(done).lower()
            
            # Safely represent action as a string (stripping whitespace to avoid newlines)
            action_str = repr(action.type.value)
            if action.tool_name:
                action_str = f"{action.type.value}({action.tool_name.value})"
                
            print(
                f"[STEP] step={step_count} action={action_str} reward={reward:.2f} done={done_val} error={error_val}",
                flush=True,
            )

            if done: break
    finally:
        grade = info.get("grade", {})
        score = grade.get("final_score", 0.0)
        success = score >= 0.5  # defined threshold
        success_str = str(bool(success)).lower()
        rewards_str = ",".join(f"{r:.2f}" for r in rewards)
        print(f"[END] success={success_str} steps={step_count} rewards={rewards_str}", flush=True)

    return grade


def main() -> None:
    """Main inference loop."""
    log.info(f"[INFO] Dashboard: {SERVER_URL}")
    log.info("--------------------------------------------------")

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    log.info(f"[INFO] Connecting to {SERVER_URL}...")
    try:
        env = RemoteEnv(SERVER_URL)
        httpx.get(f"{SERVER_URL}/health", timeout=2.0).raise_for_status()
    except Exception as e:
        log.error(f"[ERROR] Could not connect: {e}")
        sys.exit(1)

    all_scores: list[float] = []
    from cs_env.tasks.task_registry import TASK_REGISTRY
    task_ids = list(TASK_REGISTRY.keys())[:MAX_EPISODES]

    for i, tid in enumerate(task_ids):
        log.info("[STEP] Episode %d/%d: %s", i + 1, len(task_ids), tid)
        try:
            grade = run_episode(client, env, task_id=tid)
            all_scores.append(grade.get("final_score", 0.0))
        except Exception as e:
            log.error("[STEP] Failed: %s", e)
            all_scores.append(0.0)
        time.sleep(SLEEP_BETWEEN_EPISODES)

    avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
    stats = env.curriculum.stats

    log.info("[INFO] === RESULTS ===")
    log.info("[INFO] average_score=%.4f", avg)

    results = {
        "scores": all_scores,
        "average_score": round(avg, 4),
        "curriculum": stats,
    }
    with open("results.json", "w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    main()
