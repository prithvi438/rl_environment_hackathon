"""Deterministic grading system for the Customer Support Environment.

Provides episode-level grading with multi-factor scoring,
anti-cheat logic, and a final composite score.

Final score = 0.6 * task_completion + 0.4 * average_step_score
"""

import os
import json
import logging
from openai import OpenAI
from typing import Any
from cs_env.models import ActionType, Difficulty
from cs_env.state import EpisodeState


class LLMJudge:
    """LLM-based judge for qualitative evaluation of conversation.

    Uses the same OpenAI client configuration as inference.py:
      HF_TOKEN / OPENAI_API_KEY  — API key
      API_BASE_URL               — OpenAI-compatible base URL
      MODEL_NAME                 — Model identifier
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self._api_key = api_key or os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY") or "sk-dummy-key-to-prevent-startup-crash"
        self._base_url = base_url or os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
        self._model = model or os.environ.get("MODEL_NAME", "gpt-4o-mini")
        self._client = OpenAI(base_url=self._base_url, api_key=self._api_key, max_retries=3)

    def evaluate(self, state: EpisodeState) -> dict[str, Any]:
        """Call LLM to evaluate the conversation quality."""
        # Only take the last 5 turns to avoid context overflow
        history = state.conversation[-5:]
        formatted_history = "\n".join([f"{m.role}: {m.content}" for m in history])

        prompt = f"""You are an expert customer support auditor. Evaluate this interaction.
        
CRITERIA:
1. Tone & Empathy (0-10): Is the agent professional, polite, and empathetic?
2. Technical Accuracy (0-10): Did the agent provide correct info and use the right tools?
3. Efficiency (0-10): Did the agent resolve the issue without unnecessary steps?

CONTEXT:
Task: {state.task.title}
Issue: {state.ticket.subject}
History:
{formatted_history}

