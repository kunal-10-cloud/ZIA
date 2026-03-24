"""
BehavioralSignalLog — One row per behavioral signal detected per turn.
Source: Architecture doc §21 models/behavioral_signal_log.py
        Architecture doc inference/ section (behavioral_signal_extractor.py)

Append-only log. Never update or delete rows.
The mixing_board_updater async task reads recent rows for a candidate
and adjusts CompanionProfile.mixing_board_state incrementally (±0.05 per signal).
"""

import uuid
from typing import Optional

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class SignalType:
    """
    All valid signal types. Use these constants — never raw strings.
    Adding a new signal type: add it here, then add extraction logic
    in inference/behavioral_signal_extractor.py.
    """
    HINGLISH_DETECTED   = "hinglish_detected"
    HUMOR_RESPONDED     = "humor_responded"
    CHALLENGE_RESPONDED = "challenge_responded"
    WARMTH_RESPONDED    = "warmth_responded"
    CONFIDENCE_LOW      = "confidence_low"
    CONFIDENCE_HIGH     = "confidence_high"
    VOSS_MOMENT         = "voss_moment"
    PERSONAL_OPENED     = "personal_opened"
    DEFENSIVE           = "defensive"
    ENGAGED             = "engaged"
    DECISION_MADE       = "decision_made"
    ACTION_COMMITTED    = "action_committed"


class BehavioralSignalLog(Base):
    __tablename__ = "behavioral_signal_log"

    # ── Foreign keys ──────────────────────────────────────────────────────────
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # ── Signal data ───────────────────────────────────────────────────────────
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    signal_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    # signal_value: 1.0 = strong signal, 0.5 = moderate, 0.1 = weak
    signal_value: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<BehavioralSignalLog "
            f"candidate={self.candidate_id} "
            f"turn={self.turn_number} "
            f"signal={self.signal_type} "
            f"value={self.signal_value}>"
        )