"""
Memory — One row per stored memory about a candidate.
Source: Architecture doc inference/memory_store.py (services layer)
        Layer 3 (Memory & Continuity) §4 — technical architecture

The iceberg. Ring 2's memory_retriever queries this table to find
the 3-5 most relevant memories for each conversation turn.

Phase A: keyword matching for retrieval.
Phase B: pgvector cosine similarity on embedding column.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class MemoryCategory:
    """
    Five categories. Each has different surfacing rules (Ring 1 memory_rules.py).
    CAREER_FACT   → surface HIGH   (almost every conversation)
    TRAJECTORY    → surface MEDIUM (append-only, long-game reframes)
    CONVERSATION  → surface MEDIUM (follow-ups, connecting threads)
    PERSONAL      → DOOR RULE      (only when candidate opens the topic)
    BEHAVIORAL    → NEVER explicit (drives mixing board silently)
    """
    CAREER_FACT   = "career_fact"
    TRAJECTORY    = "trajectory"
    CONVERSATION  = "conversation"
    PERSONAL      = "personal"
    BEHAVIORAL    = "behavioral"


class Memory(Base):
    __tablename__ = "memories"

    # ── Foreign key ───────────────────────────────────────────────────────────
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # ── Memory content ────────────────────────────────────────────────────────
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    # Written from Zia's perspective:
    # "Candidate is at Infosys Pune, 6 YoE backend engineer."
    # "Mentioned father is pressuring him to stay stable."
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Vector embedding (populated in Phase B when pgvector is active) ───────
    embedding_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Surfacing tracking ────────────────────────────────────────────────────
    surfaced_count: Mapped[int] = mapped_column(Integer, default=0)
    last_surfaced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Soft delete — implements the FORGET RULE from Ring 1 ─────────────────
    # "Please forget that" → is_deleted = True
    # Memory stays in DB for audit. Never surfaced again. Never hard-deleted.
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return (
            f"<Memory "
            f"candidate={self.candidate_id} "
            f"category={self.category} "
            f"deleted={self.is_deleted} "
            f"content={self.content[:50]!r}>"
        )