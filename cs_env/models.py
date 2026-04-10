"""Pydantic models for the Customer Support OpenEnv environment.

Defines the core data structures: Action, Observation, StepFeedback,
EnvironmentState, and all supporting types used throughout the system.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Sentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"


class ActionType(str, enum.Enum):
    REPLY = "reply"
    LOOKUP = "lookup"
    ESCALATE = "escalate"
    CLOSE = "close"
    REFUND = "refund"
    UPDATE_TICKET = "update_ticket"
    INTERNAL_NOTE = "internal_note"


class ToolName(str, enum.Enum):
    CRM_LOOKUP = "crm_lookup"
    ORDER_DATABASE = "order_database"
    PAYMENT_SYSTEM = "payment_system"
    KNOWLEDGE_BASE = "knowledge_base"


# ──────────────────────────────────────────────
# Supporting Models
# ──────────────────────────────────────────────

class CustomerProfile(BaseModel):
    """Customer information from the CRM."""
    customer_id: str
    name: str
    email: str
    phone: Optional[str] = None
    account_tier: Literal["free", "basic", "premium", "enterprise"] = "basic"
    account_created: str
    lifetime_value: float = 0.001
    previous_tickets: int = 0
    satisfaction_rating: Optional[float] = None


class OrderRecord(BaseModel):
    """An order from the order database."""
    order_id: str
    customer_id: str
    product_name: str
    quantity: int = 1
    price: float
    status: Literal["pending", "processing", "shipped", "delivered", "cancelled", "returned"]
    order_date: str
    delivery_date: Optional[str] = None
    tracking_number: Optional[str] = None


class PaymentRecord(BaseModel):
    """A payment/refund record."""
    payment_id: str
    order_id: str
    amount: float
    method: Literal["credit_card", "debit_card", "paypal", "bank_transfer"]
    status: Literal["completed", "pending", "failed", "refunded", "partially_refunded"]
    timestamp: str


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""
    role: Literal["customer", "agent", "system"]
    content: str
    timestamp: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result returned from a tool invocation."""
    tool: ToolName
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class TicketMetadata(BaseModel):
    """Metadata attached to a support ticket."""
    ticket_id: str
    subject: str
    category: str
    priority: TicketPriority
    status: TicketStatus = TicketStatus.OPEN
    sentiment: Sentiment = Sentiment.NEUTRAL
    customer_id: str
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)
    escalation_level: int = 0
    assigned_agent: Optional[str] = None


# ──────────────────────────────────────────────
# Core OpenEnv Models
# ──────────────────────────────────────────────

class Action(BaseModel):
    """Structured action that the agent can take.
    
    Actions are NOT plain text — they are typed and validated.
    Each action type has specific required and optional fields.
    """
    type: ActionType
    message: Optional[str] = None
    tool_name: Optional[ToolName] = None
    tool_input: Optional[dict[str, Any]] = None
    priority_update: Optional[TicketPriority] = None
    escalation_reason: Optional[str] = None

    @field_validator("message")
    @classmethod
    def message_required_for_reply(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("type") == ActionType.REPLY and not v:
            raise ValueError("Message is required for reply actions")
        return v

    @field_validator("tool_name")
    @classmethod
    def tool_required_for_lookup(cls, v: Optional[ToolName], info) -> Optional[ToolName]:
        if info.data.get("type") == ActionType.LOOKUP and not v:
            raise ValueError("tool_name is required for lookup actions")
        return v


class Observation(BaseModel):
    """What the agent observes at each step.
    
    Contains the current ticket state, conversation history,
    available tools, and contextual information.
    """
    ticket: TicketMetadata
    last_customer_message: str
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    available_tools: list[ToolName] = Field(
        default_factory=lambda: list(ToolName)
    )
    tool_results: list[ToolResult] = Field(default_factory=list)
    step_number: int = 0
    max_steps: int = 15
    time_remaining_seconds: int = 300
    hints: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.EASY


class StepFeedback(BaseModel):
    """Feedback returned after each step, including scoring.
    
    Provides both a human-readable score (0.001 - 0.999) and a
    normalized reward (0.001 - 0.999) for RL training.
    """
    step_score: float = Field(gt=0.0, lt=1.0, description="Score from 0-1")
    reward: float = Field(gt=0.0, lt=1.0, description="Normalized reward 0-1")
    done: bool = False
    reason: Optional[str] = None
    evaluation_breakdown: dict[str, float] = Field(default_factory=dict)
    penalties: dict[str, float] = Field(default_factory=dict)


class EnvironmentState(BaseModel):
    """Full internal state of the environment, for inspection/debugging."""
    ticket: TicketMetadata
    customer: CustomerProfile
    orders: list[OrderRecord] = Field(default_factory=list)
    payments: list[PaymentRecord] = Field(default_factory=list)
    conversation: list[ConversationMessage] = Field(default_factory=list)
    step_count: int = 0
    max_steps: int = 15
    total_reward: float = 0.001
    step_score_history: list[float] = Field(default_factory=list)
    actions_taken: list[dict[str, Any]] = Field(default_factory=list)
    tools_used: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.EASY
    task_id: str = ""
    done: bool = False
    resolution_achieved: bool = False
    escalated: bool = False
    gold_actions: list[dict[str, Any]] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    required_actions: list[str] = Field(default_factory=list)
