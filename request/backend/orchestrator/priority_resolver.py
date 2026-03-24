"""
Orchestrator — Priority Resolver
===================================
Source: Architecture doc §16 — Priority Resolution
        Build plan §A.6

Lower ring number ALWAYS wins on conflict.
Ring 0 > Ring 1 > Ring 2 > Ring 3.

This is a rules engine — NOT an LLM call.
Runs after prompt assembly, before the LLM call.
Deterministic, fast (~10ms).

All 6 conflict scenarios (architecture doc §16):
  1. Skill wants to nudge assessment before 10-minute timer      → Ring 1 wins
  2. Stage 1 candidate — skill wants authority move              → Ring 1 wins
  3. High-stakes moment — Voss must activate                     → Ring 1 wins
  4. Candidate requests memory deletion                          → Ring 1 wins
  5. Skill producing company opinion (defamation risk)           → Ring 1 wins
  6. Skill using "you should" language (Ring 0: "we" not "you")  → Ring 0 wins

Plus:
  - Repeat nudge suppression (Ring 1: max 1 nudge per session)

Implementation note (architecture doc §16):
  Overrides are appended as a directive block to the assembled prompt
  by prompt_assembler.py. The LLM sees them as hard constraints
  that override any conflicting Ring 3 instructions.
"""

from dataclasses import dataclass, field

# ── Override directive strings ─────────────────────────────────────────────────
# These are injected verbatim into the assembled prompt as override blocks.
# Test assertions check for specific substrings — do NOT change those substrings.

SUPPRESS_ASSESSMENT_NUDGE = (
    "PRIORITY OVERRIDE (Ring 1 wins over Ring 3): 10-minute timer has NOT elapsed. "
    "DO NOT mention assessment, Nyra, or the Signal Assessment in any form. "
    "Continue the current conversation naturally. The nudge is blocked by timer policy."
)

ENFORCE_FRIENDLY_FIRST = (
    "PRIORITY OVERRIDE (Ring 1 wins over Ring 3): Stage 1 candidate — Warmth MUST lead. "
    "This is first contact. No authority moves, no Priyanka energy, no teasing, no challenging. "
    "Pure warmth and genuine curiosity only. The candidate's trust has not been established yet."
)

SUPPRESS_REPEAT_NUDGE = (
    "PRIORITY OVERRIDE (Ring 1 wins over Ring 3): Maximum 1 nudge per session. "
    "A nudge has already sent this session — do NOT mention assessment, Nyra, or the "
    "Signal Assessment again. Ring 1 policy is absolute: never repeat the nudge within "
    "the same conversation."
)

ACTIVATE_VOSS_PROTOCOL = (
    "PRIORITY OVERRIDE (Ring 1 wins over Ring 2): High-stakes moment detected. "
    "Voss protocol is now ACTIVE. Use: mirror (repeat last 1-3 words), label emotions "
    "('It sounds like...'), calibrated questions ('What would need to change for...'), "
    "and tactical silence (3-5 seconds after mirrors/labels). "
    "Warmth overrides any humor or authority impulse right now. Hold the space."
)

ENFORCE_WE_NOT_YOU = (
    "PRIORITY OVERRIDE (Ring 0 wins over Ring 3): Replace all 'you should' language with "
    "'we' framing. Ring 0 rule: Zia never prescribes — she collaborates. "
    "Use 'let's figure this out', 'we can look at', 'what if we tried' instead. "
    "The word 'should' directed at the candidate must not appear in this response."
)

ENFORCE_MEMORY_FORGET = (
    "PRIORITY OVERRIDE (Ring 1 wins over Ring 3): Candidate has asked to forget something. "
    "Gone — do not reference, hint at, or circle back to the forgotten topic in any way. "
    "Treat it as if it was never said. Pivot naturally with light energy: "
    "'Gone. Never happened 😄 — so, where were we?'"
)

ENFORCE_FACTS_NOT_OPINIONS = (
    "PRIORITY OVERRIDE (Ring 1 wins over Ring 3): FACTS only about companies and employers. "
    "Do NOT express opinions, judgments, or recommendations about specific companies. "
    "Defamation and brand risk are real. State market data only: salary ranges, "
    "demand signals, role scope, growth patterns. Never: 'X is a good/bad company.'"
)

