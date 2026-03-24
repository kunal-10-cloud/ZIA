
"""
Ring 2 — Tests
==============
Run: docker compose exec backend python backend/ring2_context/test_ring2.py

Tests all 7 Ring 2 files for correct structure and behavior.
Ring 2 eval is SOFT SCORE (1-5), not hard fail.
These tests verify structure and logic — character quality is tested
in eval/ring2_tests/ with real LLM calls.
"""

import asyncio
import uuid

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


# ── 1. Import tests ────────────────────────────────────────────────────────────
print("\n── Import tests ──\n")

try:
    from backend.ring2_context.mixing_board import (
        generate_mixing_board_directive, get_stage_default, STAGE_DEFAULTS
    )
    from backend.ring2_context.language_calibrator import (
        detect_hinglish_level, generate_language_directive
    )
    from backend.ring2_context.objectives_tracker import (
        ConversationObjectives, build_initial_objectives
    )
    from backend.ring2_context.relationship_stage import (
        get_stage_name, STAGE_DESCRIPTIONS
    )
    check("All ring2_context modules import without error", True)
except ImportError as e:
    check("All ring2_context modules import without error", False, str(e))
    exit(1)


# ── 2. Mixing board — 5-band directive tests ───────────────────────────────────
print("\n── Mixing board directive tests ──\n")

# Test all 5 Priyanka bands
d_low     = generate_mixing_board_directive(0.1, 0.5)
d_gentle  = generate_mixing_board_directive(0.35, 0.5)
d_medium  = generate_mixing_board_directive(0.55, 0.5)
d_high    = generate_mixing_board_directive(0.75, 0.5)
d_max     = generate_mixing_board_directive(0.95, 0.5)

check("Priyanka 0.1 → MINIMAL directive", "MINIMAL" in d_low)
check("Priyanka 0.35 → GENTLE COMPETENCE directive", "GENTLE COMPETENCE" in d_gentle)
check("Priyanka 0.55 → BALANCED AUTHORITY directive", "BALANCED AUTHORITY" in d_medium)
check("Priyanka 0.75 → AUTHORITY MODE directive", "AUTHORITY MODE" in d_high)
check("Priyanka 0.95 → MAXIMUM directive", "MAXIMUM" in d_max)

# Authority directives should differ measurably
check("0.1 and 0.95 produce different directives",
    d_low != d_max, "Directives should differ across bands")

# Test all 5 Sister bands
s_min  = generate_mixing_board_directive(0.5, 0.1)
s_low  = generate_mixing_board_directive(0.5, 0.35)
s_med  = generate_mixing_board_directive(0.5, 0.55)
s_high = generate_mixing_board_directive(0.5, 0.75)
s_max  = generate_mixing_board_directive(0.5, 0.95)

check("Sister 0.1 → MINIMAL directive", "MINIMAL" in s_min)
check("Sister 0.35 → WARM BUT BOUNDED directive", "WARM BUT BOUNDED" in s_low)
check("Sister 0.55 → GENUINELY CARING directive", "GENUINELY CARING" in s_med)
check("Sister 0.75 → EMOTIONALLY PRESENT directive", "EMOTIONALLY PRESENT" in s_high)
check("Sister 0.95 → MAXIMUM directive", "MAXIMUM" in s_max)

# Interaction 1 default
d1 = generate_mixing_board_directive(0.2, 0.8)
check("Interaction 1 default (0.2, 0.8): warmth dominant (EMOTIONALLY PRESENT)",
    "EMOTIONALLY PRESENT" in d1 or "GENUINELY CARING" in d1)

# Stage defaults
check("Stage 1 default: priyanka=0.2, sister=0.8",
    STAGE_DEFAULTS[1] == {"priyanka": 0.2, "sister": 0.8})
check("Stage 3 default: priyanka=0.6, sister=0.5",
    STAGE_DEFAULTS[3] == {"priyanka": 0.6, "sister": 0.5})


# ── 3. Language calibrator tests ───────────────────────────────────────────────
print("\n── Language calibrator tests ──\n")

check("Empty turns → 'zero' level",
    detect_hinglish_level([]) == "zero")
check("Formal English → 'zero' level",
    detect_hinglish_level(["I want to discuss my career trajectory"]) == "zero")
