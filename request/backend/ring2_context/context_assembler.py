"""
Ring 2 — Context Assembler
============================
Source: Architecture doc §10 Ring 2 — all 8 components
        Architecture doc ring2_context/context_assembler.py

THE main Ring 2 function. Called by the orchestrator on every turn.
Assembles all 8 Ring 2 components into a single ~2,500 token block.

Ring 2 contains (architecture doc §10):
  1. Candidate profile summary         — profile_loader.py
  2. Mixing board values                — mixing_board.py
  3. Relationship stage                 — relationship_stage.py
  4. Episodic memories                  — memory_retriever.py
  5. Language calibration               — language_calibrator.py
  6. Conversation objectives            — objectives_tracker.py
  7. Conversation summary               — from CompanionConversation.compacted_summary
  8. Assessment status                  — from CompanionProfile

Token budget: ~2,500 tokens total (architecture doc §12 token breakdown).

Phase A note:
  If the candidate has no DB profile yet (new candidate, test session),
  assemble_ring2 returns a clean stub Ring 2 with safe defaults.
  This allows text conversations during Phase A without seeded DB data.
  Phase B wires real memory retrieval and profile persistence.
"""

import uuid
import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ring2_context.mixing_board import generate_mixing_board_directive
from backend.ring2_context.profile_loader import load_profile_summary
from backend.ring2_context.relationship_stage import load_relationship_stage
from backend.ring2_context.memory_retriever import get_relevant_memories
from backend.ring2_context.language_calibrator import (
    detect_hinglish_level,
    generate_language_directive,
)
from backend.ring2_context.objectives_tracker import (
    ConversationObjectives,
    build_initial_objectives,
)

logger = logging.getLogger(__name__)

# Ring 2 token budget (architecture doc §12)
RING2_TOKEN_BUDGET = 2500


def _build_stub_ring2(
    elapsed_minutes: float = 0.0,
    turn_number: int = 1,
    recent_candidate_turns: Optional[list[str]] = None,
) -> str:
    """
    Returns a minimal but valid Ring 2 block when no candidate profile exists.

    Used in Phase A for new/unknown candidates.
    Applies first-interaction defaults:
      - Priyanka 0.2, Sister 0.8  (friendly first, architecture doc §9)
      - Relationship stage 1
      - No episodic memories
      - Language: warm English, no Hinglish yet

    Phase B replaces this with real DB-backed assembly.
    """
    recent_candidate_turns = recent_candidate_turns or []

    mixing_block = generate_mixing_board_directive(priyanka=0.2, sister=0.8)

    hinglish_level = detect_hinglish_level(recent_candidate_turns)
    language_block = generate_language_directive(hinglish_level, turn_number)

    objectives = build_initial_objectives(
        relationship_stage=1,
        elapsed_minutes=elapsed_minutes,
        nudge_count=0,
        has_previous_conversations=False,
    )
    objectives_block = objectives.format_for_prompt()

    stub_profile = (
        "--- CANDIDATE PROFILE ---\n"
        "Status: New candidate — no profile data yet.\n"
        "Zia should gather basic profile information naturally during this conversation.\n"
        "Key things to learn: current role, YoE, company, tech stack, career goals.\n\n"
    )

    stub_stage = (
        "--- RELATIONSHIP STAGE ---\n"
        "Stage 1: First contact. Warmth leads. No authority moves.\n"
        "Friendly first — sovereign confidence earns its way in.\n\n"
    )

    stub_memory = (
        "--- EPISODIC MEMORIES ---\n"
        "No previous conversations on record. This is the first interaction.\n\n"
    )

    ring2 = (
        "================================================================\n"
        "RING 2 — CANDIDATE CONTEXT (this candidate, this conversation)\n"
        "================================================================\n\n"
        + stub_profile
        + mixing_block
        + stub_stage
        + stub_memory
        + language_block
        + objectives_block
    )

    return ring2


