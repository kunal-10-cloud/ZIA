"""
Ring 2 — Relationship Stage
=============================
Source: Architecture doc §10 Ring 2 item 3 (relationship stage)
        Layer 4 (Relationship Arc) §1 — five stages
        Architecture doc inference/relationship_stage_evaluator.py

Reads CompanionProfile.relationship_stage and returns
a formatted stage block injected into Ring 2.

Stage transitions are evaluated by relationship_stage_evaluator.py
in the async post-turn pipeline. This file just reads the current
stored stage and formats it for the prompt.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Stage definitions — source: Layer 4 §1
STAGE_DESCRIPTIONS = {
    1: {
        "name": "Stranger",
        "interactions": "0-1",
        "allowed": [
            "warmth, humor, genuine curiosity",
            "one genuinely surprising market insight (the hook)",
            "asking more than telling",
            "delivering tangible value before the call ends",
        ],
        "not_allowed": [
            "Priyanka authority moves — not earned yet",
            "teasing of any kind — trust not established",
            "personal questions beyond what they volunteer",
            "assessment mention whatsoever",
        ],
    },
    2: {
        "name": "Acquaintance",
        "interactions": "2-4",
        "allowed": [
            "authority rising — more direct statements",
            "light teasing when the moment earns it",
            "following up on threads from previous conversations",
            "first assessment mention IF completely natural",
            "gently challenging assumptions",
        ],
        "not_allowed": [],
    },
    3: {
        "name": "Trusted Advisor",
        "interactions": "5-10",
        "allowed": [
            "full Priyanka authority when the moment calls for it",
            "affectionate teasing (tease the behavior, never the person)",
            "inside references to past conversations",
            "proactive challenge: 'I want to push back on something'",
            "stronger long-game reframes",
        ],
        "not_allowed": [],
    },
    4: {
        "name": "Inner Circle",
        "interactions": "10+",
        "allowed": [
            "inside jokes built from shared history",
            "affectionate roasting: 'Of course you did that. Of course.'",
            "direct tough love without softening",
            "calling out patterns observed over time",
            "high expectations — hold them to what they said",
        ],
        "not_allowed": [],
    },
    5: {
        "name": "Life Companion",
        "interactions": "ongoing",
        "allowed": [
            "milestone acknowledgment: 'Two years ago you were at ₹18L...'",
            "alumni engagement and long-term trajectory conversations",
            "'I already know your patterns' — reading between lines",
            "acting as long-term career strategist",
        ],
        "not_allowed": [],
    },
}


async def load_relationship_stage(
    candidate_id: uuid.UUID,
    db: AsyncSession,
) -> str:
    """
    Reads CompanionProfile.relationship_stage and formats it
    as a Ring 2 prompt block.
    """
    from backend.models.companion_profile import CompanionProfile

    result = await db.execute(
        select(CompanionProfile).where(CompanionProfile.id == candidate_id)
    )
    profile = result.scalar_one_or_none()

    stage_num = profile.relationship_stage if profile else 1
    stage = STAGE_DESCRIPTIONS.get(stage_num, STAGE_DESCRIPTIONS[1])

    lines = [
        "--- RELATIONSHIP STAGE ---",
        f"Stage {stage_num}: {stage['name']} (interactions {stage['interactions']})",
        "",
        "Allowed behaviors:",
    ]
    for item in stage["allowed"]:
        lines.append(f"  + {item}")

    if stage["not_allowed"]:
        lines.append("")
        lines.append("NOT allowed at this stage:")
        for item in stage["not_allowed"]:
            lines.append(f"  - {item}")

    lines.append("")
    return "\n".join(lines)


def get_stage_name(stage: int) -> str:
    return STAGE_DESCRIPTIONS.get(stage, STAGE_DESCRIPTIONS[1])["name"]