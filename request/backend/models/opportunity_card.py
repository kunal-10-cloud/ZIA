"""
OpportunityCard — One row per matched opportunity shown to a candidate.
Source: Architecture doc §21 models/opportunity_card.py
        Architecture doc services/opportunity_router.py

Powers the candidate dashboard in Phase D.
When Zia identifies a role that matches a candidate, a card is created here
and shown in the dashboard via the opportunity_router service.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class OpportunityCard(Base):
    __tablename__ = "opportunity_cards"

    # ── Foreign key ───────────────────────────────────────────────────────────
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # ── Role details ──────────────────────────────────────────────────────────
    role_title: Mapped[str] = mapped_column(String(200), nullable=False)
    # company_type: gcc | startup | product | services
    company_type: Mapped[str] = mapped_column(String(50), nullable=False)
    company_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    location: Mapped[str] = mapped_column(String(100), nullable=False)

    # ── Compensation — stored in rupees ───────────────────────────────────────
    ctc_range_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ctc_range_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Match quality ─────────────────────────────────────────────────────────
    # match_score: 0.0-1.0 computed from YoE, tech stack, location, comp target
    match_score: Mapped[float] = mapped_column(Float, default=0.0)
    match_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Dashboard state ───────────────────────────────────────────────────────
    shown_in_dashboard: Mapped[bool] = mapped_column(Boolean, default=False)
    shown_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Candidate response: "interested" | "not_interested" | "maybe" | None ──
    candidate_response: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Source: "internal" (EmployLabs pipeline) | "market" (demand signals) ──
    sourced_from: Mapped[str] = mapped_column(String(20), default="internal")

    def __repr__(self) -> str:
        return (
            f"<OpportunityCard "
            f"candidate={self.candidate_id} "
            f"role={self.role_title} "
            f"score={self.match_score:.2f}>"
        )

    @property
    def ctc_range_display(self) -> str:
        """2800000 / 3800000 → '₹28.0L - ₹38.0L'"""
        if self.ctc_range_min and self.ctc_range_max:
            min_l = round(self.ctc_range_min / 100000, 1)
            max_l = round(self.ctc_range_max / 100000, 1)
            return f"₹{min_l}L - ₹{max_l}L"
        return "Competitive"