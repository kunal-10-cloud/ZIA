"""
Ring 2 — Memory Retriever
===========================
Source: Architecture doc §10 Ring 2 item 4 (episodic memories)
        Layer 3 (Memory & Continuity) §4 — technical architecture
        Architecture doc ring2_context/memory_retriever.py

Selects top 3-5 relevant memories for the current turn.

Phase A: keyword matching (simple, no external deps)
Phase B: pgvector cosine similarity on Memory.embedding_text column

The iceberg rule (Ring 1 memory_rules.py) applies:
  - PERSONAL category memories: only return if door_open=True
  - BEHAVIORAL category memories: never return (drive behavior silently)
  - All other categories: return by relevance
"""

import uuid
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.memory import Memory, MemoryCategory


async def get_relevant_memories(
    candidate_id: uuid.UUID,
    current_turn_text: str,
    db: AsyncSession,
    top_k: int = 5,
    door_open_topics: Optional[list[str]] = None,
) -> str:
    """
    Retrieves the most relevant memories for the current turn.
    Returns a formatted string block for Ring 2 injection.

    Args:
        candidate_id      : which candidate
        current_turn_text : what the candidate just said (used for relevance)
        db                : async db session
        top_k             : max memories to return (architecture: 3-5)
        door_open_topics  : list of personal topics the candidate opened this
                            session (e.g. ["family", "relocation"])
                            Used to decide whether PERSONAL memories surface.

    Phase A implementation: keyword matching
    Phase B: replace with pgvector similarity search
    """
    door_open_topics = door_open_topics or []

    # Fetch all non-deleted memories for this candidate
    # excluding BEHAVIORAL (never surface) and PERSONAL (door rule)
    allowed_categories = [
        MemoryCategory.CAREER_FACT,
        MemoryCategory.TRAJECTORY,
        MemoryCategory.CONVERSATION,
    ]

    # Add PERSONAL only if the candidate opened that door this session
    if door_open_topics:
        allowed_categories.append(MemoryCategory.PERSONAL)

    result = await db.execute(
        select(Memory).where(
            and_(
                Memory.candidate_id == candidate_id,
                Memory.is_deleted == False,
                Memory.category.in_(allowed_categories),
            )
        ).order_by(Memory.created_at.desc()).limit(50)
    )
    memories = result.scalars().all()

    if not memories:
        return ""

    # Phase A: keyword scoring
    # Score each memory by how many words from the current turn appear in it
    turn_words = set(current_turn_text.lower().split())

    def keyword_score(memory: Memory) -> float:
        content_words = set(memory.content.lower().split())
        overlap = len(turn_words & content_words)
        # Boost CAREER_FACT — always highly relevant
        boost = 2.0 if memory.category == MemoryCategory.CAREER_FACT else 1.0
        # Penalize over-surfaced memories
        recency_penalty = min(memory.surfaced_count * 0.1, 0.5)
        return (overlap * boost) - recency_penalty

    scored = sorted(memories, key=keyword_score, reverse=True)
    top_memories = scored[:top_k]

    if not top_memories:
        return ""

    lines = ["--- EPISODIC MEMORIES (relevant to this turn) ---"]
    for mem in top_memories:
        category_label = mem.category.replace("_", " ").title()
        lines.append(f"[{category_label}] {mem.content}")

    lines.append("")
    return "\n".join(lines)