async def assemble_ring2(
    candidate_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession,
    current_turn_text: str = "",
    turn_number: int = 1,
    elapsed_minutes: float = 0.0,
    recent_candidate_turns: Optional[list[str]] = None,
    door_open_topics: Optional[list[str]] = None,
    objectives: Optional[ConversationObjectives] = None,
) -> str:
    """
    Assembles the complete Ring 2 block for one LLM call.

    Falls back to _build_stub_ring2 if the candidate has no DB profile
    or if any DB call fails. Never crashes a live conversation.

    Args:
        candidate_id          : which candidate
        conversation_id       : current session
        db                    : async db session
        current_turn_text     : what the candidate just said
        turn_number           : turn counter (1-indexed)
        elapsed_minutes       : minutes elapsed in this session
        recent_candidate_turns: last 3-5 candidate messages (for language detection)
        door_open_topics      : personal topics candidate opened this session
        objectives            : current conversation objectives state

    Returns:
        Ring 2 prompt block string (~2,500 tokens).
        Injected between Ring 1 and Ring 3 in the assembled prompt.
    """
    recent_candidate_turns = recent_candidate_turns or []

    try:
        return await _assemble_ring2_from_db(
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
    except Exception as e:
        # Log the error but never crash the conversation.
        # Phase A: most errors here are "no candidate profile" — expected.
        # Phase B: real profiles exist and this branch should never trigger.
        logger.warning(
            f"Ring 2 assembly fell back to stub for candidate {candidate_id}: {e}"
        )
        return _build_stub_ring2(
            elapsed_minutes=elapsed_minutes,
            turn_number=turn_number,
            recent_candidate_turns=recent_candidate_turns,
        )


async def _assemble_ring2_from_db(
    candidate_id: uuid.UUID,
    conversation_id: uuid.UUID,
    db: AsyncSession,
    current_turn_text: str,
    turn_number: int,
    elapsed_minutes: float,
    recent_candidate_turns: list[str],
    door_open_topics: Optional[list[str]],
    objectives: Optional[ConversationObjectives],
) -> str:
    """
    Full Ring 2 assembly from DB. Called by assemble_ring2.
    Raises on any DB error — caller catches and falls back to stub.
    """
    from backend.models.companion_profile import CompanionProfile
    from backend.models.companion_conversation import CompanionConversation

    # ── Load candidate profile ─────────────────────────────────────────────────
    profile_result = await db.execute(
        select(CompanionProfile).where(CompanionProfile.id == candidate_id)
    )
    profile = profile_result.scalar_one_or_none()

    # No profile = new candidate → use stub (clean, not an error)
    if profile is None:
        return _build_stub_ring2(
            elapsed_minutes=elapsed_minutes,
            turn_number=turn_number,
            recent_candidate_turns=recent_candidate_turns,
        )

    # ── 1. Profile summary ─────────────────────────────────────────────────────
    profile_block = await load_profile_summary(candidate_id, db)

    # ── 2. Mixing board directive ──────────────────────────────────────────────
    priyanka = profile.mixing_board_priyanka
    sister = profile.mixing_board_sister
    mixing_block = generate_mixing_board_directive(priyanka, sister)

    # ── 3. Relationship stage ──────────────────────────────────────────────────
    stage_block = await load_relationship_stage(candidate_id, db)

    # ── 4. Episodic memories ───────────────────────────────────────────────────
    memory_block = await get_relevant_memories(
        candidate_id=candidate_id,
        current_turn_text=current_turn_text,
        db=db,
        top_k=5,
        door_open_topics=door_open_topics,
    )

    # ── 5. Language calibration ────────────────────────────────────────────────
    hinglish_level = detect_hinglish_level(recent_candidate_turns)
    language_block = generate_language_directive(hinglish_level, turn_number)

    # ── 6. Conversation objectives ─────────────────────────────────────────────
    if objectives is None:
        nudge_count = profile.nudge_count
        relationship_stage = profile.relationship_stage

        conv_result = await db.execute(
            select(CompanionConversation).where(
                CompanionConversation.candidate_id == candidate_id,
                CompanionConversation.id != conversation_id,
            ).limit(1)
        )
        has_previous = conv_result.scalar_one_or_none() is not None

        objectives = build_initial_objectives(
            relationship_stage=relationship_stage,
            elapsed_minutes=elapsed_minutes,
            nudge_count=nudge_count,
            has_previous_conversations=has_previous,
        )

    objectives_block = objectives.format_for_prompt()

    # ── 7. Conversation summary (compacted from previous sessions) ─────────────
    conv_result = await db.execute(
        select(CompanionConversation).where(
            CompanionConversation.candidate_id == candidate_id,
            CompanionConversation.id != conversation_id,
            CompanionConversation.compacted_summary.isnot(None),
        ).order_by(CompanionConversation.started_at.desc()).limit(3)
    )
    previous_convs = conv_result.scalars().all()

    summary_block = ""
    if previous_convs:
        lines = ["--- PREVIOUS CONVERSATIONS (compacted) ---"]
        for conv in previous_convs:
            lines.append(conv.compacted_summary)
        lines.append("")
        summary_block = "\n".join(lines)

    # ── 8. Assessment status ───────────────────────────────────────────────────
    assessment_block = (
        f"--- ASSESSMENT STATUS ---\n"
        f"Status: {profile.assessment_status}\n"
        f"Nudges sent this lifetime: {profile.nudge_count}\n"
    )
    if profile.nudge_last_declined_at:
        assessment_block += (
            f"Last declined: "
            f"{profile.nudge_last_declined_at.strftime('%Y-%m-%d')}\n"
        )
    assessment_block += "\n"

    # ── Assemble ───────────────────────────────────────────────────────────────
    ring2 = (
        "================================================================\n"
        "RING 2 — CANDIDATE CONTEXT (this candidate, this conversation)\n"
        "================================================================\n\n"
        + profile_block
        + mixing_block
        + stage_block
        + memory_block
        + language_block
        + objectives_block
        + summary_block
        + assessment_block
    )

    return ring2