"""
Orchestrator — Tests (Step 8)
==============================
Run: docker compose exec backend python backend/orchestrator/test_orchestrator.py

Tests:
  - tool_manager.py  : tool hierarchy, masking, session tools
  - compaction.py    : compaction schedule, history splitting
  - prompt_assembler : token estimation, trim logic
  - priority_resolver: all 6 conflict scenarios (covered in separate test)
"""

import asyncio

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


# ── 1. Tool Manager tests ──────────────────────────────────────────────────────
print("\n── Tool Manager tests ──\n")

from backend.orchestrator.tool_manager import (
    CORE_TOOLS, SKILL_TOOLS, get_tools_for_session, get_all_tools_for_session,
)
from backend.orchestrator.skill_router import (
    CAREER_GUIDE, SALARY_NAVIGATOR, NOTICE_PERIOD, OFFER_EVALUATION
)

# Core tools
check("8 core tools defined (architecture doc §14)",
    len(CORE_TOOLS) == 8,
    f"Got {len(CORE_TOOLS)}")

core_names = [t["function"]["name"] for t in CORE_TOOLS]
for expected in [
    "log_behavioral_signal", "schedule_followup", "route_to_dashboard",
    "handoff_to_nyra", "lookup_candidate_profile", "search_market_data",
    "send_whatsapp_message", "update_conversation_state",
]:
    check(f"Core tool '{expected}' present", expected in core_names)

# Skill tools — masking (not removal)
career_tools = get_tools_for_session(CAREER_GUIDE)
salary_tools = get_tools_for_session(SALARY_NAVIGATOR)
notice_tools = get_tools_for_session(NOTICE_PERIOD)

check("Career Guide session has core + career tools",
    len(career_tools) == len(CORE_TOOLS) + len(SKILL_TOOLS[CAREER_GUIDE]),
    f"Got {len(career_tools)}")

check("Salary Navigator session has core + salary tools",
    len(salary_tools) == len(CORE_TOOLS) + len(SKILL_TOOLS[SALARY_NAVIGATOR]),
    f"Got {len(salary_tools)}")

check("Notice Period session has core + notice tools",
    len(notice_tools) == len(CORE_TOOLS) + len(SKILL_TOOLS[NOTICE_PERIOD]))

# Masking verified: career tools don't appear in salary session
career_specific = [
    t["function"]["name"] for t in SKILL_TOOLS[CAREER_GUIDE]
    if t["function"]["name"] not in [t2["function"]["name"] for t2 in SKILL_TOOLS[SALARY_NAVIGATOR]]
]
if career_specific:
    salary_tool_names = [t["function"]["name"] for t in salary_tools]
    check("Career-specific tools masked in Salary Navigator session",
        not any(n in salary_tool_names for n in career_specific))

# All tools for session init
all_tools = get_all_tools_for_session()
check("All tools ≥ 8 (core + skill tools deduplicated)",
    len(all_tools) >= 8,
    f"Got {len(all_tools)}")


# ── 2. Compaction tests ────────────────────────────────────────────────────────
print("\n── Compaction tests ──\n")

from backend.orchestrator.compaction import (
    needs_compaction, split_history, build_compacted_history,
    Turn, FULL_HISTORY_TURNS, RECENT_TURNS_ALWAYS_FULL,
)

# Compaction schedule
check("Turn 1 → no compaction needed",    needs_compaction(1) is False)
check("Turn 10 → no compaction needed",   needs_compaction(10) is False)
check("Turn 11 → compaction needed",      needs_compaction(11) is True)
check("Turn 15 → no compaction needed",   needs_compaction(15) is False)
check("Turn 21 → compaction needed",      needs_compaction(21) is True)
check("Turn 30 → compaction needed",      needs_compaction(30) is True)
check("Turn 40 → compaction needed",      needs_compaction(40) is True)

# History splitting
sample_turns = [
    Turn(role="user", content=f"turn {i}", turn_number=i)
    for i in range(1, 16)
]
to_compact, recent = split_history(sample_turns)
check(f"15 turns: recent = last {RECENT_TURNS_ALWAYS_FULL}",
    len(recent) == RECENT_TURNS_ALWAYS_FULL,
    f"Got {len(recent)}")
check(f"15 turns: to_compact = {15 - RECENT_TURNS_ALWAYS_FULL}",
    len(to_compact) == 15 - RECENT_TURNS_ALWAYS_FULL,
    f"Got {len(to_compact)}")
check("Recent turns are the LAST turns",
    recent[-1].content == "turn 15")
check("Compact turns are the OLDEST turns",
    to_compact[0].content == "turn 1")

# Build compacted history
history = build_compacted_history(sample_turns, existing_summary="Test summary.")
check("CompactedHistory has compacted_summary",
    history.compacted_summary == "Test summary.")
check("CompactedHistory has recent_turns in OpenAI format",
    all("role" in t and "content" in t for t in history.recent_turns))
check("CompactedHistory total_turns = 15",
    history.total_turns == 15)
check("format_for_prompt() includes summary and recent turns",
    "Test summary" in history.format_for_prompt()
    and "turn 11" in history.format_for_prompt())


# ── 3. Prompt assembler tests ──────────────────────────────────────────────────
print("\n── Prompt assembler tests ──\n")

from backend.orchestrator.prompt_assembler import (
    estimate_tokens, _trim_to_budget, build_messages_for_llm,
    TOKEN_BUDGET_MAX,
)