# ── High-stakes triggers (for detect_high_stakes) ─────────────────────────────
# These phrases in a candidate's message signal a high-stakes moment
# where Voss protocol should activate automatically.
# Source: Architecture doc §16 (Voss activation conditions) +
#         Ring 1 Behavioral OS (Voss protocol)

_HIGH_STAKES_TRIGGERS = [
    # Resignation / notice
    "resigned", "i resigned", "i have resigned", "put in my papers",
    "gave my notice", "serving notice", "serving my notice",
    # Counter-offers (financially high-stakes)
    "counter offer", "counter-offer", "counteroffer",
    "they want me to stay", "asking me to stay",
    # Layoff / job loss
    "laid off", "layoff", "let go", "fired", "terminated",
    "lost my job", "job at risk",
    # Crisis / distress signals
    "mental health", "anxiety", "depression", "burnout",
    "family emergency", "health issue", "i'm struggling",
    "feeling overwhelmed", "i don't know what to do",
]

# ── Company opinion detection patterns ────────────────────────────────────────
# Patterns that indicate Ring 3 content contains a company opinion/judgment.
# These violate Ring 1 (facts-not-opinions, defamation risk).

_COMPANY_OPINION_PATTERNS = [
    "good company", "bad company", "great company", "terrible company",
    "best company", "worst company", "amazing company", "awful company",
    "toxic company", "is a good", "is a bad", "is not a good",
    "is great to work", "is terrible to work", "recommend joining",
    "don't join", "avoid this company", "stay away from",
    "best place to work", "worst place to work",
    "toxic culture", "great culture", "bad culture",
]

# ── Forget request detection ───────────────────────────────────────────────────

_FORGET_TRIGGERS = [
    "forget that", "forget i said", "don't remember that",
    "dont remember that", "please forget", "forget what i said",
    "never mind that", "ignore what i said",
]


# ── ConversationState ─────────────────────────────────────────────────────────

@dataclass
class ConversationState:
    """
    Snapshot of the current conversation state passed to the priority resolver.

    Fields:
        elapsed_minutes         : minutes elapsed in the current session
        ring3_content           : the active skill's prompt fragment content
                                  (used to detect what Ring 3 is attempting)
        candidate_message       : the candidate's current raw message
        relationship_stage      : 1-5 stage from Layer 4 arc
        turn_number             : current turn count (1-indexed)
        high_stakes_detected    : True if a high-stakes signal was detected
                                  in the candidate's message (see detect_high_stakes)
        nudge_sent_this_session : True if an assessment nudge was already sent
                                  this session (Ring 1: max 1 per session)
    """
    elapsed_minutes: float = 0.0
    ring3_content: str = ""
    candidate_message: str = ""
    relationship_stage: int = 2        # default Stage 2 (returning, trust building)
    turn_number: int = 1
    high_stakes_detected: bool = False
    nudge_sent_this_session: bool = False


# ── ResolutionResult ──────────────────────────────────────────────────────────

@dataclass
class ResolutionResult:
    """
    Output of PriorityResolver.resolve().

    Fields:
        overrides       : list of override directive strings to inject into the prompt.
                          Empty list = no conflicts detected.
        blocked_nudge   : True if assessment nudge was blocked this turn.
        voss_activated  : True if Voss protocol was activated this turn.
    """
    overrides: list = field(default_factory=list)
    blocked_nudge: bool = False
    voss_activated: bool = False


# ── Helper functions ───────────────────────────────────────────────────────────

def detect_high_stakes(message: str) -> bool:
    """
    Returns True if the candidate's message contains a high-stakes signal.

    Used by the conversation engine to set ConversationState.high_stakes_detected
    before calling the priority resolver.

    Source: Architecture doc §16 (Voss activation conditions).
    """
    lowered = message.lower()
    return any(trigger in lowered for trigger in _HIGH_STAKES_TRIGGERS)


def _has_assessment_intent(ring3_content: str) -> bool:
    """True if ring3_content contains an assessment/Nyra nudge attempt."""
    lowered = ring3_content.lower()
    return "assessment" in lowered or "nyra" in lowered


def _has_company_opinion(ring3_content: str) -> bool:
    """True if ring3_content expresses a company opinion (defamation risk)."""
    lowered = ring3_content.lower()
    return any(pattern in lowered for pattern in _COMPANY_OPINION_PATTERNS)


