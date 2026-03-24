"""
ConversationFeedback — Per-message feedback from candidates.

One row per thumbs-up/down on a specific message in a conversation.
Linked to (session_id, turn_number) for precise tracking.

Used to:
  - Gauge Zia's quality on specific turns
  - Trace bottlenecks in particular skills
  - Build feedback-weighted ranking for improvements
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ConversationFeedback(Base):
    __tablename__ = "conversation_feedback"

    # ── Linkage ───────────────────────────────────────────────────────────────
    session_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # CompanionConversation.id (stored as string in Redis, UUID in DB)

    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # Composite index on (session_id, turn_number) for quick lookup

    # ── Feedback ──────────────────────────────────────────────────────────────
    rating: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "up" or "down"
    note: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # User's optional comment

    # ── Audit ─────────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now()
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationFeedback "
            f"session={self.session_id} "
            f"turn={self.turn_number} "
            f"rating={self.rating}>"
        )
