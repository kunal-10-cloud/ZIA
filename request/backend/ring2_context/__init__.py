"""
Ring 2 — Candidate Context package.
Source: Architecture doc §10, §21 ring2_context/

The orchestrator calls assemble_ring2() once per turn.
All other functions are called internally by context_assembler.

Usage:
    from backend.ring2_context.context_assembler import assemble_ring2

    ring2_block = await assemble_ring2(
        candidate_id=candidate_id,
        conversation_id=conversation_id,
        db=db,
        current_turn_text=message,
        turn_number=turn_number,
        elapsed_minutes=elapsed,
        recent_candidate_turns=recent_turns,
    )

Files → Architecture doc §10 components:
    profile_loader.py      → component 1: candidate profile summary
    mixing_board.py        → component 2: mixing board values
    relationship_stage.py  → component 3: relationship stage
    memory_retriever.py    → component 4: episodic memories
    language_calibrator.py → component 5: language calibration
    objectives_tracker.py  → component 6: conversation objectives
    context_assembler.py   → assembles all 8 components (7+8 inline)
"""

from backend.ring2_context.context_assembler import assemble_ring2
from backend.ring2_context.mixing_board import (
    generate_mixing_board_directive,
    get_stage_default,
    STAGE_DEFAULTS,
)
from backend.ring2_context.objectives_tracker import (
    ConversationObjectives,
    Objective,
    build_initial_objectives,
)

__all__ = [
    "assemble_ring2",
    "generate_mixing_board_directive",
    "get_stage_default",
    "STAGE_DEFAULTS",
    "ConversationObjectives",
    "Objective",
    "build_initial_objectives",
]