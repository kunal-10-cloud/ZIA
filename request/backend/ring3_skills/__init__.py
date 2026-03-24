"""
Ring 3 — Skill Loader
=======================
Source: Mental Architecture v2.0 §11 (Ring 3 — Skill Execution Layer)
        Build Plan §A.7, §A.8

Maps skill name (from skill_router.py) → prompt fragment string.
Called by conversation_engine.py on every turn.

Usage:
    from backend.ring3_skills import load_skill_prompt
    ring3_prompt = load_skill_prompt(active_skill)

Rules (architecture doc §11):
  - Only ONE skill prompt is loaded per LLM call
  - Loading all skills would add ~12,000 tokens — never do this
  - DEFAULT_SKILL is career_guide — always the fallback
  - If an unknown skill name is passed, fall back to career_guide
    and log a warning rather than crashing a live conversation
"""

from backend.ring3_skills.career_guide.prompt_fragment import CAREER_GUIDE_PROMPT
from backend.ring3_skills.salary_navigator.prompt_fragment import SALARY_NAVIGATOR_PROMPT

# ── Skill name constants (match skill_router.py exactly) ──────────────────────
CAREER_GUIDE     = "career_guide"
SALARY_NAVIGATOR = "salary_navigator"
WORK_MENTOR      = "work_mentor"
NOTICE_PERIOD    = "notice_period"
OFFER_EVALUATION = "offer_evaluation"

# ── Placeholder prompts for Phase C skills (built in Phase C) ─────────────────
# These are stub strings so the loader doesn't crash if the router
# somehow activates a Phase C skill before those files are written.
# Replace each with a proper import when the skill is built.

_WORK_MENTOR_STUB = """[ACTIVE SKILL: Work Mentor]

You are helping this candidate navigate a workplace situation.
Listen carefully. Validate before advising. Use Voss techniques
when emotions are high. Focus on what the candidate can control.
Do not prescribe — help them think through their options clearly.

(Full Work Mentor prompt fragment — Phase C deliverable C.3)
"""

_NOTICE_PERIOD_STUB = """[ACTIVE SKILL: Notice Period Navigator]

You are helping this candidate through their notice period or
a counter-offer situation. This is a high-stakes moment.
Voss protocol may already be active from Ring 1. Follow it.
Use calculate_buyout and get_notice_templates as needed.

(Full Notice Period prompt fragment — Phase C deliverable C.4)
"""

_OFFER_EVALUATION_STUB = """[ACTIVE SKILL: Offer Evaluation]

You are helping this candidate evaluate a job offer they have received.
Decode the CTC structure first using decode_ctc_structure.
Then compare against market benchmarks. Frame every comparison
with specificity — never vague language.

(Full Offer Evaluation prompt fragment — Phase C deliverable C.5)
"""

# ── Skill prompt registry ──────────────────────────────────────────────────────

_SKILL_PROMPTS: dict[str, str] = {
    CAREER_GUIDE    : CAREER_GUIDE_PROMPT,
    SALARY_NAVIGATOR: SALARY_NAVIGATOR_PROMPT,
    WORK_MENTOR     : _WORK_MENTOR_STUB,
    NOTICE_PERIOD   : _NOTICE_PERIOD_STUB,
    OFFER_EVALUATION: _OFFER_EVALUATION_STUB,
}

# ── Public interface ───────────────────────────────────────────────────────────

def load_skill_prompt(skill_name: str) -> str:
    """
    Returns the prompt fragment for the given skill name.

    Falls back to CAREER_GUIDE_PROMPT if skill_name is unknown.
    Never raises — a missing skill must not crash a live conversation.

    Args:
        skill_name: one of the SKILL_* constants from skill_router.py

    Returns:
        Prompt fragment string (~300-500 tokens) for injection into Ring 3
    """
    if skill_name not in _SKILL_PROMPTS:
        # Unknown skill — log and fall back to default
        # In production this should also fire a monitoring alert
        import logging
        logging.getLogger(__name__).warning(
            f"Unknown skill '{skill_name}' passed to load_skill_prompt. "
            f"Falling back to career_guide."
        )
        return CAREER_GUIDE_PROMPT

    return _SKILL_PROMPTS[skill_name]


def get_available_skills() -> list[str]:
    """Returns all skill names currently registered."""
    return list(_SKILL_PROMPTS.keys())