"""State management for the Customer Support Environment.

Maintains the full mutable state of an episode, tracking conversation
history, actions taken, tool invocations, and scoring across steps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from cs_env.models import (
    ActionType,
    ConversationMessage,
    CustomerProfile,
    Difficulty,
    EnvironmentState,
    Observation,
    OrderRecord,
    PaymentRecord,
    TicketMetadata,
    TicketPriority,
    TicketStatus,
    ToolName,
    ToolResult,
)
from cs_env.tasks.task_registry import TaskDefinition


class EpisodeState:
    """Mutable state container for a single episode.

    Tracks everything that changes over the course of an episode:
    conversation, scores, tools used, etc. The TaskDefinition provides
    the immutable scenario data.
    """

    def __init__(self, task: TaskDefinition) -> None:
        self._task = task.copy()  # Deep copy to avoid mutation

        # Core state
        self.ticket: TicketMetadata = self._task.ticket.model_copy(deep=True)
        self.customer: CustomerProfile = self._task.customer.model_copy(deep=True)
        self.orders: list[OrderRecord] = [o.model_copy(deep=True) for o in self._task.orders]
        self.payments: list[PaymentRecord] = [p.model_copy(deep=True) for p in self._task.payments]

        # Conversation
        self.conversation: list[ConversationMessage] = list(self._task.initial_messages)

        # Tracking
        self.step_count: int = 0
        self.total_reward: float = 0.001
        self.step_score_history: list[float] = []
        self.actions_taken: list[dict[str, Any]] = []
        self.tools_used: list[str] = []
        self.tool_results: list[ToolResult] = []
        self.done: bool = False
        self.resolution_achieved: bool = False
        self.escalated: bool = False

        # Anti-exploitation
        self._reply_hashes: list[int] = []
        self._consecutive_invalid: int = 0

        # Time tracking
        self._start_time: datetime = datetime.now(timezone.utc)
        self._time_limit: int = self._task.time_limit_seconds

    # ── Properties ────────────────────────────────────────

    @property
    def task(self) -> TaskDefinition:
        return self._task

    @property
    def task_id(self) -> str:
        return self._task.task_id

    @property
    def difficulty(self) -> Difficulty:
        return self._task.difficulty

    @property
    def max_steps(self) -> int:
        return self._task.max_steps

    @property
    def time_remaining(self) -> int:
        elapsed = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        return max(0, int(self._time_limit - elapsed))

    @property
    def last_customer_message(self) -> str:
        for msg in reversed(self.conversation):
            if msg.role == "customer":
                return msg.content
        return ""

    @property
    def gold_actions(self) -> list[dict[str, Any]]:
        return self._task.gold_actions

    @property
    def required_tools(self) -> list[str]:
        return self._task.required_tools

    @property
    def required_actions(self) -> list[str]:
        return self._task.required_actions

    @property
    def resolution_criteria(self) -> dict[str, Any]:
        return self._task.resolution_criteria

    # ── State Mutation ────────────────────────────────────

    def add_agent_message(self, content: str) -> None:
        self.conversation.append(
            ConversationMessage(
                role="agent",
                content=content,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def add_system_message(self, content: str) -> None:
        self.conversation.append(
            ConversationMessage(
                role="system",
                content=content,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def record_action(self, action_dict: dict[str, Any]) -> None:
        self.actions_taken.append(action_dict)
        self.step_count += 1

    def record_tool_use(self, tool_name: str, result: ToolResult) -> None:
        self.tools_used.append(tool_name)
        self.tool_results.append(result)

    def record_step_score(self, score: float, reward: float) -> None:
        self.step_score_history.append(score)
        self.total_reward += reward

    def mark_resolved(self) -> None:
        self.resolution_achieved = True
        self.ticket.status = TicketStatus.RESOLVED

    def mark_escalated(self, reason: str = "") -> None:
        self.escalated = True
        self.ticket.status = TicketStatus.ESCALATED
        self.ticket.escalation_level += 1

    def mark_closed(self) -> None:
        self.ticket.status = TicketStatus.CLOSED

    def mark_done(self) -> None:
        self.done = True

    def update_priority(self, priority: TicketPriority) -> None:
        self.ticket.priority = priority
        self.ticket.updated_at = datetime.now(timezone.utc).isoformat()

    # ── Anti-exploitation ─────────────────────────────────

    def check_repetition(self, message: str) -> bool:
        """Returns True if the message is a repeat of a recent reply."""
        msg_hash = hash(message.strip().lower())
        is_repeat = msg_hash in self._reply_hashes[-5:]
        self._reply_hashes.append(msg_hash)
        return is_repeat

    def record_invalid_action(self) -> int:
        self._consecutive_invalid += 1
        return self._consecutive_invalid

    def reset_invalid_streak(self) -> None:
        self._consecutive_invalid = 0

    @property
    def consecutive_invalid_actions(self) -> int:
        return self._consecutive_invalid

    # ── Serialization ─────────────────────────────────────

    def to_observation(self) -> Observation:
        """Build an Observation for the agent from current state."""
        # Limit conversation history (last 5 turns)
        history_limit = 5

        hints = self._task.hints if self.difficulty in (Difficulty.EASY, Difficulty.MEDIUM) else []

        return Observation(
            ticket=self.ticket.model_copy(deep=True),
            last_customer_message=self.last_customer_message,
            conversation_history=self.conversation[-history_limit:],
            available_tools=list(ToolName),
            tool_results=self.tool_results[-3:],  # Last 3 tool results
            step_number=self.step_count,
            max_steps=self.max_steps,
            time_remaining_seconds=self.time_remaining,
            hints=hints,
            difficulty=self.difficulty,
        )

    def to_environment_state(self) -> EnvironmentState:
        """Build the full state for debugging / inspection."""
        return EnvironmentState(
            ticket=self.ticket.model_copy(deep=True),
            customer=self.customer.model_copy(deep=True),
            orders=[o.model_copy(deep=True) for o in self.orders],
            payments=[p.model_copy(deep=True) for p in self.payments],
            conversation=list(self.conversation),
            step_count=self.step_count,
            max_steps=self.max_steps,
            total_reward=self.total_reward,
            step_score_history=list(self.step_score_history),
            actions_taken=list(self.actions_taken),
            tools_used=list(self.tools_used),
            difficulty=self.difficulty,
            task_id=self.task_id,
            done=self.done,
            resolution_achieved=self.resolution_achieved,
            escalated=self.escalated,
            gold_actions=self.gold_actions,
            required_tools=self.required_tools,
            required_actions=self.required_actions,
        )
