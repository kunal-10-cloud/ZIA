"""
Ring 2 — Conversation Objectives Tracker
==========================================
Source: Architecture doc §15 — Conversation Objectives Tracker
        Architecture doc ring2_context/objectives_tracker.py

Injects a ~150-200 token objectives block into Ring 2 each turn.
Updated by the post-processing pipeline after each turn (NOT by the LLM).

This solves the Manus "todo file pattern" problem:
in long conversations the LLM loses track of goals and starts
responding reactively instead of steering toward objectives.

Objective statuses (from architecture doc §15 examples):
  [DONE]    — completed this session
  [ACTIVE]  — in progress right now
  [QUEUED]  — not yet started
  [BLOCKED] — cannot proceed (e.g. timer not elapsed)
"""

from dataclasses import dataclass, field
from typing import Literal


ObjectiveStatus = Literal["DONE", "ACTIVE", "QUEUED", "BLOCKED"]


@dataclass
class Objective:
    status: ObjectiveStatus
    description: str


@dataclass
class ConversationObjectives:
    """
    Tracks the objectives for the current conversation session.
    Stored in Redis (keyed by conversation_id) — not in Postgres.
    Lightweight, turn-by-turn state.
    """
    conversation_id: str
    objectives: list[Objective] = field(default_factory=list)

    def format_for_prompt(self) -> str:
        """
        Formats objectives as a Ring 2 prompt block.
        ~150-200 tokens as per architecture doc §15.
        """
        if not self.objectives:
            return ""

        lines = ["CONVERSATION OBJECTIVES (auto-updated):"]
        for obj in self.objectives:
            lines.append(f"- [{obj.status}] {obj.description}")
        lines.append("")
        return "\n".join(lines)

    def mark_done(self, description_contains: str) -> None:
        for obj in self.objectives:
            if description_contains.lower() in obj.description.lower():
                obj.status = "DONE"

    def mark_active(self, description_contains: str) -> None:
        for obj in self.objectives:
            if description_contains.lower() in obj.description.lower():
                obj.status = "ACTIVE"

    def add(self, status: ObjectiveStatus, description: str) -> None:
        self.objectives.append(Objective(status=status, description=description))


def build_initial_objectives(
    relationship_stage: int,
    elapsed_minutes: float,
    nudge_count: int,
    has_previous_conversations: bool,
) -> ConversationObjectives:
    """
    Builds the initial objectives list for a new conversation turn.
    Based on: relationship stage + nudge timing + session history.
    Source: Architecture doc §15 examples.
    """
    import uuid
    objectives = ConversationObjectives(conversation_id=str(uuid.uuid4()))

    if relationship_stage == 1:
        objectives.add("ACTIVE", "Open warm — candidate must feel comfortable before anything else")
        objectives.add("QUEUED", "Deliver one surprising market insight (the hook)")
        objectives.add("BLOCKED", f"Assessment mention (timer: {max(0, 10 - elapsed_minutes):.0f} min remaining)" if elapsed_minutes < 10 else "Assessment mention (timer elapsed — ok to nudge if natural)")
        objectives.add("QUEUED", "End with tangible value delivered (WhatsApp summary)")
    else:
        if has_previous_conversations:
            objectives.add("ACTIVE", "Catch up on open threads from last conversation")
        objectives.add("ACTIVE", "Understand candidate's current situation honestly")
        objectives.add("QUEUED", "Deliver relevant market insight for their specific profile")
        if nudge_count == 0 and elapsed_minutes >= 10:
            objectives.add("QUEUED", "Assessment nudge if natural moment arises")
        elif nudge_count > 0:
            objectives.add("DONE", "Assessment nudge already delivered this session")

    return objectives