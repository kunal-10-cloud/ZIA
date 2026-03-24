"""
Skill Router — Tests
=====================
Run: docker compose exec backend python backend/orchestrator/test_skill_router.py

Tests Phase 1 (hard rules) and Phase 2 (intent match) synchronously.
Phase 4 (LLM fallback) requires OPENROUTER_API_KEY — tested separately.

Source: Build plan §A.2 skill trigger table.
"""

import asyncio

passed = 0
failed = 0


def check(name, condition, message=""):
    global passed, failed
    if condition:
        print(f"  PASS — {name}")
        passed += 1
    else:
        print(f"  FAIL — {name}: {message}")
        failed += 1


from backend.orchestrator.skill_router import (
    route,
    CAREER_GUIDE, SALARY_NAVIGATOR, WORK_MENTOR,
    NOTICE_PERIOD, OFFER_EVALUATION,
    _phase1_hard_rules, _phase2_intent_match,
    _phase3_sticky,
)


# ── Phase 1: Hard rule tests ───────────────────────────────────────────────────
print("\n── Phase 1: Hard rules ──\n")

# First turn of first conversation → always Career Guide
check("First turn, first conversation → career_guide",
    _phase1_hard_rules("hello", 1, True, False) == CAREER_GUIDE)

# Second turn first conversation → NOT a hard rule
check("Second turn, first conversation → not a hard rule (None)",
    _phase1_hard_rules("hello", 2, True, False) is None)

# Post-assessment → Career Guide
check("Post-assessment re-engagement → career_guide",
    _phase1_hard_rules("how did i do", 5, False, True) == CAREER_GUIDE)

# Resignation → Notice Period (HIGH priority)
check("'I resigned' → notice_period",
    _phase1_hard_rules("I resigned today", 3, False, False) == NOTICE_PERIOD)
check("'serving notice' → notice_period",
    _phase1_hard_rules("I am serving my notice period now", 3, False, False) == NOTICE_PERIOD)
check("'counter offer' → notice_period",
    _phase1_hard_rules("they gave me a counter offer", 4, False, False) == NOTICE_PERIOD)

# Offer received → Offer Evaluation (HIGH priority)
check("'got an offer' → offer_evaluation",
    _phase1_hard_rules("I got an offer from a GCC", 5, False, False) == OFFER_EVALUATION)
check("'offer letter' → offer_evaluation",
    _phase1_hard_rules("received the offer letter today", 5, False, False) == OFFER_EVALUATION)


# ── Phase 2: Intent match tests ────────────────────────────────────────────────
print("\n── Phase 2: Intent match ──\n")

check("'my salary is too low' → salary_navigator",
    _phase2_intent_match("my salary is too low") == SALARY_NAVIGATOR)
check("'what is the CTC for this role' → salary_navigator",
    _phase2_intent_match("what is the CTC for this role") == SALARY_NAVIGATOR)
check("'how much compensation should I expect' → salary_navigator",
    _phase2_intent_match("how much compensation should I expect") == SALARY_NAVIGATOR)

check("'my manager is toxic' → work_mentor",
    _phase2_intent_match("my manager is toxic") == WORK_MENTOR)
check("'team conflict is affecting my work' → work_mentor",
    _phase2_intent_match("team conflict is affecting my work") == WORK_MENTOR)
check("'stuck in my current role' → work_mentor",
    _phase2_intent_match("stuck in my current role with bad politics") == WORK_MENTOR)

check("'should I switch to a GCC' → career_guide",
    _phase2_intent_match("should I switch to a GCC") == CAREER_GUIDE)
check("'what should I do with my career' → career_guide",
    _phase2_intent_match("what should I do with my career") == CAREER_GUIDE)

# High confidence — two salary signals
check("Two salary signals → high confidence salary_navigator",
    _phase2_intent_match("my CTC and salary package both need to improve") == SALARY_NAVIGATOR)

# Low confidence — ambiguous → None
check("Vague message → None (below 0.7 threshold)",
    _phase2_intent_match("I am not sure") is None)
check("Pure greeting → None",
    _phase2_intent_match("hi how are you") is None)


# ── Phase 3: Sticky rule tests ─────────────────────────────────────────────────
print("\n── Phase 3: Sticky rule ──\n")

check("Current skill is salary_navigator → stay on salary_navigator",
    _phase3_sticky(SALARY_NAVIGATOR) == SALARY_NAVIGATOR)
check("Current skill is None → default to career_guide",
    _phase3_sticky(None) == CAREER_GUIDE)
