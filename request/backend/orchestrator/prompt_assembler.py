"""
Orchestrator — Prompt Assembler
==================================
Source: Architecture doc §12 — The Orchestrator: Prompt Assembly Pipeline
        Architecture doc token budget breakdown (§12)

Builds the complete system prompt from all 4 rings + history.
Called by conversation_engine.py on every turn.

Token budget (architecture doc §12):
  Ring 0 (static)           ~2,500  ← KV-cache: 100% hit
  Ring 1 (static)           ~2,000  ← KV-cache: 100% hit
  Ring 2 (dynamic/conv)     ~2,500  ← KV-cache: ~90% hit
  Ring 3 (dynamic/skill)    ~1,500  ← KV-cache: varies
  Conversation objectives     ~200
  Recent history (5 turns)  ~1,500  ← changes every turn
  Compacted older history     ~500  ← changes every 10 turns
  ─────────────────────────────────
  Total                    ~10,700

KV-cache rule (from Manus): Ring 0 + Ring 1 are IDENTICAL across
ALL candidates and ALL turns. This guarantees ~4,500 tokens of
KV-cache hit on every single call.
"""

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.ring0_identity import RING0_PROMPT
from backend.ring1_behavior import RING1_PROMPT
from backend.ring2_context.context_assembler import assemble_ring2
from backend.ring2_context.objectives_tracker import ConversationObjectives
from backend.orchestrator.compaction import CompactedHistory
from backend.orchestrator.priority_resolver import ResolutionResult
from backend.config.settings import settings

# Max token budget — hard limit (architecture doc §12)
TOKEN_BUDGET_MAX = settings.TOKEN_BUDGET_MAX  # 10,700
TOKEN_BUDGET_WARN = settings.TOKEN_BUDGET_WARN  # 9,000


def estimate_tokens(text: str) -> int:
    """Rough token estimate: words * 1.3"""
    return int(len(text.split()) * 1.3)


async def assemble_prompt(
    candidate_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession,
    ring3_prompt: str,
    history: CompactedHistory,
    current_turn_text: str = "",
    turn_number: int = 1,
    elapsed_minutes: float = 0.0,
    recent_candidate_turns: Optional[list[str]] = None,
    door_open_topics: Optional[list[str]] = None,
    objectives: Optional[ConversationObjectives] = None,
    resolution: Optional[ResolutionResult] = None,
) -> tuple[str, int]:
    """
    Assembles the complete system prompt for one LLM call.

    Args:
        candidate_id          : which candidate
        conversation_id       : current session
        db                    : async db session
        ring3_prompt          : active skill's prompt fragment
        history               : compacted conversation history
        current_turn_text     : candidate's current message
        turn_number           : turn counter
        elapsed_minutes       : minutes elapsed in session
        recent_candidate_turns: last 3-5 candidate messages (language detection)
        door_open_topics      : personal topics candidate opened
        objectives            : current conversation objectives
        resolution            : priority resolver output (overrides to append)

    Returns:
        Tuple of (assembled_system_prompt, estimated_token_count)
    """

    # ── Ring 0 + Ring 1 (static — KV-cache 100% hit) ──────────────────────────
    ring0 = RING0_PROMPT
    ring1 = RING1_PROMPT

    # ── Ring 2 (dynamic per candidate) ────────────────────────────────────────
    ring2 = await assemble_ring2(
        candidate_id=candidate_id,
        conversation_id=conversation_id,
        db=db,
        current_turn_text=current_turn_text,
        turn_number=turn_number,
        elapsed_minutes=elapsed_minutes,
        recent_candidate_turns=recent_candidate_turns,
        door_open_topics=door_open_topics,
        objectives=objectives,
    )

    # ── Ring 3 (dynamic per skill) ─────────────────────────────────────────────
    ring3 = (
        "================================================================\n"
        "RING 3 — ACTIVE SKILL\n"
        "================================================================\n\n"
        + ring3_prompt
        + "\n"
    )

    # ── Priority resolver overrides (appended after Ring 3) ───────────────────
    overrides_block = ""
    if resolution and resolution.overrides:
        overrides_block = (
            "\n--- PRIORITY OVERRIDES (lower ring wins) ---\n"
            + "\n".join(f"• {o}" for o in resolution.overrides)
            + "\n"
        )

    # ── Conversation history ───────────────────────────────────────────────────
    history_block = history.format_for_prompt()

    # ── Assemble ───────────────────────────────────────────────────────────────
    assembled = (
        ring0
        + ring1
        + ring2
        + ring3
        + overrides_block
        + history_block
    )

    token_count = estimate_tokens(assembled)

    # ── Token budget warning ───────────────────────────────────────────────────
    if token_count > TOKEN_BUDGET_MAX:
        # Log but don't crash — trim history if over budget
        assembled = _trim_to_budget(
            ring0, ring1, ring2, ring3,
            overrides_block, history_block,
            TOKEN_BUDGET_MAX,
        )
        token_count = estimate_tokens(assembled)

    return assembled, token_count


def _trim_to_budget(
    ring0: str,
    ring1: str,
    ring2: str,
    ring3: str,
    overrides: str,
    history: str,
    max_tokens: int,
) -> str:
    """
    If over budget, trim history first (never trim rings).
    Rings 0-3 are never compromised — only history is trimmed.
    """
    base = ring0 + ring1 + ring2 + ring3 + overrides
    base_tokens = estimate_tokens(base)
    remaining = max_tokens - base_tokens

    if remaining <= 0:
        # Rings alone exceed budget — log critical error, return base only
        return base + "\n[HISTORY OMITTED: token budget exceeded]\n"

    # Trim history lines until within budget
    history_lines = history.split("\n")
    trimmed = []
    used = 0
    for line in history_lines:
        line_tokens = estimate_tokens(line)
        if used + line_tokens > remaining:
            break
        trimmed.append(line)
        used += line_tokens

    return base + "\n".join(trimmed)


def build_messages_for_llm(
    system_prompt: str,
    conversation_turns: list[dict],
    current_message: str,
) -> tuple[str, list[dict]]:
    """
    Formats the system prompt and message history for the OpenAI-compatible API.

    Returns:
        Tuple of (system_prompt, messages_list)
        where messages_list is in OpenAI chat format.
    """
    messages = list(conversation_turns)
    messages.append({"role": "user", "content": current_message})
    return system_prompt, messages