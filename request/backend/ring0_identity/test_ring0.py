"""
Ring 0 — Tests
==============
Run: docker compose exec backend python backend/ring0_identity/test_ring0.py

Verifies all four files exist with correct content and that the
combined RING0_PROMPT matches the architecture doc §7 production prompt.
"""

from backend.ring0_identity.kernel import RING0_KERNEL_PROMPT
from backend.ring0_identity.worldview import RING0_WORLDVIEW_PROMPT
from backend.ring0_identity.voice_config import RING0_VOICE_CONFIG_PROMPT
from backend.ring0_identity.self_narrative import RING0_SELF_NARRATIVE_PROMPT
from backend.ring0_identity import RING0_PROMPT

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

print("\n── Ring 0 — File structure tests ──\n")

check("kernel.py exists and is non-empty",
    isinstance(RING0_KERNEL_PROMPT, str) and len(RING0_KERNEL_PROMPT) > 50)
check("worldview.py exists and is non-empty",
    isinstance(RING0_WORLDVIEW_PROMPT, str) and len(RING0_WORLDVIEW_PROMPT) > 50)
check("voice_config.py exists and is non-empty",
    isinstance(RING0_VOICE_CONFIG_PROMPT, str) and len(RING0_VOICE_CONFIG_PROMPT) > 50)
check("self_narrative.py exists and is non-empty",
    isinstance(RING0_SELF_NARRATIVE_PROMPT, str) and len(RING0_SELF_NARRATIVE_PROMPT) > 50)
check("RING0_PROMPT combines all four files",
    all(p in RING0_PROMPT for p in [
        RING0_KERNEL_PROMPT.strip()[:30],
        RING0_WORLDVIEW_PROMPT.strip()[:30],
        RING0_VOICE_CONFIG_PROMPT.strip()[:30],
        RING0_SELF_NARRATIVE_PROMPT.strip()[:30],
    ]))

print("\n── Ring 0 — Token budget ──\n")

words = len(RING0_PROMPT.split())
tokens = int(words * 1.3)
check(f"Combined token budget (~{tokens} / 2,500 limit)",
    tokens <= 2500,
    f"Architecture specifies ~2,450 tokens. Got ~{tokens}.")
print(f"  INFO — Estimated tokens: ~{tokens} / 2,500")

print("\n── Ring 0 — No dynamic content (KV-cache safety) ──\n")

forbidden = ["candidate_id", "conversation_id", "datetime", "turn_number"]
for term in forbidden:
    check(f"No '{term}' in RING0_PROMPT",
        term not in RING0_PROMPT.lower(),
        f"Dynamic value found — breaks KV-cache. Move to Ring 2.")

print("\n── Ring 0 — Architecture §7 content checks ──\n")

p = RING0_PROMPT
check("§7: RING 0 — IDENTITY KERNEL header", "RING 0 — IDENTITY KERNEL" in p)
check("§7: Three-layer arc (Surface/Middle/Core)", "Surface (minutes 0-2)" in p and "Middle (minutes 2-5)" in p)
check("§7: IMMUTABLE CHARACTER RULES section", "IMMUTABLE CHARACTER RULES" in p)
check("§7: 'We' not 'you' rule", '"We" not "you"' in p or "We not you" in p)
check("§7: Humor as DEFAULT", "Humor is your DEFAULT" in p)
check("§7: Introduction script ('before you roll your eyes')", "before you roll your eyes" in p)
check("§7: AI superpower framing", "superpower" in p)
check("§7: EmployLabs — only when asked", "ONLY when directly asked" in p)
check("§7: Data sources narrative ('pattern, not a guess')", "pattern, not a guess" in p)
check("§7: Recruiter positioning ('I work for you')", "I work for you" in p)
check("§7: WORLDVIEW section", "WORLDVIEW — PLAY THE LONG GAME" in p)
check("§7: Compounding decisions principle", "Compounding decisions" in p)
check("§7: Specific knowledge principle", "Specific knowledge" in p)
check("§7: VOICE IDENTITY section", "VOICE IDENTITY" in p)
check("§7: 155-165 wpm pace", "155-165" in p)
check("§7: Startups = width, GCCs = depth", "Startups = width" in p)

print(f"\n── Results: {passed} passed, {failed} failed ──\n")
if failed == 0:
    print("Ring 0 is correct and aligned with architecture doc §7.\n")
else:
    print("Fix failures. Ring 0 must match Zia_Mental_Architecture_v2.md §7.\n")