"""
Ring 0 — Identity Kernel package.

Loads all four sections and exposes the combined prompt
that the orchestrator uses as the Ring 0 system prompt prefix.

Usage:
    from backend.ring0_identity import RING0_PROMPT

The combined prompt equals the exact production prompt
from Zia_Mental_Architecture_v2.md §7.
"""

from backend.ring0_identity.kernel import RING0_KERNEL_PROMPT
from backend.ring0_identity.worldview import RING0_WORLDVIEW_PROMPT
from backend.ring0_identity.voice_config import RING0_VOICE_CONFIG_PROMPT
from backend.ring0_identity.self_narrative import RING0_SELF_NARRATIVE_PROMPT

# Combined prompt — used by prompt_assembler.py
# Order matches §7: identity → self-narrative → worldview → voice → rules
RING0_PROMPT = (
    RING0_KERNEL_PROMPT
    + RING0_SELF_NARRATIVE_PROMPT
    + RING0_WORLDVIEW_PROMPT
    + RING0_VOICE_CONFIG_PROMPT
)