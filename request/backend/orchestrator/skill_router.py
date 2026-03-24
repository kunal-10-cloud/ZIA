"""
Orchestrator — Skill Router
=============================
Source: Zia_Build_Plan_Phase_A_to_E.md §A.2
        Zia_Mental_Architecture_v2.md §11 (Ring 3)

Decides which Ring 3 skill is active for each conversational turn.
The "traffic cop" of the orchestrator.

4-phase routing (build plan §A.2):
  Phase 1: Hard rules      (~0ms)   — deterministic, no ambiguity
  Phase 2: Intent match    (~5ms)   — keyword scanning with confidence
  Phase 3: Sticky rule     (~0ms)   — keep current if no clear shift
  Phase 4: LLM fallback    (~300ms) — Claude Haiku, only when 1-3 fail

Rules:
  - One primary skill active per turn (architecture doc §11)
  - Skill transitions invisible to candidate
  - Sticky by default — switching on ambiguity causes jarring shifts
  - Assessment nudge is NOT a skill (Ring 1 sub-routine, not Ring 3)
"""

import re
from typing import Optional
from openai import AsyncOpenAI

from backend.config.settings import settings

# ── Skill name constants ───────────────────────────────────────────────────────
CAREER_GUIDE      = "career_guide"
SALARY_NAVIGATOR  = "salary_navigator"
WORK_MENTOR       = "work_mentor"
NOTICE_PERIOD     = "notice_period"
OFFER_EVALUATION  = "offer_evaluation"

# Default skill — lowest priority, always the fallback
DEFAULT_SKILL = CAREER_GUIDE

# All Phase A skills
PHASE_A_SKILLS = [
    CAREER_GUIDE,
    SALARY_NAVIGATOR,
    WORK_MENTOR,
    NOTICE_PERIOD,
    OFFER_EVALUATION,
]

# ── Keyword trigger tables (build plan §A.2 exact keywords) ───────────────────

NOTICE_PERIOD_TRIGGERS = [
    "resigned", "i resigned", "serving notice", "counter offer",
    "counter-offer", "notice period", "last day", "buyout",
    "i have resigned", "put in my papers", "gave my notice",
    "serving my notice", "notice buyout",
]

OFFER_TRIGGERS = [
    "got an offer", "received an offer", "offer letter",
    "ctc breakdown", "joining bonus", "compare offers",
    "they gave me an offer", "i have an offer", "offer came",
    "got the offer",
]

SALARY_TRIGGERS = [
    "salary", "ctc", "compensation", "package", "₹",
    "lakhs", "lakh", "hike", "appraisal", "in-hand",
    "how much", "pay", "increment", "raise", "band",
    "stipend", "fixed pay", "variable",
]

WORK_MENTOR_TRIGGERS = [
    "manager", "my manager", "team", "conflict",
    "politics", "toxic", "promotion", "appraisal", "feedback",
    "performance review", "pip", "micromanage",
    "colleague", "work culture", "team issue", "boss",
]