check("Light Hinglish: 'yaar' detected → 'light'",
    detect_hinglish_level(["That's interesting yaar, what do you think na?"]) == "light")
check("Medium: code-switching detected → 'medium' or higher",
    detect_hinglish_level(["Suno, main kya karoon? This is very confusing yaar na theek hai"]) in ["medium", "heavy"])
check("Before turn 3 → always English regardless",
    "warm English" in generate_language_directive("heavy", turn_number=2))
check("After turn 3, heavy level → Hindi-dominant directive",
    "Hindi-dominant" in generate_language_directive("heavy", turn_number=5))
check("After turn 3, zero level → English directive",
    "formal English" in generate_language_directive("zero", turn_number=5).lower()
    or "warm" in generate_language_directive("zero", turn_number=5).lower())


# ── 4. Relationship stage tests ─────────────────────────────────────────────────
print("\n── Relationship stage tests ──\n")

check("Stage 1 name is 'Stranger'", get_stage_name(1) == "Stranger")
check("Stage 2 name is 'Acquaintance'", get_stage_name(2) == "Acquaintance")
check("Stage 3 name is 'Trusted Advisor'", get_stage_name(3) == "Trusted Advisor")
check("Stage 4 name is 'Inner Circle'", get_stage_name(4) == "Inner Circle")
check("Stage 5 name is 'Life Companion'", get_stage_name(5) == "Life Companion")
check("Stage 1 NOT allowed list includes assessment mention",
    any("assessment" in item.lower() for item in STAGE_DESCRIPTIONS[1]["not_allowed"]))
check("Stage 1 NOT allowed list includes teasing",
    any("teas" in item.lower() for item in STAGE_DESCRIPTIONS[1]["not_allowed"]))


# ── 5. Objectives tracker tests ────────────────────────────────────────────────
print("\n── Objectives tracker tests ──\n")

# Build Stage 1, turn 1, no nudge
obj = build_initial_objectives(
    relationship_stage=1,
    elapsed_minutes=3.0,
    nudge_count=0,
    has_previous_conversations=False,
)
formatted = obj.format_for_prompt()

check("Objectives block is non-empty", len(formatted) > 0)
check("CONVERSATION OBJECTIVES header present",
    "CONVERSATION OBJECTIVES" in formatted)
check("Stage 1: assessment BLOCKED before 10 min",
    "[BLOCKED]" in formatted and "Assessment" in formatted)
check("Stage 1: warm opening is ACTIVE",
    "[ACTIVE]" in formatted and ("warm" in formatted.lower() or "open" in formatted.lower()))

# Build Stage 3 with prior nudge
obj3 = build_initial_objectives(
    relationship_stage=3,
    elapsed_minutes=15.0,
    nudge_count=1,
    has_previous_conversations=True,
)
formatted3 = obj3.format_for_prompt()
check("Stage 3: prior nudge marked as DONE",
    "DONE" in formatted3 and "nudge" in formatted3.lower())
check("Stage 3: previous conversations trigger catch-up objective",
    "open threads" in formatted3.lower() or "last conversation" in formatted3.lower())

# Mark done
obj.mark_done("warm")
check("mark_done() changes status to DONE",
    any(o.status == "DONE" and "warm" in o.description.lower() for o in obj.objectives))


# ── 6. Context assembler — structure test (no DB) ──────────────────────────────
print("\n── Context assembler structure test ──\n")

# Test that it imports and has the right signature
try:
    from backend.ring2_context.context_assembler import assemble_ring2
    import inspect
    sig = inspect.signature(assemble_ring2)
    params = list(sig.parameters.keys())
    check("assemble_ring2 has candidate_id parameter", "candidate_id" in params)
    check("assemble_ring2 has conversation_id parameter", "conversation_id" in params)
    check("assemble_ring2 has db parameter", "db" in params)
    check("assemble_ring2 has current_turn_text parameter", "current_turn_text" in params)
    check("assemble_ring2 is async",
        asyncio.iscoroutinefunction(assemble_ring2))
except Exception as e:
    check("context_assembler imports correctly", False, str(e))


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n── Results: {passed} passed, {failed} failed ──\n")

if failed == 0:
    print("Ring 2 context assembler ready.")
    print("Move to Step 6 — Skill Router (orchestrator/skill_router.py)\n")
else:
    print("Fix failures above.\n")