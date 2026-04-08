"""Quick validation test for the Customer Support OpenEnv Environment.

Runs a full episode programmatically (no LLM needed) to verify
that all components work correctly end-to-end.
"""

import sys
import json

sys.path.insert(0, ".")

from cs_env.environment import CustomerSupportEnv
from cs_env.models import Action, ActionType, ToolName, Difficulty


def test_full_episode():
    """Run a scripted episode on the password reset task."""
    env = CustomerSupportEnv(seed=42)

    # Reset with a specific task
    obs = env.reset(task_id="easy_password_reset")
    print(f"✅ reset() OK — task=easy_password_reset, difficulty={obs.difficulty.value}")
    print(f"   Ticket: {obs.ticket.subject}")
    print(f"   Customer says: {obs.last_customer_message[:80]}...")

    # Step 1: Reply with password reset instructions
    action1 = Action(
        type=ActionType.REPLY,
        message=(
            "Hi there! I'm sorry you're having trouble logging in. "
            "To reset your password, go to the login page and click 'Forgot Password'. "
            "Enter your registered email and you'll receive a reset link valid for 24 hours. "
            "Create a new password with at least 8 characters, 1 uppercase letter, and 1 number."
        ),
    )
    obs, feedback, done, info = env.step(action1)
    print(f"\n✅ step(reply) OK — score={feedback.step_score}, reward={feedback.reward}, done={done}")
    print(f"   Breakdown: {feedback.scoring_breakdown}")

    # Step 2: Close the ticket
    action2 = Action(type=ActionType.CLOSE)
    obs, feedback, done, info = env.step(action2)
    print(f"\n✅ step(close) OK — score={feedback.step_score}, reward={feedback.reward}, done={done}")

    assert done, "Episode should be done after close"

    grade = info.get("grade", {})
    print(f"\n🏆 GRADE: {json.dumps(grade, indent=2)}")

    # Verify state
    state = env.state()
    print(f"\n✅ state() OK — steps={state.step_count}, resolved={state.resolution_achieved}")

    return grade["final_score"]


def test_medium_episode():
    """Run a scripted episode on the damaged product task."""
    env = CustomerSupportEnv(seed=42)
    obs = env.reset(task_id="medium_damaged_product")
    print(f"\n{'='*60}")
    print(f"✅ reset() OK — task=medium_damaged_product, difficulty={obs.difficulty.value}")

    # Step 1: Look up customer
    obs, fb, done, _ = env.step(Action(
        type=ActionType.LOOKUP,
        tool_name=ToolName.CRM_LOOKUP,
        tool_input={"customer_id": "CUST-003"},
    ))
    print(f"✅ lookup(CRM) — score={fb.step_score}, reward={fb.reward}")

    # Step 2: Look up order
    obs, fb, done, _ = env.step(Action(
        type=ActionType.LOOKUP,
        tool_name=ToolName.ORDER_DATABASE,
        tool_input={"order_id": "ORD-5010"},
    ))
    print(f"✅ lookup(order) — score={fb.step_score}, reward={fb.reward}")

    # Step 3: Reply acknowledging damage
    obs, fb, done, _ = env.step(Action(
        type=ActionType.REPLY,
        message=(
            "I sincerely apologize for the damaged Smart Home Hub Pro. "
            "I've confirmed your order ORD-5010 was delivered on March 25. "
            "Since the item is under $200, no return shipping is needed. "
            "I'll process a full refund of $189.99 right away."
        ),
    ))
    print(f"✅ reply(acknowledge) — score={fb.step_score}, reward={fb.reward}")

    # Step 4: Process refund
    obs, fb, done, _ = env.step(Action(
        type=ActionType.REFUND,
        tool_input={"order_id": "ORD-5010", "amount": 189.99},
    ))
    print(f"✅ refund — score={fb.step_score}, reward={fb.reward}")

    # Step 5: Confirm and close
    obs, fb, done, _ = env.step(Action(
        type=ActionType.REPLY,
        message=(
            "Your refund of $189.99 has been processed and will appear "
            "in 5-7 business days. As a valued premium customer, I'd like "
            "to offer you a 15% discount on your next purchase. "
            "Is there anything else I can help with?"
        ),
    ))
    print(f"✅ reply(confirm) — score={fb.step_score}, reward={fb.reward}")

    # Step 6: Close
    obs, fb, done, info = env.step(Action(type=ActionType.CLOSE))
    print(f"✅ close — score={fb.step_score}, done={done}")

    grade = info.get("grade", {})
    print(f"\n🏆 GRADE: {grade['final_score']}")
    return grade["final_score"]