# Token estimation
check("Token estimate works for non-empty string",
    estimate_tokens("hello world") > 0)
check("Token estimate scales with length",
    estimate_tokens("a " * 100) > estimate_tokens("a " * 10))

# Token budget max matches settings
check(f"TOKEN_BUDGET_MAX = {TOKEN_BUDGET_MAX} (architecture doc: 10,700)",
    TOKEN_BUDGET_MAX == 10700,
    f"Got {TOKEN_BUDGET_MAX}")

# Trim logic
long_history = "word " * 5000
trimmed = _trim_to_budget(
    ring0="Ring0 " * 200,
    ring1="Ring1 " * 150,
    ring2="Ring2 " * 200,
    ring3="Ring3 " * 100,
    overrides="",
    history=long_history,
    max_tokens=TOKEN_BUDGET_MAX,
)
check("Trim keeps output within token budget",
    estimate_tokens(trimmed) <= TOKEN_BUDGET_MAX + 100,  # small margin for estimate rounding
    f"Got ~{estimate_tokens(trimmed)} tokens")
check("Trim never removes Ring 0 content",
    "Ring0" in trimmed)
check("Trim never removes Ring 1 content",
    "Ring1" in trimmed)

# build_messages_for_llm
system, messages = build_messages_for_llm(
    system_prompt="You are Zia.",
    conversation_turns=[
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hey!"},
    ],
    current_message="what should i do?",
)
check("build_messages_for_llm returns system prompt",
    system == "You are Zia.")
check("build_messages_for_llm appends current message",
    messages[-1] == {"role": "user", "content": "what should i do?"})
check("build_messages_for_llm includes prior turns",
    len(messages) == 3)


# ── 4. Priority resolver — all 6 conflict scenarios ───────────────────────────
print("\n── Priority Resolver — 6 conflict scenarios ──\n")

from backend.orchestrator.priority_resolver import (
    PriorityResolver, ConversationState, detect_high_stakes,
    SUPPRESS_ASSESSMENT_NUDGE, ENFORCE_FRIENDLY_FIRST,
    SUPPRESS_REPEAT_NUDGE, ACTIVATE_VOSS_PROTOCOL,
    ENFORCE_WE_NOT_YOU, ENFORCE_MEMORY_FORGET,
    ENFORCE_FACTS_NOT_OPINIONS,
)

resolver = PriorityResolver()

# Scenario 1: Early nudge suppressed
state = ConversationState(elapsed_minutes=5.0, ring3_content="assessment nyra")
result = resolver.resolve(state)
check("Scenario 1: Early nudge → SUPPRESS_ASSESSMENT_NUDGE",
    any("10-minute" in o or "timer" in o for o in result.overrides),
    f"Overrides: {result.overrides}")
check("Scenario 1: blocked_nudge = True", result.blocked_nudge)

# Scenario 2: Stage 1 friendly first
state = ConversationState(relationship_stage=1, turn_number=1)
result = resolver.resolve(state)
check("Scenario 2: Stage 1 turn 1 → ENFORCE_FRIENDLY_FIRST",
    any("Stage 1" in o or "Warmth MUST" in o for o in result.overrides),
    f"Overrides: {result.overrides}")

# Scenario 3: Voss activated
state = ConversationState(high_stakes_detected=True)
result = resolver.resolve(state)
check("Scenario 3: high_stakes → ACTIVATE_VOSS_PROTOCOL",
    any("Voss" in o for o in result.overrides),
    f"Overrides: {result.overrides}")
check("Scenario 3: voss_activated = True", result.voss_activated)

# Scenario 4: Memory forget
state = ConversationState(candidate_message="please forget that")
result = resolver.resolve(state)
check("Scenario 4: forget request → ENFORCE_MEMORY_FORGET",
    any("forget" in o.lower() or "Gone" in o for o in result.overrides),
    f"Overrides: {result.overrides}")

# Scenario 5: Company opinion
state = ConversationState(ring3_content="this is a good company to work for")
result = resolver.resolve(state)
check("Scenario 5: company opinion → ENFORCE_FACTS_NOT_OPINIONS",
    any("defamation" in o or "FACTS" in o for o in result.overrides),
    f"Overrides: {result.overrides}")

# Scenario 6: "You should" language
state = ConversationState(ring3_content="you should update your resume now")
result = resolver.resolve(state)
check("Scenario 6: 'you should' → ENFORCE_WE_NOT_YOU",
    any("we" in o.lower() for o in result.overrides),
    f"Overrides: {result.overrides}")

# detect_high_stakes
check("detect_high_stakes: counter offer detected",
    detect_high_stakes("they gave me a counter offer to stay") is True)
check("detect_high_stakes: resignation detected",
    detect_high_stakes("I resigned this morning") is True)
check("detect_high_stakes: normal message = False",
    detect_high_stakes("tell me about GCC companies") is False)

# Repeat nudge suppression
state = ConversationState(
    elapsed_minutes=15.0,
    nudge_sent_this_session=True,
    ring3_content="assessment nyra",
)
result = resolver.resolve(state)
check("Repeat nudge → SUPPRESS_REPEAT_NUDGE",
    any("Maximum 1" in o or "already sent" in o for o in result.overrides),
    f"Overrides: {result.overrides}")


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n── Results: {passed} passed, {failed} failed ──\n")

if failed == 0:
    print("Step 8 complete: tool_manager, compaction, prompt_assembler all ready.")
    print("Move to Step 9 — Conversation Engine.\n")
else:
    print("Fix failures above.\n")