RESPONSE FORMAT (ONLY JSON):
{{"tone_points": 0-10, "accuracy_points": 0-10, "efficiency_points": 0-10, "reasoning": "..."}}
"""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            total_llm_points = result.get("tone_points", 0) + result.get("accuracy_points", 0) + result.get("efficiency_points", 0)
            return {
                "points": float(total_llm_points),  # 0-30 total
                "reasoning": result.get("reasoning", "No reason provided")
            }
        except Exception as e:
            logging.error(f"LLM Judge evaluation failed: {e}")
            return {"points": 15.0, "reasoning": "Fallback points due to LLM error"}

class Grader:
    """Hybrid episode grader combining rules and LLM evaluation.

    Evaluates the agent's full episode performance:
    - 70% Deterministic (Completion + Step Accuracy)
    - 30% Qualitative (LLM Judge)
    """

    DETERMINISTIC_WEIGHT = 0.7
    LLM_JUDGE_WEIGHT = 0.3

    def __init__(self, api_key: str | None = None) -> None:
        self._llm_judge = LLMJudge(api_key=api_key)

    def grade(self, state: EpisodeState) -> dict[str, Any]:
        """Grade a completed episode. Returns detailed results."""
        task_completion = self._compute_task_completion(state)
        avg_step = self._compute_avg_step_score(state)
        llm_eval = self._llm_judge.evaluate(state)
        
        # Rule-based component (0.0 - 1.0)
        rule_score = (task_completion * 0.6) + (avg_step * 0.4)
        
        # Hybrid combination
        final_score = (self.DETERMINISTIC_WEIGHT * rule_score) + (self.LLM_JUDGE_WEIGHT * (llm_eval["points"] / 30.0))
        
        anti_cheat = self._anti_cheat_adjustment(state)
        # Ensure factor is strictly in (0, 1)
        anti_cheat = max(0.001, min(0.999, anti_cheat))
        final_score = max(0.001, min(0.999, final_score * anti_cheat))

        return {
            "final_score": float(final_score),
            "task_completion": float(max(0.001, min(0.999, task_completion))),
            "average_step_score": float(max(0.001, min(0.999, avg_step))),
            "llm_evaluation_points": round(llm_eval["points"], 2),
            "llm_reasoning": llm_eval["reasoning"],
            "anti_cheat_factor": float(anti_cheat),
            "breakdown": self._detailed_breakdown(state),
            "episode_stats": {
                "steps_taken": state.step_count,
                "max_steps": state.max_steps,
                "tools_used": list(set(state.tools_used)),
                "actions_taken": [a.get("type") for a in state.actions_taken],
                "resolution_achieved": state.resolution_achieved,
                "escalated": state.escalated,
                "difficulty": state.difficulty.value,
                "task_id": state.task_id,
            },
        }

    def _compute_task_completion(self, state: EpisodeState) -> float:
        """Score task completion based on resolution criteria (0-1)."""
        criteria = state.resolution_criteria
        if not criteria:
            return 0.5  # No criteria defined

        checks: list[bool] = []
        actions_done = {a.get("type") for a in state.actions_taken}
        msgs = " ".join(
            m.content.lower()
            for m in state.conversation
            if m.role == "agent"
        )

        # Check required action types
        for req in state.required_actions:
            checks.append(req in actions_done)

        # Check required tools used
        tools_used_set = set(state.tools_used)
        for tool in state.required_tools:
            checks.append(tool in tools_used_set)

        # Must-mention keywords
        if "must_mention" in criteria:
            for keyword in criteria["must_mention"]:
                checks.append(keyword.lower() in msgs)

        # Resolution-specific checks
        if criteria.get("must_process_refund"):
            checks.append("refund" in actions_done)

        if criteria.get("must_escalate"):
            checks.append(state.escalated)

        if criteria.get("must_de_escalate"):
            empathy_present = any(
                w in msgs for w in ["sorry", "apologize", "understand"]
            )
            checks.append(empathy_present)

        if criteria.get("must_not_process_refund"):
            checks.append("refund" not in actions_done)

        if criteria.get("must_identify_discrepancy"):
            discrepancy_words = ["discrepancy", "mismatch", "records show", "different"]
            checks.append(any(w in msgs for w in discrepancy_words))

        if criteria.get("must_address_all_orders"):
            # Check that multiple order IDs were mentioned
            order_mentions = sum(
                1 for a in state.actions_taken
                if a.get("type") == "lookup" and a.get("tool") == "order_database"
            )
            checks.append(order_mentions >= 1)

        if criteria.get("must_address_wrong_item"):
            checks.append(
                any(w in msgs for w in ["wrong", "incorrect", "replacement"])
            )

        if criteria.get("must_address_overcharge"):
            checks.append(
                any(w in msgs for w in ["overcharge", "price", "$10", "difference"])
            )

        if not checks:
            return 0.5

        return sum(checks) / len(checks)

    def _compute_avg_step_score(self, state: EpisodeState) -> float:
        """Average normalized step score (0-1)."""
        if not state.step_score_history:
            return 0.001
        avg = sum(state.step_score_history) / len(state.step_score_history)
        return max(0.001, min(0.999, avg))

    def _anti_cheat_adjustment(self, state: EpisodeState) -> float:
        """Detect and penalize exploitative behavior (multiplier 0-1)."""
        multiplier = 1.0

        # Penalty for too few steps (gaming the system)
        if state.step_count <= 1 and state.difficulty != Difficulty.EASY:
            multiplier *= 0.3

        # Penalty for excessive invalid actions
        if state.consecutive_invalid_actions >= 3:
            multiplier *= 0.6

        # Penalty for never using required tools
        if state.required_tools and not state.tools_used:
            multiplier *= 0.7

        # Penalty for closing without any replies
        reply_count = sum(
            1 for a in state.actions_taken if a.get("type") == "reply"
        )
        if reply_count == 0:
            multiplier *= 0.4

        # Penalty for very short episode on complex tasks
        if state.difficulty in (Difficulty.HARD, Difficulty.EXPERT):
            if state.step_count < 3:
                multiplier *= 0.5

        return multiplier

    def _detailed_breakdown(self, state: EpisodeState) -> dict[str, Any]:
        """Generate detailed per-criterion grading breakdown."""
        criteria = state.resolution_criteria
        breakdown = {}
        actions_done = {a.get("type") for a in state.actions_taken}

        for req in state.required_actions:
            breakdown[f"action_{req}"] = req in actions_done

        tools_used_set = set(state.tools_used)
        for tool in state.required_tools:
            breakdown[f"tool_{tool}"] = tool in tools_used_set

        if criteria.get("expected_resolution"):
            exp = criteria["expected_resolution"]
            if "refund" in exp:
                breakdown["refund_processed"] = "refund" in actions_done
            if "escalat" in exp:
                breakdown["escalation_done"] = state.escalated

        breakdown["resolution_achieved"] = state.resolution_achieved

        return breakdown
