"""Main Customer Support OpenEnv Environment.

Implements the OpenEnv interface: reset(), step(), state().
Orchestrates the task lifecycle, tool invocations, reward
computation, grading, and curriculum progression.
"""

from __future__ import annotations

from typing import Any, Optional

from cs_env.curriculum import CurriculumManager
from cs_env.grader import Grader
from cs_env.models import (
    Action,
    ActionType,
    Difficulty,
    EnvironmentState,
    Observation,
    StepFeedback,
    ToolName,
)
from cs_env.reward import RewardCalculator
from cs_env.state import EpisodeState
from cs_env.tools import ToolRegistry


class CustomerSupportEnv:
    """OpenEnv-compatible Customer Support Operations Environment.

    Simulates a real-world customer support workflow where an AI agent
    handles tickets, uses tools (CRM, orders, payments), and is
    evaluated with dense step-level rewards and deterministic grading.

    Usage
    -----
    >>> env = CustomerSupportEnv(seed=42)
    >>> obs = env.reset()
    >>> obs, reward, done, info = env.step(Action(type="reply", message="Hello!"))
    >>> full_state = env.state()
    """

    def __init__(
        self,
        seed: Optional[int] = 42,
        curriculum_window: int = 3,
        promote_threshold: float = 0.75,
        demote_threshold: float = 0.30,
        api_key: Optional[str] = None,
    ) -> None:
        self._curriculum = CurriculumManager(
            window_size=curriculum_window,
            promote_threshold=promote_threshold,
            demote_threshold=demote_threshold,
            seed=seed,
        )
        self._reward_calc = RewardCalculator()
        self._grader = Grader(api_key=api_key)
        self._tools = ToolRegistry()
        self._episode: Optional[EpisodeState] = None
        self._last_grade: Optional[dict[str, Any]] = None

    # ── OpenEnv Interface ─────────────────────────────────

    def reset(
        self,
        task_id: Optional[str] = None,
        difficulty: Optional[Difficulty] = None,
    ) -> Observation:
        """Reset and start a new episode.

        Parameters
        ----------
        task_id : str, optional
            Force a specific task. If None, curriculum selects one.
        difficulty : Difficulty, optional
            Force a difficulty level for task selection.
        """
        from cs_env.tasks.task_registry import TASK_REGISTRY

        if task_id and task_id in TASK_REGISTRY:
            task = TASK_REGISTRY[task_id].copy()
        else:
            task = self._curriculum.select_task(force_difficulty=difficulty)

        # Initialize episode state
        self._episode = EpisodeState(task)
        self._last_grade = None

        # Load tool data
        self._tools.clear()
        self._tools.load_customer(self._episode.customer)
        for order in self._episode.orders:
            self._tools.load_order(order)
        for payment in self._episode.payments:
            self._tools.load_payment(payment)
        self._tools.load_knowledge_base(task.knowledge_base)

        return self._episode.to_observation()

    def step(self, action: Action) -> tuple[Observation, StepFeedback, bool, dict[str, Any]]:
        """Execute one step in the environment.

        Parameters
        ----------
        action : Action
            The structured action to take.

        Returns
        -------
        tuple of (Observation, StepFeedback, bool, dict)
            observation, reward/feedback, done flag, info dict
        """
        if self._episode is None:
            raise RuntimeError("Call reset() before step()")

        if self._episode.done:
            raise RuntimeError("Episode is done. Call reset() to start a new one.")

        # Process the action
        self._process_action(action)

        # Compute reward
        feedback = self._reward_calc.compute(action, self._episode)

        # Record step
        self._episode.record_step_score(feedback.step_score, feedback.reward)

        # Handle episode termination
        if feedback.done:
            self._episode.mark_done()
            if action.type == ActionType.CLOSE:
                self._episode.mark_resolved()
            grade = self._grader.grade(self._episode)
            self._last_grade = grade
            self._curriculum.record_episode_reward(grade["final_score"])
            info = {
                "grade": grade,
                "curriculum": self._curriculum.stats,
            }
        else:
            info = {
                "step": self._episode.step_count,
                "tools_used": list(set(self._episode.tools_used)),
            }

        obs = self._episode.to_observation()
        return obs, feedback, feedback.done, info

    def state(self) -> EnvironmentState:
        """Return the full internal state (for debugging/inspection)."""
        if self._episode is None:
            raise RuntimeError("No active episode. Call reset() first.")
        return self._episode.to_environment_state()

    # ── Action Processing ─────────────────────────────────

    def _process_action(self, action: Action) -> None:
        """Process an action, updating state and invoking tools."""
        ep = self._episode
        action_record: dict[str, Any] = {"type": action.type.value}

        if action.type == ActionType.REPLY:
            ep.add_agent_message(action.message or "")
            action_record["message"] = action.message
            ep.reset_invalid_streak()

        elif action.type == ActionType.LOOKUP:
            if action.tool_name:
                result = self._tools.invoke(action.tool_name, action.tool_input)
                ep.record_tool_use(action.tool_name.value, result)
                ep.add_system_message(
                    f"[Tool: {action.tool_name.value}] "
                    f"{'Success' if result.success else 'Failed'}: "
                    f"{result.data if result.success else result.error}"
                )
                action_record["tool"] = action.tool_name.value
                action_record["tool_input"] = action.tool_input
                action_record["tool_success"] = result.success
                ep.reset_invalid_streak()
            else:
                ep.record_invalid_action()
                ep.add_system_message("[System] Lookup action requires a tool_name.")

        elif action.type == ActionType.ESCALATE:
            reason = action.escalation_reason or "Agent escalation"
            ep.mark_escalated(reason)
            ep.add_system_message(f"[System] Ticket escalated: {reason}")
            action_record["reason"] = reason
            ep.reset_invalid_streak()

        elif action.type == ActionType.CLOSE:
            ep.mark_closed()
            ep.add_system_message("[System] Ticket closed by agent.")
            ep.reset_invalid_streak()

        elif action.type == ActionType.REFUND:
            inp = action.tool_input or {}
            inp["action"] = "refund"
            result = self._tools.invoke(ToolName.PAYMENT_SYSTEM, inp)
            ep.record_tool_use("payment_system", result)
            ep.add_system_message(
                f"[Refund] {'Processed' if result.success else 'Failed'}: "
                f"{result.data if result.success else result.error}"
            )
            action_record["tool_input"] = inp
            action_record["refund_success"] = result.success
            ep.reset_invalid_streak()

        elif action.type == ActionType.UPDATE_TICKET:
            if action.priority_update:
                ep.update_priority(action.priority_update)
                ep.add_system_message(
                    f"[System] Ticket priority updated to {action.priority_update.value}"
                )
                action_record["priority"] = action.priority_update.value
            ep.reset_invalid_streak()

        elif action.type == ActionType.INTERNAL_NOTE:
            ep.add_system_message(f"[Internal Note] {action.message or 'No content'}")
            action_record["note"] = action.message
            ep.reset_invalid_streak()

        else:
            ep.record_invalid_action()

        ep.record_action(action_record)

    # ── Accessors ─────────────────────────────────────────

    @property
    def curriculum(self) -> CurriculumManager:
        return self._curriculum

    @property
    def last_grade(self) -> Optional[dict[str, Any]]:
        return self._last_grade

    @property
    def is_done(self) -> bool:
        return self._episode.done if self._episode else True
