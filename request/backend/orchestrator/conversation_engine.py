"""
Orchestrator — Conversation Engine
=====================================
Source: Architecture doc §12 — Runtime Flow (step 1)
        Build Plan §A.10 — Basic conversation engine (turn management)
        v2.2 Spec §4.2.1 — Conversation Engine

The single entry point for every candidate message.
Coordinates the full pipeline on every turn:

  candidate message
    → skill_router        (which skill is active?)
    → load_skill_prompt   (get Ring 3 prompt text)
    → detect_high_stakes  (set ConversationState flags)
    → assemble_prompt     (Ring 0+1+2+3 + history + objectives)
    → priority_resolver   (inject overrides)
    → LLM call            (generate response)
    → async post-process  (signals, compaction, stage check)
    → return response

Phase A scope (text only, no voice):
  - Full pipeline from message → response
  - Session state tracking (turns, elapsed time, skill, nudge state)
  - Compaction schedule (build_compacted_history)
  - Priority resolver integrated
  - Async post-processing stubs (wired in Phase C)
  - No LiveKit — LLM called directly via OpenAI-compatible client

Phase C will add:
  - LiveKit adapter replacing the direct LLM call
  - Real async post-processing (behavioral signal extractor,
    cultural profiler, mixing board updater)
  - TTS voice configuration

Architecture doc rule (§12, from Manus):
  ONE LLM call per turn. Never multiple serial calls in the hot path.
  Async post-processing never blocks the response to the candidate.
"""

import asyncio
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.settings import settings
from backend.orchestrator.skill_router import route as skill_route
from backend.orchestrator.prompt_assembler import assemble_prompt, build_messages_for_llm
from backend.orchestrator.priority_resolver import (
    PriorityResolver, ConversationState, detect_high_stakes,
)
from backend.orchestrator.compaction import (
    Turn, build_compacted_history, needs_compaction,
)
from backend.ring3_skills import load_skill_prompt

logger = logging.getLogger(__name__)

# ── Session State ──────────────────────────────────────────────────────────────

@dataclass
class SessionState:
    """
    Complete mutable state for one conversation session.
    Created when a conversation starts, updated after every turn.
    Passed to priority_resolver and prompt_assembler each turn.

    Fields map directly to ConversationState fields used by resolver.
    """
    candidate_id: uuid.UUID
    conversation_id: uuid.UUID

    # Turn tracking
    turn_number: int = 0
    session_start_time: float = field(default_factory=time.time)

    # Skill routing state
    current_skill: Optional[str] = None
    is_first_conversation: bool = True
    assessment_just_completed: bool = False

    # Nudge policy (Ring 1 — max 1 per session)
    nudge_sent_this_session: bool = False

    # Relationship context (from DB — passed in at session start)
    relationship_stage: int = 1  # starts at Stage 1 until loaded from DB

    # Conversation history (for compaction)
    all_turns: list[Turn] = field(default_factory=list)
    compacted_summary: str = ""  # grows as compaction runs

    # Objectives (updated by post-processor, injected into Ring 2)
    # Phase A: None — objectives_tracker wires in Phase B
    objectives: None = None

    @property
    def elapsed_minutes(self) -> float:
        return (time.time() - self.session_start_time) / 60.0

    def record_turn(self, role: str, content: str) -> None:
        """Appends a turn to the full history for compaction tracking."""
        self.all_turns.append(Turn(
            role=role,
            content=content,
            turn_number=self.turn_number,
        ))


# ── ConversationEngine ────────────────────────────────────────────────────────

