"""Dense reward shaping for the Customer Support Environment.

Computes step-level scores (1-100) and normalized rewards (0-1)
based on multiple factors: action relevance, tone handling,
tool usage correctness, and anti-exploitation penalties.
"""

from __future__ import annotations

from typing import Any

from cs_env.models import (
    Action,
    ActionType,
    Difficulty,
    Sentiment,
    StepFeedback,
    ToolName,
)
from cs_env.state import EpisodeState


# Difficulty multipliers — harder tasks have tighter scoring
_DIFFICULTY_MULTIPLIER = {
    Difficulty.EASY: 1.0,
    Difficulty.MEDIUM: 0.95,
    Difficulty.HARD: 0.90,
    Difficulty.EXPERT: 0.85,
}


class RewardCalculator:
    """Computes dense, multi-factor rewards for each step."""

    def __init__(self) -> None:
        self._max_repetition_penalty = 0.4
        self._max_invalid_penalty = 0.5
        self._time_penalty_weight = 0.05

    def compute(self, action: Action, state: EpisodeState) -> StepFeedback:
        """Compute step feedback for the given action in the current state."""
        breakdown: dict[str, float] = {}
        penalties: dict[str, float] = {}

        # 1. Action relevance score (0-30 points)
        relevance = self._score_action_relevance(action, state)
        breakdown["action_relevance"] = relevance

        # 2. Action correctness (0-25 points)
        correctness = self._score_action_correctness(action, state)
        breakdown["action_correctness"] = correctness

        # 3. Tool usage score (0-15 points)
        tool_score = self._score_tool_usage(action, state)
        breakdown["tool_usage"] = tool_score

        # 4. Progress bonus (0-0 points) - Moved to deterministic completion in grader
        breakdown["progress"] = 0.0

        # Tone/Sentiment (0-0 points) - Moved to LLM Judge for nuanced evaluation
        breakdown["tone_handling"] = 0.0

        raw_score = sum(breakdown.values())

        # Apply penalties
        rep_penalty = self._repetition_penalty(action, state)
        if rep_penalty > 0:
            penalties["repetition"] = rep_penalty

        invalid_penalty = self._invalid_action_penalty(action, state)
        if invalid_penalty > 0:
            penalties["invalid_action"] = invalid_penalty

        time_penalty = self._time_penalty(state)
        if time_penalty > 0:
            penalties["time"] = time_penalty

        total_penalty = sum(penalties.values())

        # Difficulty multiplier
        mult = _DIFFICULTY_MULTIPLIER.get(state.difficulty, 1.0)

        # Final score: clamp to 0.001-0.999
        final = max(0.001, min(0.999, (raw_score * mult) - (total_penalty)))

        # Check if episode should end
        done = self._check_done(action, state)
        reason = self._get_done_reason(action, state) if done else None

        return StepFeedback(
            step_score=round(final, 4),
            reward=round(final, 4),
            done=done,
            reason=reason,
            scoring_breakdown={k: round(v, 2) for k, v in breakdown.items()},
            penalties={k: round(v, 4) for k, v in penalties.items()},
        )

    # ── Scoring Components ────────────────────────────────

    def _score_action_relevance(self, action: Action, state: EpisodeState) -> float:
        """How relevant is this action type at the current step? (0-30)"""
        gold = state.gold_actions
        step = state.step_count
        action_type = action.type.value

        # Check if this action type appears in gold actions
        gold_types = [g["type"] for g in gold]
        if action_type in gold_types:
            # Bonus if it's the right action at roughly the right time
            expected_idx = gold_types.index(action_type)
            distance = abs(step - expected_idx)
            if distance <= 1:
                return 0.30
            elif distance <= 3:
                return 0.22
            else:
                return 0.15

        # Action type not in gold but still reasonable
        if action_type in ("reply", "lookup"):
            return 0.10

        return 0.05

    def _score_action_correctness(self, action: Action, state: EpisodeState) -> float:
        """Is the action content correct? (0-25)"""
        score = 0.0

        if action.type == ActionType.REPLY and action.message:
            # Check for keyword matches against gold actions
            for gold in state.gold_actions:
                if gold.get("type") == "reply" and "keywords" in gold:
                    keywords = gold["keywords"]
                    msg_lower = action.message.lower()
                    matches = sum(1 for kw in keywords if kw.lower() in msg_lower)
                    ratio = matches / max(len(keywords), 1)
                    score = max(score, ratio * 0.25)

            # Minimum score for non-empty relevant replies
            if score == 0.0 and len(action.message) > 20:
                score = 0.08

        elif action.type == ActionType.LOOKUP:
            # Check if this is a required tool lookup
            tool = action.tool_name.value if action.tool_name else ""
            if tool in state.required_tools:
                score = 0.20
                # Bonus for correct input
                for gold in state.gold_actions:
                    if gold.get("tool") == tool and "input" in gold:
                        if action.tool_input and all(
                            action.tool_input.get(k) == v
                            for k, v in gold["input"].items()
                        ):
                            score = 0.25
                            break
            else:
                score = 0.10  # Exploratory lookup

        elif action.type == ActionType.ESCALATE:
            if "escalate" in state.required_actions:
                score = 0.25
            else:
                score = 0.10  # Unnecessary escalation

        elif action.type == ActionType.REFUND:
            if "refund" in state.required_actions:
                criteria = state.resolution_criteria
                exp_amount = criteria.get("refund_amount")
                exp_order = criteria.get("refund_order_id")
                inp = action.tool_input or {}
                if inp.get("order_id") == exp_order:
                    if exp_amount and abs(float(inp.get("amount", 0)) - exp_amount) < 0.01:
                        score = 0.25
                    else:
                        score = 0.18
                else:
                    score = 0.08
            else:
                score = 0.03  # Wrong action

        elif action.type == ActionType.CLOSE:
            if "close" in state.required_actions:
                # Only good if we've made progress
                if state.step_count >= 2:
                    score = 0.25
                else:
                    score = 0.05  # Premature close
            else:
                score = 0.05

        elif action.type == ActionType.INTERNAL_NOTE:
            if "internal_note" in state.required_actions:
                score = 0.20
            else:
                score = 0.12

        elif action.type == ActionType.UPDATE_TICKET:
            if "update_ticket" in state.required_actions:
                score = 0.20
            else:
                score = 0.10

        return score

    def _score_tone_handling(self, action: Action, state: EpisodeState) -> float:
        """Did the agent handle sentiment appropriately? (0-15)"""
        if action.type != ActionType.REPLY or not action.message:
            return 0.07  # Neutral for non-reply actions

        sentiment = state.ticket.sentiment
        msg = action.message.lower()

        if sentiment in (Sentiment.ANGRY, Sentiment.FRUSTRATED):
            empathy_words = ["sorry", "apologize", "understand", "frustrat", "inconvenience"]
            matches = sum(1 for w in empathy_words if w in msg)
            if matches >= 2:
                return 0.15
            elif matches == 1:
                return 0.10
            else:
                return 0.03

        elif sentiment == Sentiment.CONFUSED:
            clarity_words = ["let me explain", "here's how", "step", "first", "simply"]
            matches = sum(1 for w in clarity_words if w in msg)
            return min(0.15, 0.08 + matches * 2.5)

        else:  # NEUTRAL or POSITIVE
            professional_words = ["happy to help", "assist", "please", "thank"]
            matches = sum(1 for w in professional_words if w in msg)
            return min(0.15, 0.08 + matches * 2.0)

    def _score_tool_usage(self, action: Action, state: EpisodeState) -> float:
        """Was the right tool used correctly? (0-15)"""
        if action.type != ActionType.LOOKUP:
            # Check if tools should have been used by now
            required = state.required_tools
            used = set(state.tools_used)
            if required and not used and state.step_count > 2:
                return 0.03  # Should have used tools by now
            return 0.08  # N/A

        tool = action.tool_name.value if action.tool_name else ""
        if tool in state.required_tools:
            if tool not in state.tools_used:
                return 0.15  # First use of required tool
            else:
                return 0.08  # Redundant but not wrong
        return 0.06  # Non-required tool

    def _score_progress(self, action: Action, state: EpisodeState) -> float:
        """How much does this step advance toward resolution? (0-15)"""
        required = set(state.required_actions)
        done_types = {a.get("type") for a in state.actions_taken}
        action_type = action.type.value

        if action_type in required and action_type not in done_types:
            # New required action being performed
            completion = (len(done_types & required) + 1) / max(len(required), 1)
            return completion * 0.15

        if action.type == ActionType.CLOSE and state.resolution_achieved:
            return 0.15

        if action.type == ActionType.ESCALATE and "escalate" in required:
            return 0.15

        return 0.05

    # ── Penalties ─────────────────────────────────────────

    def _repetition_penalty(self, action: Action, state: EpisodeState) -> float:
        if action.type == ActionType.REPLY and action.message:
            if state.check_repetition(action.message):
                return self._max_repetition_penalty
        return 0.0

    def _invalid_action_penalty(self, action: Action, state: EpisodeState) -> float:
        # Penalize closing without progress
        if action.type == ActionType.CLOSE and state.step_count < 2:
            return 0.3

        # Penalize refund on wrong criteria
        criteria = state.resolution_criteria
        if criteria.get("must_not_process_refund") and action.type == ActionType.REFUND:
            return self._max_invalid_penalty

        return 0.0

    def _time_penalty(self, state: EpisodeState) -> float:
        remaining_ratio = state.time_remaining / max(state.task.time_limit_seconds, 1)
        if remaining_ratio < 0.1:
            return self._time_penalty_weight * 2
        elif remaining_ratio < 0.3:
            return self._time_penalty_weight
        return 0.0

    # ── Episode Termination ───────────────────────────────

    def _check_done(self, action: Action, state: EpisodeState) -> bool:
        if action.type == ActionType.CLOSE:
            return True
        if state.step_count >= state.max_steps - 1:
            return True
        if state.time_remaining <= 0:
            return True
        if state.consecutive_invalid_actions >= 5:
            return True
        if action.type == ActionType.ESCALATE:
            criteria = state.resolution_criteria
            if criteria.get("expected_resolution", "").startswith("escalated"):
                return True
        return False

    def _get_done_reason(self, action: Action, state: EpisodeState) -> str:
        if action.type == ActionType.CLOSE:
            return "ticket_closed"
        if state.step_count >= state.max_steps - 1:
            return "max_steps_reached"
        if state.time_remaining <= 0:
            return "time_expired"
        if state.consecutive_invalid_actions >= 5:
            return "too_many_invalid_actions"
        if action.type == ActionType.ESCALATE:
            return "escalated"
        return "unknown"