def _has_you_should(ring3_content: str) -> bool:
    """True if ring3_content uses 'you should' language (Ring 0 violation)."""
    return "you should" in ring3_content.lower()


def _has_forget_request(candidate_message: str) -> bool:
    """True if candidate is asking Zia to forget something (Ring 1 memory rule)."""
    lowered = candidate_message.lower()
    return any(trigger in lowered for trigger in _FORGET_TRIGGERS)


# ── Priority Resolver ─────────────────────────────────────────────────────────

class PriorityResolver:
    """
    Rules engine that scans the assembled prompt state for conflicts and
    returns override directives.

    Lower ring number ALWAYS wins. Deterministic, ~10ms.
    Never makes an LLM call.

    Source: Architecture doc §16.
    """

    def resolve(self, state: ConversationState) -> ResolutionResult:
        """
        Evaluates all conflict scenarios and returns a ResolutionResult.

        Checks run in priority order (Ring 0 > Ring 1 > Ring 2 > Ring 3).
        Multiple overrides can be active simultaneously.

        Args:
            state: current conversation state snapshot

        Returns:
            ResolutionResult with override directives and flags
        """
        overrides: list[str] = []
        blocked_nudge = False
        voss_activated = False

        # ── Check 1: Assessment nudge before 10-minute timer (Ring 1 > Ring 3) ──
        # Rule: NO mention of assessment in first 10 minutes of any conversation.
        # Source: Architecture doc §16, nudge_policy.py Ring 1 rule.
        if state.elapsed_minutes < 10.0 and _has_assessment_intent(state.ring3_content):
            overrides.append(SUPPRESS_ASSESSMENT_NUDGE)
            blocked_nudge = True

        # ── Check 2: Repeat nudge within same session (Ring 1 > Ring 3) ─────────
        # Rule: Maximum 1 nudge per conversation. If sent, never repeat.
        # Source: Architecture doc §16, Ring 1 nudge policy.
        if state.nudge_sent_this_session and _has_assessment_intent(state.ring3_content):
            overrides.append(SUPPRESS_REPEAT_NUDGE)
            blocked_nudge = True

        # ── Check 3: Stage 1 — friendly first, sovereign earned (Ring 1 > Ring 3) ─
        # Rule: Stage 1 candidates must always receive warmth-led responses.
        # No authority, no challenging, no Priyanka energy until trust is built.
        # Source: Architecture doc §16, Character Bible §4 (friendly first).
        if state.relationship_stage == 1:
            overrides.append(ENFORCE_FRIENDLY_FIRST)

        # ── Check 4: High-stakes moment → Voss protocol (Ring 1 > Ring 2) ────────
        # Rule: When high-stakes detected, Voss overrides even humor-heavy
        # personalized equilibrium from Ring 2.
        # Source: Architecture doc §16 (Voss activation scenario).
        if state.high_stakes_detected:
            overrides.append(ACTIVATE_VOSS_PROTOCOL)
            voss_activated = True

        # ── Check 5: Memory deletion request (Ring 1 > Ring 3) ───────────────────
        # Rule: "Forget that" = deleted immediately. No questions, no drama.
        # Source: Architecture doc §16, Layer 3 Memory "forget rule".
        if _has_forget_request(state.candidate_message):
            overrides.append(ENFORCE_MEMORY_FORGET)

        # ── Check 6: Company opinion / defamation risk (Ring 1 > Ring 3) ─────────
        # Rule: FACTS only about companies. No recommendations, judgments, or ratings.
        # Source: Architecture doc §16, Layer 2 Boundaries (brand/legal risk).
        if _has_company_opinion(state.ring3_content):
            overrides.append(ENFORCE_FACTS_NOT_OPINIONS)

        # ── Check 7: "You should" language — Ring 0 "we" rule (Ring 0 > Ring 3) ──
        # Rule: Zia never prescribes. "You should" is a Ring 0 violation.
        # Always reframe as collaborative "we" language.
        # Source: Architecture doc §16, Ring 0 Identity Kernel.
        if _has_you_should(state.ring3_content):
            overrides.append(ENFORCE_WE_NOT_YOU)

        return ResolutionResult(
            overrides=overrides,
            blocked_nudge=blocked_nudge,
            voss_activated=voss_activated,
        )