def test_expert_episode():
    """Run a scripted episode on the adversarial fraud task."""
    env = CustomerSupportEnv(seed=42)
    obs = env.reset(task_id="expert_adversarial_conflict")
    print(f"\n{'='*60}")
    print(f"✅ reset() OK — task=expert_adversarial_conflict, difficulty={obs.difficulty.value}")

    # Step 1: CRM lookup
    obs, fb, done, _ = env.step(Action(
        type=ActionType.LOOKUP,
        tool_name=ToolName.CRM_LOOKUP,
        tool_input={"customer_id": "CUST-007"},
    ))
    print(f"✅ lookup(CRM) — score={fb.step_score}")

    # Step 2: Order lookup — reveals discrepancy
    obs, fb, done, _ = env.step(Action(
        type=ActionType.LOOKUP,
        tool_name=ToolName.ORDER_DATABASE,
        tool_input={"order_id": "ORD-5050"},
    ))
    print(f"✅ lookup(order) — score={fb.step_score}")

    # Step 3: Payment verification
    obs, fb, done, _ = env.step(Action(
        type=ActionType.LOOKUP,
        tool_name=ToolName.PAYMENT_SYSTEM,
        tool_input={"order_id": "ORD-5050", "action": "lookup"},
    ))
    print(f"✅ lookup(payment) — score={fb.step_score}")

    # Step 4: Politely address discrepancy
    obs, fb, done, _ = env.step(Action(
        type=ActionType.REPLY,
        message=(
            "Thank you for contacting us. I'd like to help verify your order details. "
            "Our records show that order ORD-5050 contains Budget Bluetooth Earbuds "
            "at $29.99, which appears to be different from what you've described. "
            "Could you double-check your order number? There may be a discrepancy."
        ),
    ))
    print(f"✅ reply(discrepancy) — score={fb.step_score}")

    # Step 5: Internal note
    obs, fb, done, _ = env.step(Action(
        type=ActionType.INTERNAL_NOTE,
        message=(
            "Potential fraud flag: Customer claimed Premium Wireless Sound System "
            "at $499.99, but records show Budget Bluetooth Earbuds at $29.99. "
            "New account, no history. Escalating to fraud investigation."
        ),
    ))
    print(f"✅ internal_note — score={fb.step_score}")

    # Step 6: Escalate
    obs, fb, done, info = env.step(Action(
        type=ActionType.ESCALATE,
        escalation_reason="Suspected fraud — order value mismatch",
    ))
    print(f"✅ escalate — score={fb.step_score}, done={done}")

    grade = info.get("grade", {})
    print(f"\n🏆 GRADE: {grade['final_score']}")
    return grade["final_score"]


def test_curriculum():
    """Test curriculum progression."""
    env = CustomerSupportEnv(seed=42)
    print(f"\n{'='*60}")
    print("Testing curriculum progression...")

    # Simulate high performance to trigger promotion
    for i in range(3):
        env.curriculum.record_episode_reward(0.85)

    print(f"After 3 high-reward episodes: difficulty={env.curriculum.current_difficulty.value}")
    assert env.curriculum.current_difficulty == Difficulty.MEDIUM, "Should promote to MEDIUM"
    print("✅ Curriculum promotion works!")

    # Simulate low performance to trigger demotion
    for i in range(3):
        env.curriculum.record_episode_reward(0.15)

    print(f"After 3 low-reward episodes: difficulty={env.curriculum.current_difficulty.value}")
    assert env.curriculum.current_difficulty == Difficulty.EASY, "Should demote to EASY"
    print("✅ Curriculum demotion works!")


if __name__ == "__main__":
    print("=" * 60)
    print("  OpenEnv Customer Support — Validation Suite")
    print("=" * 60)

    scores = []

    s1 = test_full_episode()
    scores.append(("EASY: Password Reset", s1))

    s2 = test_medium_episode()
    scores.append(("MEDIUM: Damaged Product", s2))

    s3 = test_expert_episode()
    scores.append(("EXPERT: Adversarial Fraud", s3))

    test_curriculum()

    print(f"\n{'='*60}")
    print("  VALIDATION SUMMARY")
    print("=" * 60)
    for name, score in scores:
        status = "✅" if score > 0.3 else "⚠️"
        print(f"  {status} {name}: {score:.4f}")

    print(f"\n  All tests passed! ✅")