CAREER_GUIDE_TRIGGERS = [
    "career", "next move", "should i", "what do you think",
    "gcc", "startup", "future", "growth", "switch",
    "job change", "new job", "opportunity", "role",
    "should i stay", "should i leave", "advice",
    "plan", "roadmap", "trajectory",
]


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for consistent matching."""
    return re.sub(r'[^\w\s₹]', ' ', text.lower())


def _contains_any(text: str, triggers: list[str]) -> bool:
    """Check if normalized text contains any trigger phrase."""
    normalized = _normalize(text)
    return any(trigger in normalized for trigger in triggers)


def _confidence_score(text: str, triggers: list[str]) -> float:
    """
    Returns a confidence score 0.0-1.0 based on how many
    trigger phrases appear in the text.
    Multiple matches = higher confidence.
    """
    normalized = _normalize(text)
    matches = sum(1 for t in triggers if t in normalized)
    if matches == 0:
        return 0.0
    elif matches == 1:
        return 0.75
    elif matches == 2:
        return 0.88
    else:
        return 0.95


# ── Phase 1: Hard rules ────────────────────────────────────────────────────────

def _phase1_hard_rules(
    message: str,
    turn_number: int,
    is_first_conversation: bool,
    assessment_just_completed: bool,
) -> Optional[str]:
    """
    Deterministic rules — highest priority.
    Returns skill name if matched, None to fall through.

    Source: Build plan §A.2 Phase 1 hard rules.
    """
    # First turn of first ever conversation → always Career Guide
    if turn_number == 1 and is_first_conversation:
        return CAREER_GUIDE

    # Post-assessment re-engagement → Career Guide (coaching mode)
    if assessment_just_completed:
        return CAREER_GUIDE

    # Candidate confirms resignation / serving notice → Notice Period (HIGH priority)
    if _contains_any(message, NOTICE_PERIOD_TRIGGERS):
        return NOTICE_PERIOD

    # Candidate confirms receiving an offer → Offer Evaluation (HIGH priority)
    if _contains_any(message, OFFER_TRIGGERS):
        return OFFER_EVALUATION

    return None


# ── Phase 2: Intent match ──────────────────────────────────────────────────────

def _phase2_intent_match(message: str) -> Optional[str]:
    """
    Keyword scanning with confidence threshold.
    Returns skill name if confidence > 0.7, None to fall through.

    Source: Build plan §A.2 Phase 2 + skill trigger table.
    """
    scores = {
        SALARY_NAVIGATOR : _confidence_score(message, SALARY_TRIGGERS),
        WORK_MENTOR      : _confidence_score(message, WORK_MENTOR_TRIGGERS),
        NOTICE_PERIOD    : _confidence_score(message, NOTICE_PERIOD_TRIGGERS),
        OFFER_EVALUATION : _confidence_score(message, OFFER_TRIGGERS),
        CAREER_GUIDE     : _confidence_score(message, CAREER_GUIDE_TRIGGERS),
    }

    # Pick the highest confidence skill
    best_skill = max(scores, key=scores.get)
    best_score = scores[best_skill]

    if best_score >= 0.7:
        return best_skill

    return None


# ── Phase 3: Sticky rule ───────────────────────────────────────────────────────

def _phase3_sticky(current_skill: Optional[str]) -> str:
    """
    Keep the current skill if no clear shift detected.
    Prevents jarring mid-conversation skill switches on ambiguous turns.

    If no current skill → fall back to Career Guide (default).
    Source: Build plan §A.2 Phase 3.
    """
    return current_skill if current_skill else DEFAULT_SKILL


# ── Phase 4: LLM fallback ─────────────────────────────────────────────────────

async def _phase4_llm_fallback(
    message: str,
    current_skill: Optional[str],
    conversation_summary: str = "",
) -> str:
    """
    Claude Haiku classification — last resort only.
    Expected frequency: <5% of turns.
    Cost: ~$0.0001/call. Latency: ~300ms.

    Source: Build plan §A.2 Phase 4.
    """
    client = AsyncOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )

    context = f"Current skill: {current_skill or 'none'}"
    if conversation_summary:
        context += f"\nConversation so far: {conversation_summary[:200]}"

    prompt = f"""You are routing a career conversation to the correct skill.

{context}

Candidate just said: "{message}"

Which skill should be active? Choose ONE:
- career_guide: general career trajectory, job change decisions, growth
- salary_navigator: compensation, CTC, salary negotiation, market rates
- work_mentor: manager issues, team conflict, workplace politics, promotion
- notice_period: resignation, serving notice, counter-offer situations
- offer_evaluation: evaluating a specific job offer received

Reply with ONLY the skill name, nothing else."""

    try:
        response = await client.chat.completions.create(
            model=settings.CLAUDE_HAIKU_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            extra_headers={
                "HTTP-Referer": "https://employlabs.com",
                "X-Title": "Zia Skill Router",
            },
        )
        result = response.choices[0].message.content.strip().lower()

        # Validate the returned skill name
        if result in PHASE_A_SKILLS:
            return result

        # If Haiku returned something unexpected, fall back to sticky
        return _phase3_sticky(current_skill)

    except Exception:
        # LLM call failed — fall back to sticky, never crash
        return _phase3_sticky(current_skill)


# ── Main router function ───────────────────────────────────────────────────────

async def route(
    message: str,
    current_skill: Optional[str] = None,
    turn_number: int = 1,
    is_first_conversation: bool = True,
    assessment_just_completed: bool = False,
    conversation_summary: str = "",
) -> tuple[str, str]:
    """
    Routes a candidate message to the correct Ring 3 skill.

    Args:
        message                  : candidate's message text
        current_skill            : currently active skill (None if first turn)
        turn_number              : current turn count (1-indexed)
        is_first_conversation    : True if this is the candidate's first ever session
        assessment_just_completed: True if Nyra assessment just finished
        conversation_summary     : brief summary for LLM fallback context

    Returns:
        Tuple of (skill_name, routing_method) where routing_method is one of:
        "hard_rule" | "intent_match" | "sticky" | "llm_fallback"
    """
    # Phase 1: Hard rules — deterministic, ~0ms
    result = _phase1_hard_rules(
        message=message,
        turn_number=turn_number,
        is_first_conversation=is_first_conversation,
        assessment_just_completed=assessment_just_completed,
    )
    if result:
        return result, "hard_rule"

    # Phase 2: Intent match — keyword scoring, ~5ms
    result = _phase2_intent_match(message)
    if result:
        return result, "intent_match"

    # Phase 3: Sticky rule — keep current, ~0ms
    # Only fall through to LLM if current_skill is also None
    # (i.e. we have NO signal at all)
    if current_skill:
        return _phase3_sticky(current_skill), "sticky"

    # Phase 4: LLM fallback — Claude Haiku, ~300ms
    # Only reaches here when: no hard rule + no keyword match + no current skill
    result = await _phase4_llm_fallback(
        message=message,
        current_skill=current_skill,
        conversation_summary=conversation_summary,
    )
    return result, "llm_fallback"