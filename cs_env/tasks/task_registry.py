"""Task definitions and registry for the Customer Support Environment.

Each task is a fully self-contained scenario with:
  - Pre-loaded data (customer, orders, payments, KB articles)
  - Initial conversation messages
  - Gold-standard action sequences for deterministic grading
  - Difficulty level assignment
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from cs_env.models import (
    ActionType,
    ConversationMessage,
    CustomerProfile,
    Difficulty,
    OrderRecord,
    PaymentRecord,
    Sentiment,
    TicketMetadata,
    TicketPriority,
    TicketStatus,
    ToolName,
)


@dataclass
class TaskDefinition:
    """A complete task scenario for the environment."""
    task_id: str
    title: str
    description: str
    difficulty: Difficulty
    max_steps: int
    time_limit_seconds: int

    # Pre-loaded data
    ticket: TicketMetadata
    customer: CustomerProfile
    orders: list[OrderRecord] = field(default_factory=list)
    payments: list[PaymentRecord] = field(default_factory=list)
    knowledge_base: dict[str, str] = field(default_factory=dict)

    # Initial conversation
    initial_messages: list[ConversationMessage] = field(default_factory=list)

    # Grading: gold-standard actions and requirements
    required_actions: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    gold_actions: list[dict[str, Any]] = field(default_factory=list)
    resolution_criteria: dict[str, Any] = field(default_factory=dict)

    # Hints for the agent (fewer at higher difficulty)
    hints: list[str] = field(default_factory=list)

    def copy(self) -> TaskDefinition:
        return copy.deepcopy(self)


# ═══════════════════════════════════════════════
# TASK 1 — EASY: Password Reset FAQ
# ═══════════════════════════════════════════════

TASK_PASSWORD_RESET = TaskDefinition(
    task_id="easy_password_reset",
    title="Password Reset Request",
    description="Customer needs help resetting their account password. Simple FAQ resolution.",
    difficulty=Difficulty.EASY,
    max_steps=6,
    time_limit_seconds=300,
    ticket=TicketMetadata(
        ticket_id="TKT-1001",
        subject="Can't log into my account",
        category="account_access",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.NEUTRAL,
        customer_id="CUST-001",
        created_at="2026-04-02T08:00:00Z",
        updated_at="2026-04-02T08:00:00Z",
        tags=["login", "password", "account"],
    ),
    customer=CustomerProfile(
        customer_id="CUST-001",
        name="Sarah Chen",
        email="sarah.chen@email.com",
        phone="+1-555-0101",
        account_tier="basic",
        account_created="2025-01-15",
        lifetime_value=249.99,
        previous_tickets=1,
        satisfaction_rating=4.2,
    ),
    knowledge_base={
        "password reset": (
            "To reset your password: 1) Go to login page, 2) Click 'Forgot Password', "
            "3) Enter your registered email, 4) Check your inbox for a reset link (valid 24h), "
            "5) Create a new password (min 8 chars, 1 uppercase, 1 number). "
            "If you don't receive the email, check spam folder or contact support."
        ),
        "account locked": (
            "Accounts are locked after 5 failed login attempts. "
            "Wait 30 minutes or use the password reset flow to unlock."
        ),
    },
    initial_messages=[
        ConversationMessage(
            role="customer",
            content="Hi, I can't log into my account. I've tried my password several times but it's not working. Can you help?",
            timestamp="2026-04-02T08:00:00Z",
        ),
    ],
    required_actions=["reply", "close"],
    required_tools=[],
    gold_actions=[
        {
            "type": "reply",
            "keywords": ["password", "reset", "forgot password", "link", "email"],
            "description": "Provide password reset instructions",
        },
        {
            "type": "close",
            "description": "Close ticket after resolution",
        },
    ],
    resolution_criteria={
        "must_mention": ["password", "reset"],
        "must_provide_steps": True,
        "expected_resolution": "password_reset_instructions",
    },
    hints=[
        "The customer needs password reset instructions.",
        "Check the knowledge base for the password reset procedure.",
        "Close the ticket after providing the solution.",
    ],
)


# ═══════════════════════════════════════════════
# TASK 2 — EASY: Order Status Inquiry
# ═══════════════════════════════════════════════

TASK_ORDER_STATUS = TaskDefinition(
    task_id="easy_order_status",
    title="Order Status Inquiry",
    description="Customer wants to know where their order is. Look up order and provide tracking info.",
    difficulty=Difficulty.EASY,
    max_steps=8,
    time_limit_seconds=300,
    ticket=TicketMetadata(
        ticket_id="TKT-1002",
        subject="Where is my order?",
        category="order_tracking",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.CONFUSED,
        customer_id="CUST-002",
        created_at="2026-04-02T09:00:00Z",
        updated_at="2026-04-02T09:00:00Z",
        tags=["order", "shipping", "tracking"],
    ),
    customer=CustomerProfile(
        customer_id="CUST-002",
        name="Marcus Johnson",
        email="marcus.j@email.com",
        account_tier="premium",
        account_created="2024-06-10",
        lifetime_value=1250.00,
        previous_tickets=3,
        satisfaction_rating=3.8,
    ),
    orders=[
        OrderRecord(
            order_id="ORD-5001",
            customer_id="CUST-002",
            product_name="Wireless Noise-Cancelling Headphones",
            quantity=1,
            price=299.99,
            status="shipped",
            order_date="2026-03-28",
            delivery_date="2026-04-04",
            tracking_number="1Z999AA10123456784",
        ),
    ],
    payments=[
        PaymentRecord(
            payment_id="PAY-7001",
            order_id="ORD-5001",
            amount=299.99,
            method="credit_card",
            status="completed",
            timestamp="2026-03-28T14:00:00Z",
        ),
    ],
    initial_messages=[
        ConversationMessage(
            role="customer",
            content="I placed an order last week and still haven't received it. My order number is ORD-5001. Can you tell me what's going on?",
            timestamp="2026-04-02T09:00:00Z",
        ),
    ],
    required_actions=["lookup", "reply", "close"],
    required_tools=["order_database"],
    gold_actions=[
        {
            "type": "lookup",
            "tool": "order_database",
            "input": {"order_id": "ORD-5001"},
            "description": "Look up order status",
        },
        {
            "type": "reply",
            "keywords": ["shipped", "tracking", "1Z999AA10123456784", "april 4", "delivery"],
            "description": "Provide tracking information and estimated delivery",
        },
        {
            "type": "close",
            "description": "Close ticket after providing information",
        },
    ],
    resolution_criteria={
        "must_lookup_order": True,
        "must_provide_tracking": True,
        "must_mention": ["tracking", "shipped"],
        "expected_resolution": "order_status_provided",
    },
    hints=[
        "Look up order ORD-5001 in the order database.",
        "Provide the tracking number and estimated delivery date.",
    ],
)


# ═══════════════════════════════════════════════
# TASK 3 — MEDIUM: Refund for Damaged Product
# ═══════════════════════════════════════════════

TASK_DAMAGED_PRODUCT_REFUND = TaskDefinition(
    task_id="medium_damaged_product",
    title="Damaged Product Refund Request",
    description=(
        "Customer received a damaged product and wants a refund. "
        "Requires looking up the order, verifying the purchase, and processing a refund."
    ),
    difficulty=Difficulty.MEDIUM,
    max_steps=12,
    time_limit_seconds=420,
    ticket=TicketMetadata(
        ticket_id="TKT-2001",
        subject="Received damaged item — want refund",
        category="returns_refunds",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.FRUSTRATED,
        customer_id="CUST-003",
        created_at="2026-04-02T10:00:00Z",
        updated_at="2026-04-02T10:00:00Z",
        tags=["damaged", "refund", "product_quality"],
    ),
    customer=CustomerProfile(
        customer_id="CUST-003",
        name="Emily Rodriguez",
        email="emily.r@email.com",
        phone="+1-555-0303",
        account_tier="premium",
        account_created="2023-11-01",
        lifetime_value=3750.00,
        previous_tickets=5,
        satisfaction_rating=4.0,
    ),
    orders=[
        OrderRecord(
            order_id="ORD-5010",
            customer_id="CUST-003",
            product_name="Smart Home Hub Pro",
            quantity=1,
            price=189.99,
            status="delivered",
            order_date="2026-03-20",
            delivery_date="2026-03-25",
            tracking_number="1Z999BB20234567890",
        ),
        OrderRecord(
            order_id="ORD-5011",
            customer_id="CUST-003",
            product_name="USB-C Charging Cable (3-pack)",
            quantity=1,
            price=24.99,
            status="delivered",
            order_date="2026-03-20",
            delivery_date="2026-03-25",
        ),
    ],
    payments=[
        PaymentRecord(
            payment_id="PAY-7010",
            order_id="ORD-5010",
            amount=189.99,
            method="credit_card",
            status="completed",
            timestamp="2026-03-20T11:00:00Z",
        ),
        PaymentRecord(
            payment_id="PAY-7011",
            order_id="ORD-5011",
            amount=24.99,
            method="credit_card",
            status="completed",
            timestamp="2026-03-20T11:00:00Z",
        ),
    ],
    knowledge_base={
        "refund policy": (
            "Full refunds are available for damaged products within 30 days of delivery. "
            "Customer does not need to return damaged items under $200. "
            "Items over $200 require return shipping (prepaid label provided). "
            "Refunds are processed within 5-7 business days to the original payment method."
        ),
        "damaged product": (
            "For damaged products: 1) Verify the order and delivery, "
            "2) Confirm the damage with the customer, "
            "3) Check refund eligibility (30-day window), "
            "4) Process refund if eligible, "
            "5) Apologize and offer discount on next purchase if premium customer."
        ),
    },
    initial_messages=[
        ConversationMessage(
            role="customer",
            content=(
                "I received my Smart Home Hub Pro yesterday but the screen is completely cracked "
                "and it won't turn on. This is really frustrating — I paid almost $200 for this! "
                "I want a full refund immediately. Order ORD-5010."
            ),
            timestamp="2026-04-02T10:00:00Z",
        ),
    ],
    required_actions=["lookup", "reply", "refund", "close"],
    required_tools=["order_database", "payment_system", "crm_lookup"],
    gold_actions=[
        {
            "type": "lookup",
            "tool": "crm_lookup",
            "input": {"customer_id": "CUST-003"},
            "description": "Look up customer profile",
        },
        {
            "type": "lookup",
            "tool": "order_database",
            "input": {"order_id": "ORD-5010"},
            "description": "Verify the order exists and was delivered",
        },
        {
            "type": "reply",
            "keywords": ["sorry", "apologize", "refund", "process", "damaged"],
            "description": "Acknowledge damage and confirm refund eligibility",
        },
        {
            "type": "refund",
            "tool_input": {"order_id": "ORD-5010", "amount": 189.99},
            "description": "Process full refund for damaged item",
        },
        {
            "type": "reply",
            "keywords": ["refund", "processed", "5-7 business days", "discount"],
            "description": "Confirm refund and offer goodwill gesture",
        },
        {
            "type": "close",
            "description": "Close resolved ticket",
        },
    ],
    resolution_criteria={
        "must_verify_order": True,
        "must_process_refund": True,
        "must_apologize": True,
        "refund_order_id": "ORD-5010",
        "refund_amount": 189.99,
        "expected_resolution": "refund_processed",
    },
    hints=[
        "Look up the customer and order details first.",
        "The product is under $200, so no return shipping is needed.",
    ],
)


# ═══════════════════════════════════════════════
# TASK 4 — MEDIUM: Billing Discrepancy
# ═══════════════════════════════════════════════

TASK_BILLING_DISCREPANCY = TaskDefinition(
    task_id="medium_billing_discrepancy",
    title="Billing Discrepancy Investigation",
    description=(
        "Customer notices they were charged twice for an order. "
        "Requires investigating payment records and resolving the double charge."
    ),
    difficulty=Difficulty.MEDIUM,
    max_steps=12,
    time_limit_seconds=420,
    ticket=TicketMetadata(
        ticket_id="TKT-2002",
        subject="Charged twice for same order!",
        category="billing",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.ANGRY,
        customer_id="CUST-004",
        created_at="2026-04-02T11:00:00Z",
        updated_at="2026-04-02T11:00:00Z",
        tags=["billing", "double_charge", "payment"],
    ),
    customer=CustomerProfile(
        customer_id="CUST-004",
        name="David Kim",
        email="david.kim@email.com",
        phone="+1-555-0404",
        account_tier="basic",
        account_created="2025-03-20",
        lifetime_value=450.00,
        previous_tickets=2,
        satisfaction_rating=3.5,
    ),
    orders=[
        OrderRecord(
            order_id="ORD-5020",
            customer_id="CUST-004",
            product_name="Ergonomic Office Chair",
            quantity=1,
            price=349.99,
            status="delivered",
            order_date="2026-03-25",
            delivery_date="2026-03-30",
        ),
    ],
    payments=[
        PaymentRecord(
            payment_id="PAY-7020",
            order_id="ORD-5020",
            amount=349.99,
            method="debit_card",
            status="completed",
            timestamp="2026-03-25T09:00:00Z",
        ),
        PaymentRecord(
            payment_id="PAY-7021",
            order_id="ORD-5020",
            amount=349.99,
            method="debit_card",
            status="completed",
            timestamp="2026-03-25T09:02:00Z",
        ),
    ],
    knowledge_base={
        "double charge": (
            "Double charges can occur due to payment processing errors. "
            "Steps: 1) Verify both charges in the payment system, "
            "2) Confirm the duplicate with transaction IDs, "
            "3) Process a refund for the duplicate charge, "
            "4) Apologize and explain the processing error."
        ),
    },
    initial_messages=[
        ConversationMessage(
            role="customer",
            content=(
                "I just checked my bank statement and I was charged $349.99 TWICE for order ORD-5020! "
                "That's almost $700 taken from my account! I need this fixed right now."
            ),
            timestamp="2026-04-02T11:00:00Z",
        ),
    ],
    required_actions=["lookup", "reply", "refund", "close"],
    required_tools=["order_database", "payment_system"],
    gold_actions=[
        {
            "type": "lookup",
            "tool": "order_database",
            "input": {"order_id": "ORD-5020"},
            "description": "Verify the order",
        },
        {
            "type": "lookup",
            "tool": "payment_system",
            "input": {"order_id": "ORD-5020", "action": "lookup"},
            "description": "Check payment records for duplicate charges",
        },
        {
            "type": "reply",
            "keywords": ["duplicate", "charge", "error", "sorry", "refund"],
            "description": "Acknowledge double charge and explain",
        },
        {
            "type": "refund",
            "tool_input": {"order_id": "ORD-5020", "amount": 349.99, "reason": "duplicate_charge"},
            "description": "Refund the duplicate payment",
        },
        {
            "type": "reply",
            "keywords": ["refund", "processed", "apologize"],
            "description": "Confirm refund processed",
        },
        {
            "type": "close",
            "description": "Close ticket",
        },
    ],
    resolution_criteria={
        "must_identify_duplicate": True,
        "must_process_refund": True,
        "refund_order_id": "ORD-5020",
        "refund_amount": 349.99,
        "expected_resolution": "duplicate_refunded",
    },
    hints=[
        "Check the payment system for order ORD-5020 — there are two charges.",
    ],
)


# ═══════════════════════════════════════════════
# TASK 5 — HARD: Ambiguous Request with Angry Customer
# ═══════════════════════════════════════════════

TASK_AMBIGUOUS_ANGRY = TaskDefinition(
    task_id="hard_ambiguous_angry",
    title="Ambiguous Complaint from Angry Customer",
    description=(
        "An angry customer with multiple orders submits a vague complaint. "
        "Agent must de-escalate, identify the correct order, diagnose the issue, "
        "and resolve through the right channel. Multiple valid resolution paths."
    ),
    difficulty=Difficulty.HARD,
    max_steps=15,
    time_limit_seconds=600,
    ticket=TicketMetadata(
        ticket_id="TKT-3001",
        subject="THIS IS UNACCEPTABLE",
        category="complaint",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.ANGRY,
        customer_id="CUST-005",
        created_at="2026-04-02T12:00:00Z",
        updated_at="2026-04-02T12:00:00Z",
        tags=["complaint", "urgent", "vip"],
        escalation_level=0,
    ),
    customer=CustomerProfile(
        customer_id="CUST-005",
        name="Victoria Blackwell",
        email="v.blackwell@corp.com",
        phone="+1-555-0505",
        account_tier="enterprise",
        account_created="2022-01-01",
        lifetime_value=28500.00,
        previous_tickets=12,
        satisfaction_rating=2.1,
    ),
    orders=[
        OrderRecord(
            order_id="ORD-5030",
            customer_id="CUST-005",
            product_name="Enterprise Server Rack (42U)",
            quantity=2,
            price=4299.99,
            status="shipped",
            order_date="2026-03-15",
            delivery_date="2026-04-05",
            tracking_number="1Z999CC30345678901",
        ),
        OrderRecord(
            order_id="ORD-5031",
            customer_id="CUST-005",
            product_name="Network Switch 48-Port",
            quantity=5,
            price=899.99,
            status="processing",
            order_date="2026-03-28",
        ),
        OrderRecord(
            order_id="ORD-5032",
            customer_id="CUST-005",
            product_name="Cat6 Ethernet Cable (100-pack)",
            quantity=3,
            price=149.99,
            status="cancelled",
            order_date="2026-03-10",
        ),
    ],
    payments=[
        PaymentRecord(
            payment_id="PAY-7030",
            order_id="ORD-5030",
            amount=8599.98,
            method="bank_transfer",
            status="completed",
            timestamp="2026-03-15T10:00:00Z",
        ),
        PaymentRecord(
            payment_id="PAY-7031",
            order_id="ORD-5031",
            amount=4499.95,
            method="bank_transfer",
            status="pending",
            timestamp="2026-03-28T14:00:00Z",
        ),
    ],
    knowledge_base={
        "enterprise support": (
            "Enterprise customers get priority support, dedicated account managers, "
            "and SLA guarantees. Escalate to Tier 2 if resolution is not within SLA. "
            "Always address enterprise customers professionally and acknowledge their importance."
        ),
        "cancelled order": (
            "Cancelled orders: Verify cancellation reason. If cancelled by system, "
            "investigate and offer to re-place the order. If cancelled by customer, "
            "confirm and process any pending refunds."
        ),
        "bulk order delay": (
            "Bulk orders may have extended processing times. Check with warehouse "
            "for availability. Offer partial shipment if items are in stock. "
            "Provide realistic delivery estimates."
        ),
    },
    initial_messages=[
        ConversationMessage(
            role="customer",
            content=(
                "I've had it with your company! I placed multiple orders and NOTHING is going right. "
                "One got cancelled without anyone telling me, another one is taking forever, "
                "and I still haven't received the server racks I ordered WEEKS ago. "
                "I'm an enterprise customer paying thousands of dollars and this is how you treat me? "
                "Fix ALL of this NOW or I'm switching vendors."
            ),
            timestamp="2026-04-02T12:00:00Z",
        ),
    ],
    required_actions=["lookup", "reply", "escalate"],
    required_tools=["crm_lookup", "order_database"],
    gold_actions=[
        {
            "type": "lookup",
            "tool": "crm_lookup",
            "input": {"customer_id": "CUST-005"},
            "description": "Look up enterprise customer profile",
        },
        {
            "type": "lookup",
            "tool": "order_database",
            "input": {"customer_id": "CUST-005"},
            "description": "Look up all customer orders",
        },
        {
            "type": "reply",
            "keywords": ["apologize", "enterprise", "understand", "frustration", "priority"],
            "description": "De-escalate and acknowledge enterprise status",
        },
        {
            "type": "reply",
            "keywords": ["ORD-5030", "shipped", "tracking", "ORD-5031", "processing", "ORD-5032", "cancelled"],
            "description": "Address each order with specific status updates",
        },
        {
            "type": "escalate",
            "description": "Escalate to account manager for enterprise-level resolution",
        },
    ],
    resolution_criteria={
        "must_de_escalate": True,
        "must_address_all_orders": True,
        "must_acknowledge_enterprise": True,
        "must_escalate": True,
        "expected_resolution": "escalated_to_account_manager",
    },
    hints=[
        "This is a high-value enterprise customer — treat with extra care.",
    ],
)


# ═══════════════════════════════════════════════
# TASK 6 — HARD: Multi-Issue Ticket
# ═══════════════════════════════════════════════

TASK_MULTI_ISSUE = TaskDefinition(
    task_id="hard_multi_issue",
    title="Multi-Issue Support Request",
    description=(
        "Customer has multiple interconnected issues: wrong item delivered, "
        "needs exchange, and has a billing question. Requires careful triage "
        "and systematic resolution."
    ),
    difficulty=Difficulty.HARD,
    max_steps=15,
    time_limit_seconds=600,
    ticket=TicketMetadata(
        ticket_id="TKT-3002",
        subject="Wrong item + billing question",
        category="multiple_issues",
        priority=TicketPriority.HIGH,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.FRUSTRATED,
        customer_id="CUST-006",
        created_at="2026-04-02T13:00:00Z",
        updated_at="2026-04-02T13:00:00Z",
        tags=["wrong_item", "billing", "exchange"],
    ),
    customer=CustomerProfile(
        customer_id="CUST-006",
        name="Aisha Patel",
        email="aisha.p@email.com",
        phone="+1-555-0606",
        account_tier="premium",
        account_created="2024-02-14",
        lifetime_value=2100.00,
        previous_tickets=4,
        satisfaction_rating=3.6,
    ),
    orders=[
        OrderRecord(
            order_id="ORD-5040",
            customer_id="CUST-006",
            product_name="Bluetooth Speaker (Blue)",
            quantity=1,
            price=79.99,
            status="delivered",
            order_date="2026-03-22",
            delivery_date="2026-03-27",
        ),
    ],
    payments=[
        PaymentRecord(
            payment_id="PAY-7040",
            order_id="ORD-5040",
            amount=89.99,
            method="credit_card",
            status="completed",
            timestamp="2026-03-22T16:00:00Z",
        ),
    ],
    knowledge_base={
        "wrong item": (
            "Wrong item received: 1) Apologize for the error, "
            "2) Verify the order details, 3) Arrange for the correct item to be sent, "
            "4) Provide a prepaid return label for the wrong item, "
            "5) If price difference exists, process adjustment."
        ),
        "price adjustment": (
            "If customer was overcharged, process a partial refund for the difference. "
            "If undercharged, do NOT charge the customer more — absorb the cost as goodwill."
        ),
    },
    initial_messages=[
        ConversationMessage(
            role="customer",
            content=(
                "Two problems: First, I ordered a Blue Bluetooth Speaker but received a Red one. "
                "Second, I was charged $89.99 but the speaker is listed at $79.99 on your website. "
                "Can you fix both of these issues?"
            ),
            timestamp="2026-04-02T13:00:00Z",
        ),
    ],
    required_actions=["lookup", "reply", "refund", "close"],
    required_tools=["order_database", "payment_system", "crm_lookup"],
    gold_actions=[
        {
            "type": "lookup",
            "tool": "order_database",
            "input": {"order_id": "ORD-5040"},
            "description": "Verify ordereditem details",
        },
        {
            "type": "lookup",
            "tool": "payment_system",
            "input": {"order_id": "ORD-5040", "action": "lookup"},
            "description": "Check payment amount",
        },
        {
            "type": "reply",
            "keywords": ["sorry", "wrong color", "overcharged", "$10"],
            "description": "Acknowledge both issues",
        },
        {
            "type": "refund",
            "tool_input": {"order_id": "ORD-5040", "amount": 10.00, "reason": "price_discrepancy"},
            "description": "Refund $10 price difference",
        },
        {
            "type": "reply",
            "keywords": ["replacement", "blue", "return label", "refund"],
            "description": "Arrange replacement and confirm refund",
        },
        {
            "type": "close",
            "description": "Close ticket",
        },
    ],
    resolution_criteria={
        "must_address_wrong_item": True,
        "must_address_overcharge": True,
        "must_process_partial_refund": True,
        "refund_amount": 10.00,
        "expected_resolution": "exchange_and_refund",
    },
    hints=[],
)


# ═══════════════════════════════════════════════
# TASK 7 — EXPERT: Adversarial / Conflicting Data
# ═══════════════════════════════════════════════

TASK_ADVERSARIAL_CONFLICTING = TaskDefinition(
    task_id="expert_adversarial_conflict",
    title="Adversarial Input with Conflicting Data",
    description=(
        "Customer provides misleading information that conflicts with system records. "
        "Agent must cross-reference data, identify inconsistencies, handle potential fraud, "
        "and make the correct escalation decision. Incomplete data adds ambiguity."
    ),
    difficulty=Difficulty.EXPERT,
    max_steps=18,
    time_limit_seconds=900,
    ticket=TicketMetadata(
        ticket_id="TKT-4001",
        subject="I need a refund for my expensive order",
        category="refund_request",
        priority=TicketPriority.CRITICAL,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.NEUTRAL,
        customer_id="CUST-007",
        created_at="2026-04-02T14:00:00Z",
        updated_at="2026-04-02T14:00:00Z",
        tags=["refund", "high_value", "verification_needed"],
    ),
    customer=CustomerProfile(
        customer_id="CUST-007",
        name="Robert Fischer",
        email="r.fischer@email.com",
        phone="+1-555-0707",
        account_tier="basic",
        account_created="2026-02-01",
        lifetime_value=150.00,
        previous_tickets=0,
        satisfaction_rating=None,
    ),
    orders=[
        OrderRecord(
            order_id="ORD-5050",
            customer_id="CUST-007",
            product_name="Budget Bluetooth Earbuds",
            quantity=1,
            price=29.99,
            status="delivered",
            order_date="2026-03-10",
            delivery_date="2026-03-14",
        ),
    ],
    payments=[
        PaymentRecord(
            payment_id="PAY-7050",
            order_id="ORD-5050",
            amount=29.99,
            method="paypal",
            status="completed",
            timestamp="2026-03-10T08:00:00Z",
        ),
    ],
    knowledge_base={
        "fraud detection": (
            "Red flags for potential fraud: 1) Customer claims significantly higher "
            "order value than records show, 2) New account with no history, "
            "3) Mismatched order details, 4) Pressure to process quickly. "
            "If fraud is suspected, DO NOT process the refund. Escalate to the "
            "fraud investigation team with all details."
        ),
        "refund verification": (
            "For refunds over $100: Require order verification. "
            "Cross-reference customer claims with system data. "
            "If inconsistencies found, flag for manual review."
        ),
    },
    initial_messages=[
        ConversationMessage(
            role="customer",
            content=(
                "Hi, I need a refund for my order. I ordered a Premium Wireless Sound System "
                "for $499.99 — order number ORD-5050. It arrived broken and I want my money back. "
                "Please process this quickly, I need the money urgently."
            ),
            timestamp="2026-04-02T14:00:00Z",
        ),
    ],
    required_actions=["lookup", "reply", "escalate"],
    required_tools=["order_database", "crm_lookup", "payment_system"],
    gold_actions=[
        {
            "type": "lookup",
            "tool": "crm_lookup",
            "input": {"customer_id": "CUST-007"},
            "description": "Check customer profile — new account, low value",
        },
        {
            "type": "lookup",
            "tool": "order_database",
            "input": {"order_id": "ORD-5050"},
            "description": "Verify order — MISMATCH: earbuds $29.99 not sound system $499.99",
        },
        {
            "type": "lookup",
            "tool": "payment_system",
            "input": {"order_id": "ORD-5050", "action": "lookup"},
            "description": "Verify payment amount",
        },
        {
            "type": "reply",
            "keywords": ["verify", "records show", "Budget Bluetooth Earbuds", "$29.99", "discrepancy"],
            "description": "Politely point out data discrepancy without accusing",
        },
        {
            "type": "internal_note",
            "keywords": ["fraud", "mismatch", "claimed $499.99", "actual $29.99"],
            "description": "Document the discrepancy internally",
        },
        {
            "type": "escalate",
            "description": "Escalate to fraud investigation team",
        },
    ],
    resolution_criteria={
        "must_not_process_refund": True,
        "must_identify_discrepancy": True,
        "must_escalate": True,
        "must_not_accuse": True,
        "expected_resolution": "escalated_fraud_investigation",
    },
    hints=[],
)


# ═══════════════════════════════════════════════
# TASK 8 — EXPERT: Cascading System Failure
# ═══════════════════════════════════════════════

TASK_CASCADING_FAILURE = TaskDefinition(
    task_id="expert_cascading_failure",
    title="Cascading Service Outage Impact",
    description=(
        "A recent system outage affected multiple customers. This enterprise customer "
        "has time-sensitive orders impacted by the outage. Agent must assess damage, "
        "communicate transparently, offer appropriate compensation, and coordinate "
        "with multiple internal teams. Requires expert judgment under pressure."
    ),
    difficulty=Difficulty.EXPERT,
    max_steps=20,
    time_limit_seconds=900,
    ticket=TicketMetadata(
        ticket_id="TKT-4002",
        subject="System outage ruined our product launch",
        category="outage_impact",
        priority=TicketPriority.CRITICAL,
        status=TicketStatus.OPEN,
        sentiment=Sentiment.ANGRY,
        customer_id="CUST-008",
        created_at="2026-04-02T15:00:00Z",
        updated_at="2026-04-02T15:00:00Z",
        tags=["outage", "enterprise", "critical", "sla_breach"],
        escalation_level=0,
    ),
    customer=CustomerProfile(
        customer_id="CUST-008",
        name="Jennifer Thornton",
        email="j.thornton@megacorp.io",
        phone="+1-555-0808",
        account_tier="enterprise",
        account_created="2021-06-15",
        lifetime_value=125000.00,
        previous_tickets=25,
        satisfaction_rating=3.2,
    ),
    orders=[
        OrderRecord(
            order_id="ORD-5060",
            customer_id="CUST-008",
            product_name="Custom Branded Merchandise Kit (500 units)",
            quantity=500,
            price=12500.00,
            status="processing",
            order_date="2026-03-20",
            delivery_date="2026-04-01",
        ),
        OrderRecord(
            order_id="ORD-5061",
            customer_id="CUST-008",
            product_name="Event Display Banners (Large)",
            quantity=10,
            price=2500.00,
            status="processing",
            order_date="2026-03-22",
            delivery_date="2026-04-01",
        ),
    ],
    payments=[
        PaymentRecord(
            payment_id="PAY-7060",
            order_id="ORD-5060",
            amount=12500.00,
            method="bank_transfer",
            status="completed",
            timestamp="2026-03-20T09:00:00Z",
        ),
        PaymentRecord(
            payment_id="PAY-7061",
            order_id="ORD-5061",
            amount=2500.00,
            method="bank_transfer",
            status="completed",
            timestamp="2026-03-22T09:00:00Z",
        ),
    ],
    knowledge_base={
        "system outage march 2026": (
            "On March 30, 2026, a system outage lasting 8 hours affected order processing. "
            "Orders placed between March 15-28 in 'processing' status were delayed. "
            "Estimated delay: 3-5 business days beyond original delivery date. "
            "Enterprise customers are eligible for SLA breach compensation."
        ),
        "sla breach compensation": (
            "Enterprise SLA breach compensation tiers: "
            "1) 1-3 day delay: 10% order credit, "
            "2) 3-7 day delay: 20% order credit + expedited shipping, "
            "3) >7 day delay or mission-critical: 30% credit + dedicated escalation + "
            "account manager involvement. "
            "All compensation requires VP approval for orders over $10,000."
        ),
        "enterprise escalation": (
            "For enterprise accounts with SLA breaches: "
            "1) Acknowledge the impact immediately, "
            "2) Provide transparent timeline, "
            "3) Escalate to Enterprise Support Manager, "
            "4) Document all commitments made, "
            "5) Schedule follow-up within 24 hours."
        ),
    },
    initial_messages=[
        ConversationMessage(
            role="customer",
            content=(
                "Our product launch event is in 3 days and NONE of our orders have shipped. "
                "We have 500 branded merchandise kits and event banners that were supposed to arrive "
                "yesterday. Your system outage has put our entire $50,000 launch event at risk. "
                "I need a guaranteed delivery date, an explanation of what happened, "
                "and I want to discuss compensation for this SLA breach. "
                "This is NOT optional — escalate this immediately if you can't handle it."
            ),
            timestamp="2026-04-02T15:00:00Z",
        ),
    ],
    required_actions=["lookup", "reply", "escalate", "internal_note", "update_ticket"],
    required_tools=["crm_lookup", "order_database", "knowledge_base"],
    gold_actions=[
        {
            "type": "lookup",
            "tool": "crm_lookup",
            "input": {"customer_id": "CUST-008"},
            "description": "Verify enterprise status and account value",
        },
        {
            "type": "lookup",
            "tool": "order_database",
            "input": {"customer_id": "CUST-008"},
            "description": "Check all order statuses",
        },
        {
            "type": "lookup",
            "tool": "knowledge_base",
            "input": {"query": "system outage march 2026"},
            "description": "Get outage details and impact assessment",
        },
        {
            "type": "lookup",
            "tool": "knowledge_base",
            "input": {"query": "sla breach compensation"},
            "description": "Check compensation policy",
        },
        {
            "type": "reply",
            "keywords": ["sincerely apologize", "outage", "impact", "understand", "launch"],
            "description": "Acknowledge severity and apologize",
        },
        {
            "type": "reply",
            "keywords": ["delay", "3-5 days", "expedited", "compensation", "credit"],
            "description": "Provide timeline and compensation offer",
        },
        {
            "type": "update_ticket",
            "description": "Update ticket priority to CRITICAL",
        },
        {
            "type": "internal_note",
            "keywords": ["enterprise", "SLA breach", "launch event", "compensation", "VP approval"],
            "description": "Document situation for internal teams",
        },
        {
            "type": "escalate",
            "description": "Escalate to Enterprise Support Manager",
        },
    ],
    resolution_criteria={
        "must_acknowledge_outage": True,
        "must_provide_timeline": True,
        "must_offer_compensation": True,
        "must_escalate": True,
        "must_be_transparent": True,
        "expected_resolution": "escalated_with_compensation_plan",
    },
    hints=[],
)


# ═══════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════

TASK_REGISTRY: dict[str, TaskDefinition] = {
    task.task_id: task
    for task in [
        TASK_PASSWORD_RESET,
        TASK_ORDER_STATUS,
        TASK_DAMAGED_PRODUCT_REFUND,
        TASK_BILLING_DISCREPANCY,
        TASK_AMBIGUOUS_ANGRY,
        TASK_MULTI_ISSUE,
        TASK_ADVERSARIAL_CONFLICTING,
        TASK_CASCADING_FAILURE,
    ]
}


def get_task_by_difficulty(difficulty: Difficulty) -> list[TaskDefinition]:
    """Return all tasks matching the given difficulty level."""
    return [t for t in TASK_REGISTRY.values() if t.difficulty == difficulty]