class ConversationEngine:
    """
    Ring-aware conversation coordinator.
    One instance per session (created by the API layer).

    Usage:
        engine = ConversationEngine(session_state, db)
        response = await engine.process_turn(candidate_message)
    """

    def __init__(
        self,
        session: SessionState,
        db: AsyncSession,
    ):
        self.session = session
        self.db = db
        self.resolver = PriorityResolver()
        self.llm_client = AsyncOpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
        )

    async def process_turn(self, candidate_message: str) -> dict:
        """
        Full pipeline for one candidate turn.

        Args:
            candidate_message: raw text from the candidate

        Returns:
            dict with keys:
              response_text  : Zia's response string
              active_skill   : which Ring 3 skill was active
              routing_method : how the skill was selected
              token_count    : estimated tokens in assembled prompt
              overrides      : list of priority override strings applied
              blocked_nudge  : True if nudge was blocked this turn
              voss_activated : True if Voss protocol was activated
        """
        s = self.session
        s.turn_number += 1

        # ── Step 1: Record candidate turn in history ───────────────────────────
        s.record_turn("user", candidate_message)

        # ── Step 2: Route to active skill ─────────────────────────────────────
        active_skill, routing_method = await skill_route(
            message=candidate_message,
            current_skill=s.current_skill,
            turn_number=s.turn_number,
            is_first_conversation=s.is_first_conversation,
            assessment_just_completed=s.assessment_just_completed,
            conversation_summary=s.compacted_summary,
        )
        s.current_skill = active_skill

        logger.debug(
            f"Turn {s.turn_number}: skill={active_skill}, "
            f"method={routing_method}, elapsed={s.elapsed_minutes:.1f}min"
        )

        # ── Step 3: Load Ring 3 prompt ─────────────────────────────────────────
        ring3_prompt = load_skill_prompt(active_skill)

        # ── Step 4: Build conversation state for resolver ──────────────────────
        high_stakes = detect_high_stakes(candidate_message)

        conv_state = ConversationState(
            elapsed_minutes=s.elapsed_minutes,
            ring3_content=ring3_prompt,
            candidate_message=candidate_message,
            relationship_stage=s.relationship_stage,
            turn_number=s.turn_number,
            high_stakes_detected=high_stakes,
            nudge_sent_this_session=s.nudge_sent_this_session,
        )

        # ── Step 5: Priority resolver (rules engine, ~10ms) ───────────────────
        resolution = self.resolver.resolve(conv_state)

        # If nudge was blocked, that's fine — don't update nudge_sent
        # If nudge was NOT blocked AND skill contains nudge content,
        # mark it sent so it won't fire again this session
        if not resolution.blocked_nudge and _contains_nudge(ring3_prompt):
            s.nudge_sent_this_session = True

        # ── Step 6: Build compacted history ───────────────────────────────────
        history = build_compacted_history(
            turns=s.all_turns,
            existing_summary=s.compacted_summary,
        )

        # ── Step 7: Assemble full prompt (Rings 0+1+2+3 + history) ───────────
        system_prompt, token_count = await assemble_prompt(
            candidate_id=s.candidate_id,
            conversation_id=s.conversation_id,
            db=self.db,
            ring3_prompt=ring3_prompt,
            history=history,
            current_turn_text=candidate_message,
            turn_number=s.turn_number,
            elapsed_minutes=s.elapsed_minutes,
            objectives=s.objectives,
            resolution=resolution,
        )

        # ── Step 8: LLM call ──────────────────────────────────────────────────
        # Phase A: direct OpenAI-compatible call
        # Phase C: replace with LiveKit adapter
        _, messages = build_messages_for_llm(
            system_prompt=system_prompt,
            conversation_turns=_history_to_messages(s.all_turns[:-1]),  # exclude current
            current_message=candidate_message,
        )

        response_text = await self._call_llm(system_prompt, messages)

        # ── Step 9: Record Zia's response in history ──────────────────────────
        s.record_turn("assistant", response_text)

        # ── Step 10: Async post-processing (fire and forget) ──────────────────
        # Phase A: compaction check only
        # Phase C: add behavioral signal extractor, cultural profiler,
        #          mixing board updater, relationship stage check
        asyncio.create_task(
            self._post_process(candidate_message, response_text)
        )

        return {
            "response_text"  : response_text,
            "active_skill"   : active_skill,
            "routing_method" : routing_method,
            "token_count"    : token_count,
            "overrides"      : resolution.overrides,
            "blocked_nudge"  : resolution.blocked_nudge,
            "voss_activated" : resolution.voss_activated,
        }

    async def _call_llm(self, system_prompt: str, messages: list[dict]) -> str:
        """
        Direct LLM call via OpenAI-compatible client.

        Phase A: Claude Sonnet via OpenRouter
        Phase C: Replace with LiveKit adapter for voice
        """
        try:
            response = await self.llm_client.chat.completions.create(
                model=settings.CLAUDE_SONNET_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages,
                ],
                max_tokens=1000,
                extra_headers={
                    "HTTP-Referer": "https://employlabs.com",
                    "X-Title": "Zia Companion",
                },
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"LLM call failed on turn {self.session.turn_number}: {e}")
            # Never crash a live conversation — return a graceful fallback
            return (
                "Give me one second — something went sideways on my end. "
                "What were we discussing?"
            )

    async def _post_process(
        self,
        candidate_message: str,
        zia_response: str,
    ) -> None:
        """
        Async post-processing — never blocks the response to the candidate.

        Phase A: compaction check only.
        Phase C additions:
          - Behavioral signal extraction (separate Haiku call)
          - Cultural profiler (separate Haiku call)
          - Mixing board recalibration
          - Relationship stage transition check
          - Guardrail violation logging
          - Objectives tracker update
        """
        s = self.session

        # Compaction check (architecture doc §13)
        if needs_compaction(s.turn_number):
            try:
                from backend.orchestrator.compaction import compact_turns, split_history
                turns_to_compact, _ = split_history(s.all_turns)
                if turns_to_compact:
                    summary = await compact_turns(
                        turns_to_compact=turns_to_compact,
                        candidate_name=None,  # Phase B: load from profile
                    )
                    s.compacted_summary = summary
                    logger.debug(
                        f"Compaction ran at turn {s.turn_number}: "
                        f"{len(turns_to_compact)} turns compacted"
                    )
            except Exception as e:
                # Compaction failure must never surface to the candidate
                logger.error(f"Compaction failed at turn {s.turn_number}: {e}")


# ── Session factory ────────────────────────────────────────────────────────────

def create_session(
    candidate_id: uuid.UUID,
    conversation_id: uuid.UUID,
    relationship_stage: int = 1,
    is_first_conversation: bool = True,
    assessment_just_completed: bool = False,
) -> SessionState:
    """
    Creates a fresh SessionState for a new conversation.
    Called by the API layer when a session begins.

    Args:
        candidate_id             : candidate's UUID
        conversation_id          : this conversation's UUID
        relationship_stage       : loaded from DB (1-5, default 1 for new)
        is_first_conversation    : True if this is candidate's very first session
        assessment_just_completed: True if Nyra just finished assessment

    Returns:
        SessionState ready to pass to ConversationEngine
    """
    return SessionState(
        candidate_id=candidate_id,
        conversation_id=conversation_id,
        relationship_stage=relationship_stage,
        is_first_conversation=is_first_conversation,
        assessment_just_completed=assessment_just_completed,
    )


# ── Private helpers ────────────────────────────────────────────────────────────

def _contains_nudge(ring3_content: str) -> bool:
    """True if the Ring 3 prompt contains assessment nudge content."""
    lowered = ring3_content.lower()
    return "assessment" in lowered or "nyra" in lowered


def _history_to_messages(turns: list[Turn]) -> list[dict]:
    """Converts Turn objects to OpenAI-format message dicts."""
    return [{"role": t.role, "content": t.content} for t in turns]