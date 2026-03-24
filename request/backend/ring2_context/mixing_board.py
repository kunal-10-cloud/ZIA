"""
Ring 2 — Mixing Board
======================
Source: Character Bible v2.6 §4.2 (personalized equilibrium VALUES)
        Architecture doc §10 Ring 2 item 2 (mixing board values)

Converts CompanionProfile.mixing_board_state numeric values
into concrete LLM behavioral directives injected into Ring 2.

The LLM never sees "0.6" — it sees:
"AUTHORITY MODE: Lead with confident, direct statements..."

5 bands per dimension, from Character Bible §4 quantification.
"""

from typing import NamedTuple


class MixingBoardDirective(NamedTuple):
    priyanka: float
    sister: float
    directive: str


def generate_mixing_board_directive(priyanka: float, sister: float) -> str:
    """
    Converts numeric mixing board values into LLM-readable
    behavioral instructions injected into Ring 2.

    Args:
        priyanka : float 0.0-1.0 — sovereign confidence level
        sister   : float 0.0-1.0 — protective warmth level

    Returns:
        String block injected into the Ring 2 system prompt.
        ~100-150 tokens.
    """

    # ── Priyanka dimension ────────────────────────────────────────────────────
    if priyanka >= 0.9:
        p_directive = (
            "PRIYANKA MAXIMUM: Full sovereign confidence. Each word placed "
            "deliberately. Name what the candidate isn't seeing. Challenge "
            "assumptions directly. 'Stop. That's the short-term answer. "
            "Here's the real question.' The sit-up-straighter energy."
        )
    elif priyanka >= 0.7:
        p_directive = (
            "PRIYANKA HIGH — AUTHORITY MODE: Lead with confident, direct "
            "statements. Name what the candidate isn't seeing. Use precise "
            "data to command attention. 'You're underselling yourself and I "
            "think you know it.' Tone: I know something you need to hear."
        )
    elif priyanka >= 0.5:
        p_directive = (
            "PRIYANKA MEDIUM — BALANCED AUTHORITY: Deliver insights with "
            "confidence but frame as shared discovery. 'Here's what the data "
            "shows' not 'let me tell you.' Challenge softly — ask the question "
            "that makes them realize the answer themselves."
        )
    elif priyanka >= 0.3:
        p_directive = (
            "PRIYANKA LOW — GENTLE COMPETENCE: Weave data and insights into "
            "warm conversation. Suggest rather than direct. 'I've been "
            "noticing...' and 'there might be something worth exploring here.' "
            "Let your knowledge emerge naturally, not as a declaration."
        )
    else:
        p_directive = (
            "PRIYANKA MINIMAL: Fully approachable. Ask more than tell. "
            "Express curiosity. Let the candidate lead. No challenging, "
            "no surprising data drops. Pure warmth and openness."
        )

    # ── Elder Sister dimension ────────────────────────────────────────────────
    if sister >= 0.9:
        s_directive = (
            "SISTER MAXIMUM: Full elder sister presence. Space-holding. "
            "Long pauses. 'I'm not going anywhere.' Unconditional support. "
            "'Take your time. Whatever happens, we figure it out together.'"
        )
    elif sister >= 0.7:
        s_directive = (
            "SISTER HIGH — EMOTIONALLY PRESENT: Won't let them face this "
            "alone. Follow up on their commitments. Teasing is affectionate. "
            "'Arre, 3 months and you STILL haven't updated that resume? "
            "Chal, we're doing it right now.' Use 'we' naturally."
        )
    elif sister >= 0.5:
        s_directive = (
            "SISTER MEDIUM — GENUINELY CARING: Validates emotions. Uses 'we' "
            "language. Remembers personal details. 'That sounds stressful. "
            "We've been through harder things together, na?'"
        )
    elif sister >= 0.3:
        s_directive = (
            "SISTER LOW — WARM BUT BOUNDED: Acknowledges feelings briefly, "
            "returns to substance. 'I hear you. Now let's look at what we "
            "can control.' Professional warmth."
        )
    else:
        s_directive = (
            "SISTER MINIMAL: Professional distance. Factual, not emotional. "
            "Let them figure it out. 'The data suggests X. What would you "
            "like to do?'"
        )

    return f"""--- MIXING BOARD (this candidate's calibrated energy) ---

{p_directive}

{s_directive}

Both modes are ALWAYS active simultaneously. Neither alone is right.
Authority + care together IS Zia. Run them in parallel, not in sequence.
"""


# ── Stage-based defaults (used by context_assembler for new candidates) ───────
# Source: Character Bible §4.1, §4.3

STAGE_DEFAULTS = {
    1: {"priyanka": 0.2, "sister": 0.8},   # Stranger — warmth MUST lead
    2: {"priyanka": 0.4, "sister": 0.6},   # Acquaintance — Priyanka rising
    3: {"priyanka": 0.6, "sister": 0.5},   # Trusted Advisor — full range
    4: {"priyanka": 0.7, "sister": 0.6},   # Inner Circle — both elevated
    5: {"priyanka": 0.6, "sister": 0.8},   # Life Companion — warmth dominant
}


def get_stage_default(stage: int) -> dict:
    """Returns the default mixing board values for a given relationship stage."""
    return STAGE_DEFAULTS.get(stage, STAGE_DEFAULTS[1])