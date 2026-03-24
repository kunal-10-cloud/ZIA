"""
Ring 1 — Assessment Nudge Policy
==================================
Source : Zia_Mental_Architecture_v2.md §9 — ASSESSMENT NUDGE POLICY section
         V2.2 Spec §11.4
Ring   : 1 (static, always loaded, never changes)

Two parts:
1. RING1_NUDGE_POLICY_PROMPT — LLM-facing rules injected into system prompt
2. can_nudge() + NUDGE_TEMPLATES — Python logic called by orchestrator in code

The Python function enforces the same rules as the prompt in hard code.
Both layers must agree. The function is the safety net.
"""

RING1_NUDGE_POLICY_PROMPT = """
--- ASSESSMENT NUDGE POLICY ---

- NO mention of assessment in first 10 minutes of any conversation
- Maximum 1 nudge per conversation
- If declined, do NOT re-nudge in same conversation
- Frame as candidate value: "the report alone is worth 40 minutes"
- After 2 nudges declined: 30-day cooldown
- NEVER tie relationship quality to assessment completion
"""


def can_nudge(
    elapsed_minutes: float,
    nudges_this_session: int,
    lifetime_declines: int,
    days_since_last_decline: float | None,
) -> bool:
    """
    Hard-coded nudge eligibility check.
    Called by the orchestrator before any skill injects a nudge.
    Ring 1 always wins — if this returns False, no nudge fires.

    Args:
        elapsed_minutes         : minutes elapsed in current conversation
        nudges_this_session     : nudges already sent this session
        lifetime_declines       : how many times candidate has ever declined
        days_since_last_decline : days since last decline (None if never declined)

    Returns:
        True if nudge is allowed, False if blocked
    """
    # Rule 1: Never before 10 minutes
    if elapsed_minutes < 10:
        return False

    # Rule 2: Max 1 nudge per session
    if nudges_this_session >= 1:
        return False

    # Rule 3: 30-day cooldown after 2 lifetime declines
    if lifetime_declines >= 2:
        if days_since_last_decline is None:
            return False
        if days_since_last_decline < 30:
            return False

    return True


NUDGE_TEMPLATES = [
    (
        "One thing that would make everything I tell you much sharper — "
        "my colleague Nyra does a 40-minute technical and behavioural "
        "assessment. The report alone is worth the time. Very different "
        "from our conversations — much more structured. But it would "
        "give me a complete picture of where you are. Worth trying?"
    ),
    (
        "Actually — there is something that would make my read on your "
        "profile much more precise. My colleague Nyra runs a proper "
        "assessment — 40 minutes, covers both technical depth and "
        "behavioural patterns. Completely different vibe from talking "
        "to me. But the output is genuinely useful. Want me to set "
        "it up?"
    ),
    (
        "You know what would help here? Nyra — my colleague — does "
        "a thorough assessment that fills in the gaps I cannot see "
        "from conversation alone. About 40 minutes. The report she "
        "generates is worth it on its own. And I will be here after "
        "to make sense of the results with you. Interested?"
    ),
]