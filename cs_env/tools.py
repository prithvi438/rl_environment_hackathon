"""Simulated tool APIs for the Customer Support Environment.

Provides deterministic, fake implementations of:
  - CRM Lookup
  - Order Database
  - Payment/Refund System
  - Knowledge Base

All tools return structured ToolResult objects and are seeded
by the task's pre-loaded data so behavior is fully reproducible.
"""

from __future__ import annotations

from typing import Any, Optional

from cs_env.models import (
    CustomerProfile,
    OrderRecord,
    PaymentRecord,
    ToolName,
    ToolResult,
)


class ToolRegistry:
    """Registry of simulated tools available to the agent.
    
    Each tool operates on pre-loaded data injected during environment
    reset, ensuring deterministic behavior across runs.
    """

    def __init__(self) -> None:
        self._customers: dict[str, CustomerProfile] = {}
        self._orders: dict[str, OrderRecord] = {}
        self._orders_by_customer: dict[str, list[OrderRecord]] = {}
        self._payments: dict[str, PaymentRecord] = {}
        self._payments_by_order: dict[str, list[PaymentRecord]] = {}
        self._knowledge_base: dict[str, str] = {}
        self._refund_log: list[dict[str, Any]] = []

    # ── Data Loading ──────────────────────────────────────

    def load_customer(self, customer: CustomerProfile) -> None:
        self._customers[customer.customer_id] = customer

    def load_order(self, order: OrderRecord) -> None:
        self._orders[order.order_id] = order
        self._orders_by_customer.setdefault(order.customer_id, []).append(order)

    def load_payment(self, payment: PaymentRecord) -> None:
        self._payments[payment.payment_id] = payment
        self._payments_by_order.setdefault(payment.order_id, []).append(payment)

    def load_knowledge_base(self, articles: dict[str, str]) -> None:
        self._knowledge_base = {k.lower(): v for k, v in articles.items()}

    def clear(self) -> None:
        self._customers.clear()
        self._orders.clear()
        self._orders_by_customer.clear()
        self._payments.clear()
        self._payments_by_order.clear()
        self._knowledge_base.clear()
        self._refund_log.clear()

    # ── Tool Dispatch ─────────────────────────────────────

    def invoke(self, tool: ToolName, inputs: Optional[dict[str, Any]] = None) -> ToolResult:
        inputs = inputs or {}
        dispatch = {
            ToolName.CRM_LOOKUP: self._crm_lookup,
            ToolName.ORDER_DATABASE: self._order_lookup,
            ToolName.PAYMENT_SYSTEM: self._payment_action,
            ToolName.KNOWLEDGE_BASE: self._knowledge_search,
        }
        handler = dispatch.get(tool)
        if handler is None:
            return ToolResult(tool=tool, success=False, error=f"Unknown tool: {tool}")
        try:
            return handler(inputs)
        except Exception as exc:
            return ToolResult(tool=tool, success=False, error=str(exc))

    # ── CRM ───────────────────────────────────────────────

    def _crm_lookup(self, inputs: dict[str, Any]) -> ToolResult:
        customer_id = inputs.get("customer_id")
        email = inputs.get("email")

        if customer_id and customer_id in self._customers:
            cust = self._customers[customer_id]
            return ToolResult(
                tool=ToolName.CRM_LOOKUP,
                success=True,
                data=cust.model_dump(),
            )

        if email:
            for cust in self._customers.values():
                if cust.email.lower() == email.lower():
                    return ToolResult(
                        tool=ToolName.CRM_LOOKUP,
                        success=True,
                        data=cust.model_dump(),
                    )

        return ToolResult(
            tool=ToolName.CRM_LOOKUP,
            success=False,
            error="Customer not found. Provide a valid customer_id or email.",
        )

    # ── Order Database ────────────────────────────────────

    def _order_lookup(self, inputs: dict[str, Any]) -> ToolResult:
        order_id = inputs.get("order_id")
        customer_id = inputs.get("customer_id")

        if order_id and order_id in self._orders:
            order = self._orders[order_id]
            return ToolResult(
                tool=ToolName.ORDER_DATABASE,
                success=True,
                data=order.model_dump(),
            )

        if customer_id and customer_id in self._orders_by_customer:
            orders = self._orders_by_customer[customer_id]
            return ToolResult(
                tool=ToolName.ORDER_DATABASE,
                success=True,
                data={"orders": [o.model_dump() for o in orders]},
            )

        return ToolResult(
            tool=ToolName.ORDER_DATABASE,
            success=False,
            error="No orders found. Provide a valid order_id or customer_id.",
        )

    # ── Payment System ────────────────────────────────────

    def _payment_action(self, inputs: dict[str, Any]) -> ToolResult:
        action = inputs.get("action", "lookup")

        if action == "lookup":
            order_id = inputs.get("order_id")
            payment_id = inputs.get("payment_id")

            if payment_id and payment_id in self._payments:
                pay = self._payments[payment_id]
                return ToolResult(
                    tool=ToolName.PAYMENT_SYSTEM,
                    success=True,
                    data=pay.model_dump(),
                )

            if order_id and order_id in self._payments_by_order:
                payments = self._payments_by_order[order_id]
                return ToolResult(
                    tool=ToolName.PAYMENT_SYSTEM,
                    success=True,
                    data={"payments": [p.model_dump() for p in payments]},
                )

            return ToolResult(
                tool=ToolName.PAYMENT_SYSTEM,
                success=False,
                error="No payment records found.",
            )

        if action == "refund":
            order_id = inputs.get("order_id")
            amount = inputs.get("amount")
            reason = inputs.get("reason", "customer_request")

            if not order_id or order_id not in self._orders:
                return ToolResult(
                    tool=ToolName.PAYMENT_SYSTEM,
                    success=False,
                    error=f"Order {order_id} not found.",
                )

            order = self._orders[order_id]
            if amount is None:
                amount = order.price

            if amount > order.price:
                return ToolResult(
                    tool=ToolName.PAYMENT_SYSTEM,
                    success=False,
                    error=f"Refund amount ${amount} exceeds order total ${order.price}.",
                )

            # Process refund deterministically
            refund_id = f"REF-{order_id}-{len(self._refund_log) + 1:03d}"
            refund_record = {
                "refund_id": refund_id,
                "order_id": order_id,
                "amount": amount,
                "reason": reason,
                "status": "processed",
            }
            self._refund_log.append(refund_record)

            return ToolResult(
                tool=ToolName.PAYMENT_SYSTEM,
                success=True,
                data=refund_record,
            )

        return ToolResult(
            tool=ToolName.PAYMENT_SYSTEM,
            success=False,
            error=f"Unknown payment action: {action}. Use 'lookup' or 'refund'.",
        )

    # ── Knowledge Base ────────────────────────────────────

    def _knowledge_search(self, inputs: dict[str, Any]) -> ToolResult:
        query = inputs.get("query", "").lower().strip()
        if not query:
            return ToolResult(
                tool=ToolName.KNOWLEDGE_BASE,
                success=False,
                error="Provide a 'query' string to search the knowledge base.",
            )

        results: list[dict[str, str]] = []
        for title, body in self._knowledge_base.items():
            if query in title or any(word in title for word in query.split()):
                results.append({"title": title, "content": body})

        if not results:
            # Fuzzy fallback: return all articles containing query words
            for title, body in self._knowledge_base.items():
                if any(word in body.lower() for word in query.split()):
                    results.append({"title": title, "content": body})

        if results:
            return ToolResult(
                tool=ToolName.KNOWLEDGE_BASE,
                success=True,
                data={"articles": results[:5]},
            )

        return ToolResult(
            tool=ToolName.KNOWLEDGE_BASE,
            success=False,
            error="No knowledge base articles found for query.",
        )

    # ── Accessors ─────────────────────────────────────────

    @property
    def refund_log(self) -> list[dict[str, Any]]:
        return list(self._refund_log)

    def get_customer(self, customer_id: str) -> Optional[CustomerProfile]:
        return self._customers.get(customer_id)

    def get_order(self, order_id: str) -> Optional[OrderRecord]:
        return self._orders.get(order_id)