check("Current skill is work_mentor → stay on work_mentor",
    _phase3_sticky(WORK_MENTOR) == WORK_MENTOR)


# ── Full route() function tests (async, no LLM) ────────────────────────────────
print("\n── Full route() tests ──\n")


async def run_route_tests():
    # Hard rule: first turn
    skill, method = await route("hello", None, turn_number=1, is_first_conversation=True)
    check("route() first turn → career_guide via hard_rule",
        skill == CAREER_GUIDE and method == "hard_rule",
        f"Got: {skill}, {method}")

    # Hard rule: notice period
    skill, method = await route("I resigned today", CAREER_GUIDE, turn_number=5)
    check("route() 'I resigned' → notice_period via hard_rule",
        skill == NOTICE_PERIOD and method == "hard_rule",
        f"Got: {skill}, {method}")

    # Intent match: salary
    skill, method = await route("what is the market salary for my profile", CAREER_GUIDE, turn_number=3)
    check("route() salary question → salary_navigator via intent_match",
        skill == SALARY_NAVIGATOR and method == "intent_match",
        f"Got: {skill}, {method}")

    # Sticky: ambiguous mid-conversation
    skill, method = await route("I see, that makes sense", SALARY_NAVIGATOR, turn_number=8)
    check("route() ambiguous turn → stays on salary_navigator via sticky",
        skill == SALARY_NAVIGATOR and method == "sticky",
        f"Got: {skill}, {method}")

    # Critical: counter-offer must always go to notice_period regardless of current skill
    skill, method = await route(
        "they offered me ₹32L to stay counter offer",
        CAREER_GUIDE,
        turn_number=12,
    )
    check("route() counter-offer mid-career-guide → notice_period (hard rule wins)",
        skill == NOTICE_PERIOD,
        f"Got: {skill}, {method}")


asyncio.run(run_route_tests())


# ── Routing accuracy test — 20 sample messages ─────────────────────────────────
print("\n── Routing accuracy (20 samples, no LLM) ──\n")

SAMPLES = [
    ("I want to move to a GCC", CAREER_GUIDE),
    ("should I stay at Infosys or switch?", CAREER_GUIDE),
    ("my CTC is ₹18L, is that good?", SALARY_NAVIGATOR),
    ("what compensation should I ask for?", SALARY_NAVIGATOR),
    ("salary hike of 30% — is that realistic?", SALARY_NAVIGATOR),
    ("my manager gives me no credit", WORK_MENTOR),
    ("toxic team, constant politics", WORK_MENTOR),
    ("stuck in the same role for 3 years", WORK_MENTOR),
    ("I resigned yesterday, serving notice now", NOTICE_PERIOD),
    ("they gave me a counter offer to stay", NOTICE_PERIOD),
    ("got an offer letter from a startup", OFFER_EVALUATION),
    ("comparing two offers, which one?", OFFER_EVALUATION),
    ("what skills should I build for GCC?", CAREER_GUIDE),
    ("my package needs to improve a lot", SALARY_NAVIGATOR),
    ("team conflict is making work unbearable", WORK_MENTOR),
    ("notice period buyout — how does it work?", NOTICE_PERIOD),
    ("received joining bonus offer, is it good?", OFFER_EVALUATION),
    ("career growth feels stalled", CAREER_GUIDE),
    ("appraisal coming up, what CTC to ask", SALARY_NAVIGATOR),
    ("my boss is micromanaging everything", WORK_MENTOR),
]


async def run_accuracy_test():
    correct = 0
    for message, expected in SAMPLES:
        skill, method = await route(
            message,
            current_skill=CAREER_GUIDE,
            turn_number=5,
            is_first_conversation=False,
        )
        if skill == expected:
            correct += 1
        else:
            print(f"  WRONG: '{message[:50]}' → {skill} (expected {expected})")

    accuracy = correct / len(SAMPLES) * 100
    check(f"Routing accuracy ≥ 90% ({correct}/{len(SAMPLES)} = {accuracy:.0f}%)",
        accuracy >= 90.0,
        f"Got {accuracy:.0f}%. Review trigger keywords for misrouted messages.")


asyncio.run(run_accuracy_test())


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n── Results: {passed} passed, {failed} failed ──\n")

if failed == 0:
    print("Skill router ready.")
    print("Move to Step 7 — Priority Resolver (orchestrator/priority_resolver.py)\n")
else:
    print("Fix failures above.\n")