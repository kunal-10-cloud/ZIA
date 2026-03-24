"""
Ring 2 — Profile Loader
========================
Source: Architecture doc §10 Ring 2 item 1 (candidate profile summary)
        Architecture doc ring2_context/profile_loader.py

Loads CompanionProfile from DB and formats it as a
~200-token summary block injected into Ring 2.
"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def load_profile_summary(
    candidate_id: uuid.UUID,
    db: AsyncSession,
) -> str:
    """
    Fetches CompanionProfile from DB and returns a formatted
    summary string for Ring 2 injection.

    Returns a stub string if candidate is new (no profile yet).
    """
    from backend.models.companion_profile import CompanionProfile

    result = await db.execute(
        select(CompanionProfile).where(CompanionProfile.id == candidate_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return "--- CANDIDATE PROFILE ---\nNew candidate. No profile data yet.\n"

    lines = ["--- CANDIDATE PROFILE ---"]

    if profile.name:
        lines.append(f"Name: {profile.name}")
    if profile.current_role:
        lines.append(f"Role: {profile.current_role}")
    if profile.yoe is not None:
        lines.append(f"Experience: {profile.yoe} years")
    if profile.company:
        company_str = profile.company
        if profile.company_type:
            company_str += f" ({profile.company_type})"
        lines.append(f"Company: {company_str}")
    if profile.tech_stack:
        lines.append(f"Tech stack: {profile.tech_stack}")
    if profile.location:
        lines.append(f"Location: {profile.location}")
    if profile.comp_current_lakhs:
        lines.append(f"Current comp: ₹{profile.comp_current_lakhs}L")
    if profile.comp_target_lakhs:
        lines.append(f"Target comp: ₹{profile.comp_target_lakhs}L")
    if profile.goals:
        lines.append(f"Goals: {profile.goals}")
    if profile.assessment_status:
        lines.append(f"Assessment: {profile.assessment_status}")
    if profile.nudge_count > 0:
        lines.append(f"Nudges sent: {profile.nudge_count}")

    lines.append("")
    return "\n".join(lines)