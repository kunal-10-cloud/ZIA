"""
Ring 1 — Tests
==============
Run: docker compose exec backend python backend/ring1_behavior/test_ring1.py

Verifies all seven files exist with correct content and that the
combined RING1_PROMPT matches the architecture doc §9 production prompt.
Also tests the can_nudge() Python function.
"""

from backend.ring1_behavior import RING1_PROMPT, can_nudge, NUDGE_TEMPLATES
from backend.ring1_behavior.boundaries import RING1_BOUNDARIES_PROMPT
from backend.ring1_behavior.ethics import RING1_ETHICS_PROMPT
from backend.ring1_behavior.memory_rules import RING1_MEMORY_RULES_PROMPT
from backend.ring1_behavior.relationship_mechanics import RING1_RELATIONSHIP_MECHANICS_PROMPT
from backend.ring1_behavior.voss_protocol import RING1_VOSS_PROTOCOL_PROMPT
from backend.ring1_behavior.nyra_handoff_protocol import RING1_NYRA_HANDOFF_PROMPT
from backend.ring1_behavior.nudge_policy import RING1_NUDGE_POLICY_PROMPT

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

print("\n── Ring 1 — File structure tests ──\n")

all_files = [
    ("boundaries.py", RING1_BOUNDARIES_PROMPT),
    ("ethics.py", RING1_ETHICS_PROMPT),
    ("memory_rules.py", RING1_MEMORY_RULES_PROMPT),
    ("relationship_mechanics.py", RING1_RELATIONSHIP_MECHANICS_PROMPT),
    ("voss_protocol.py", RING1_VOSS_PROTOCOL_PROMPT),
    ("nyra_handoff_protocol.py", RING1_NYRA_HANDOFF_PROMPT),
    ("nudge_policy.py", RING1_NUDGE_POLICY_PROMPT),
]

for fname, prompt in all_files:
    check(f"{fname} exists and is non-empty",
        isinstance(prompt, str) and len(prompt) > 30)

check("RING1_PROMPT combines all seven files",
    all(p.strip()[:25] in RING1_PROMPT for _, p in all_files))

print("\n── Ring 1 — Token budget ──\n")

words = len(RING1_PROMPT.split())
tokens = int(words * 1.3)
check(f"Combined token budget (~{tokens} / 2,500 limit)",
    tokens <= 2500,
    f"Architecture specifies ~2,050 tokens. Got ~{tokens}.")
print(f"  INFO — Estimated tokens: ~{tokens} / 2,500 (target ~2,050 in production)")

print("\n── Ring 1 — No dynamic content (KV-cache safety) ──\n")

forbidden = ["candidate_id", "conversation_id", "datetime", "turn_number"]
for term in forbidden:
    check(f"No '{term}' in RING1_PROMPT",
        term not in RING1_PROMPT.lower(),
        f"Dynamic value found — breaks KV-cache.")

print("\n── Ring 1 — Architecture §9 hard-fail content checks ──\n")

p = RING1_PROMPT
check("§9: RING 1 — BEHAVIORAL OPERATING SYSTEM header", "RING 1 — BEHAVIORAL OPERATING SYSTEM" in p)
check("§9: Empathy goes UP rule", "empathy" in p.lower() and "goes UP" in p)
check("§9: CASTE — ZERO inference", "ZERO inference" in p and "ZERO reference" in p)
check("§9: Gender pay gap — ₹34L", "₹34L" in p)
check("§9: Company opinions — defamation risk", "defamation risk" in p)
check("§9: Family pressure — ₹8-12L script", "₹8-12L" in p)
check("§9: Listening IS the product", "The listening IS the product" in p)
check("§9: ICEBERG MODEL", "ICEBERG MODEL" in p)
check("§9: DOOR RULE", "DOOR RULE" in p)
check("§9: FORGET RULE with exact script", "Gone. Never happened" in p)
check("§9: Stage 1 STRANGER", "Stage 1 STRANGER" in p)
check("§9: TRUST-BASED transitions", "TRUST-BASED, not time-based" in p)
check("§9: FRIENDLY FIRST, SOVEREIGN EARNED", "FRIENDLY FIRST, SOVEREIGN EARNED" in p)
check("§9: Voss — Mirror technique", "Mirror: repeat last 1-3 critical words" in p)
check("§9: Voss — 3-5 seconds silence", "3-5 seconds" in p)
check("§9: Voss — That's right summary", "That's right" in p)
check("§9: Nyra — my colleague Nyra", "my colleague Nyra" in p)
check("§9: Nyra — never blame", "NEVER blame Nyra" in p)
check("§9: Nudge — first 10 minutes", "first 10 minutes" in p)
check("§9: Nudge — 30-day cooldown", "30-day cooldown" in p)
check("§9: Nudge — report alone worth 40 minutes", "report alone is worth 40 minutes" in p)
check("§9: Counter-offer opinion framework", "Counter-offers" in p and "THING that made you want to leave" in p)
check("§9: Language register — mirror candidate", "Mirror the candidate" in p)
check("§9: Teasing — behavior not person", "Tease the behavior, not the person" in p)
check("ethics.py: Candidate data isolation", "stays between us" in p)
check("ethics.py: Aggregate patterns only", "aggregate" in p.lower() or "Aggregate" in p)

print("\n── Ring 1 — can_nudge() function tests ──\n")

check("Blocks before 10 minutes",
    can_nudge(8, 0, 0, None) is False)
check("Allows after 10 minutes (no declines)",
    can_nudge(12, 0, 0, None) is True)
check("Blocks second nudge same session",
    can_nudge(20, 1, 0, None) is False)
check("Blocks within 30-day cooldown",
    can_nudge(15, 0, 2, 10) is False)
check("Allows after 30-day cooldown expires",
    can_nudge(15, 0, 2, 35) is True)
check("NUDGE_TEMPLATES has 3 variations",
    len(NUDGE_TEMPLATES) == 3)
check("Each template mentions 'Nyra'",
    all("Nyra" in t for t in NUDGE_TEMPLATES))

print(f"\n── Results: {passed} passed, {failed} failed ──\n")
if failed == 0:
    print("Ring 1 is correct and aligned with architecture doc §9.\n")
else:
    print("Fix failures. Ring 1 must match Zia_Mental_Architecture_v2.md §9.\n")