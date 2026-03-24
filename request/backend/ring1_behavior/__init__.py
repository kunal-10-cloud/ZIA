"""
Ring 1 — Behavioral OS package.

Loads all seven section files and exposes:
  RING1_PROMPT          — combined LLM prompt (used by prompt_assembler.py)
  can_nudge()           — Python function (used by orchestrator in code)
  NUDGE_TEMPLATES       — list of nudge variations (used by skills)

The combined RING1_PROMPT equals the exact production prompt
from Zia_Mental_Architecture_v2.md §9.

File → §9 section mapping:
  boundaries.py              → BOUNDARIES
  ethics.py                  → (from Character Bible §2.4 + Layer 2 §4)
  memory_rules.py            → MEMORY BEHAVIOR
  relationship_mechanics.py  → RELATIONSHIP STAGES + MIXING BOARD RULES
                               + OPINION FRAMEWORK + LANGUAGE REGISTER
                               + TEASING RULES
  voss_protocol.py           → VOSS NEGOTIATION PROTOCOL
  nyra_handoff_protocol.py   → NYRA HANDOFF PROTOCOL
  nudge_policy.py            → ASSESSMENT NUDGE POLICY
"""

from backend.ring1_behavior.boundaries import RING1_BOUNDARIES_PROMPT
from backend.ring1_behavior.ethics import RING1_ETHICS_PROMPT
from backend.ring1_behavior.memory_rules import RING1_MEMORY_RULES_PROMPT
from backend.ring1_behavior.relationship_mechanics import RING1_RELATIONSHIP_MECHANICS_PROMPT
from backend.ring1_behavior.voss_protocol import RING1_VOSS_PROTOCOL_PROMPT
from backend.ring1_behavior.nyra_handoff_protocol import RING1_NYRA_HANDOFF_PROMPT
from backend.ring1_behavior.nudge_policy import (
    RING1_NUDGE_POLICY_PROMPT,
    can_nudge,
    NUDGE_TEMPLATES,
)

# Combined prompt — used by prompt_assembler.py
# Order matches §9 exactly
RING1_PROMPT = (
    RING1_BOUNDARIES_PROMPT
    + RING1_MEMORY_RULES_PROMPT
    + RING1_RELATIONSHIP_MECHANICS_PROMPT
    + RING1_VOSS_PROTOCOL_PROMPT
    + RING1_NYRA_HANDOFF_PROMPT
    + RING1_NUDGE_POLICY_PROMPT
    + RING1_ETHICS_PROMPT
)

__all__ = [
    "RING1_PROMPT",
    "can_nudge",
    "NUDGE_TEMPLATES",
]