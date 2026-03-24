"""
CompanionProfile — One row per candidate.
Source: Architecture doc §21 models/companion_profile.py
        V2.2 Spec §12.2 (CompanionProfile model)

This is the source of truth for everything Zia knows about a person.
Ring 2 reads mixing_board_state and relationship_stage from here on every call.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class CompanionProfile(Base):
    __tablename__ = "companion_profiles"

    # ── Identity ──────────────────────────────────────────────────────────────
    # phone is the primary lookup key — used to recognize returning candidates
    # across WhatsApp and LiveKit calls. E.164 format: "+919876543210"
    phone: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    gender: Mapped[str] = mapped_column(String(10), default="unknown")

    # ── Career facts ──────────────────────────────────────────────────────────
    current_role: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    yoe: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tech_stack: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    company_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Compensation — stored in rupees (2200000 = ₹22L) ─────────────────────
    comp_current: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    comp_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Goals ─────────────────────────────────────────────────────────────────
    goals: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Personalization — what Ring 2 reads on every LLM call ─────────────────
    # relationship_stage: 1=Stranger, 2=Acquaintance, 3=Trusted Advisor,
    #                     4=Inner Circle, 5=Life Companion
    relationship_stage: Mapped[int] = mapped_column(Integer, default=1)

    # mixing_board_state: {"priyanka": 0.2, "sister": 0.8}
    # Starts at Interaction 1 default. Updated by mixing_board_updater async task.
    mixing_board_state: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {"priyanka": 0.2, "sister": 0.8},
        nullable=False,
    )

    # ── Assessment ────────────────────────────────────────────────────────────
    assessment_status: Mapped[str] = mapped_column(
        String(20), default="not_started"
    )
    nudge_count: Mapped[int] = mapped_column(Integer, default=0)
    nudge_last_declined_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Activity ──────────────────────────────────────────────────────────────
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<CompanionProfile "
            f"phone={self.phone} "
            f"name={self.name} "
            f"stage={self.relationship_stage}>"
        )

    @property
    def mixing_board_priyanka(self) -> float:
        return self.mixing_board_state.get("priyanka", 0.2)

    @property
    def mixing_board_sister(self) -> float:
        return self.mixing_board_state.get("sister", 0.8)

    @property
    def comp_current_lakhs(self) -> Optional[float]:
        """2200000 → 22.0"""
        if self.comp_current:
            return round(self.comp_current / 100000, 1)
        return None

    @property
    def comp_target_lakhs(self) -> Optional[float]:
        if self.comp_target:
            return round(self.comp_target / 100000, 1)
        return None