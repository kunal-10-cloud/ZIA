"""
CandidateIdentity — Identity resolution across channels.
Source: Architecture doc §21 models/candidate_identity.py
        Architecture doc services/identity_resolver.py

One candidate can contact Zia across multiple channels:
  - WhatsApp number: +919876543210
  - LiveKit session from a different number
  - Web dashboard login with email

This table links all those identifiers to one CompanionProfile.
The identity_resolver.py service reads this table to answer:
"Is this new contact the same person as an existing candidate?"

Used by: Phase C (LiveKit voice calls) and Phase D (dashboard login).
"""

import uuid
from typing import Optional

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class IdentifierType:
    """All valid identifier types."""
    WHATSAPP = "whatsapp"     # +919876543210
    PHONE    = "phone"        # raw phone number from LiveKit
    EMAIL    = "email"        # dashboard login
    LIVEKIT  = "livekit"      # LiveKit participant identity


class CandidateIdentity(Base):
    __tablename__ = "candidate_identities"

    # ── Foreign key ───────────────────────────────────────────────────────────
    # Links to CompanionProfile — many identities can link to one profile
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # ── Identifier ────────────────────────────────────────────────────────────
    # identifier_type: one of IdentifierType constants above
    identifier_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    # identifier_value: the actual value (phone number, email, etc.)
    identifier_value: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )

    # ── Status ────────────────────────────────────────────────────────────────
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return (
            f"<CandidateIdentity "
            f"candidate={self.candidate_id} "
            f"type={self.identifier_type} "
            f"value={self.identifier_value}>"
        )