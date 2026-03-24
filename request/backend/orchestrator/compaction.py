"""
Orchestrator — Compaction Layer
==================================
Source: Architecture doc §13 — Compaction Layer
        Manus AI "compaction before summarization" pattern

Manages long conversation history to keep total prompt
under the ~10,700 token budget.

Strategy (architecture doc §13):
  Turn 1-10:   Full history in context
  Turn 11-20:  Turns 1-5 summarized (~200 tokens), 6-20 kept in full
  Turn 21-30:  Turns 1-15 summarized (~400 tokens), 16-30 kept in full
  Turn 30+:    Compact every 10 turns, always keep last 5 in full

Summary preserves:
  - Key facts (career data, salary numbers, decisions)
  - Emotional arc (started nervous → warmed up → engaged)
  - Open threads (mentioned manager conflict, hasn't resolved)
  - Commitments (said they'd update resume by Friday)

Summary does NOT preserve:
  - Exact phrasing
  - Small talk
  - Repeated information

Implementation: Claude Haiku async call (~200ms, ~$0.001 per call).
Never blocks the main Sonnet response.
"""

from dataclasses import dataclass
from typing import Optional
from openai import AsyncOpenAI

from backend.config.settings import settings

# Thresholds (architecture doc §13)
FULL_HISTORY_TURNS = 10       # keep all turns below this
RECENT_TURNS_ALWAYS_FULL = 5  # always keep last N turns in full detail
COMPACT_EVERY_N_TURNS = 10    # after turn 30, compact every 10 turns


@dataclass
class Turn:
    role: str      # "user" | "assistant"
    content: str
    turn_number: int


@dataclass
class CompactedHistory:
    """
    Result of compaction — what gets injected into the prompt.
    compacted_summary : ~200-400 tokens of summarized older turns
    recent_turns      : last 5 turns in full (OpenAI message format)
    total_turns       : total turns in this conversation
    """
    compacted_summary: str
    recent_turns: list[dict]
    total_turns: int

    def format_for_prompt(self) -> str:
        """
        Formats the compacted history as a prompt block.
        Injected between Ring 2 and Ring 3 by prompt_assembler.
        """
        parts = []

        if self.compacted_summary:
            parts.append(
                f"--- CONVERSATION HISTORY (compacted) ---\n"
                f"{self.compacted_summary}\n"
            )

        if self.recent_turns:
            parts.append("--- RECENT TURNS (full) ---")
            for turn in self.recent_turns:
                role = "Candidate" if turn["role"] == "user" else "Zia"
                parts.append(f"{role}: {turn['content']}")
            parts.append("")

        return "\n".join(parts)


def needs_compaction(turn_number: int) -> bool:
    """
    Returns True if compaction should run this turn.
    Source: Architecture doc §13 compaction schedule.
    """
    if turn_number <= FULL_HISTORY_TURNS:
        return False
    if turn_number < 30:
        # Compact at turns 11, 21
        return turn_number % 10 == 1
    # After turn 30: compact every 10 turns
    return turn_number % COMPACT_EVERY_N_TURNS == 0


def split_history(
    turns: list[Turn],
) -> tuple[list[Turn], list[Turn]]:
    """
    Splits conversation history into:
      - turns_to_compact: older turns to summarize
      - recent_turns: last 5 turns to keep in full

    Source: Architecture doc §13 — always keep last 5 turns in full.
    """
    if len(turns) <= RECENT_TURNS_ALWAYS_FULL:
        return [], turns

    recent = turns[-RECENT_TURNS_ALWAYS_FULL:]
    to_compact = turns[:-RECENT_TURNS_ALWAYS_FULL]
    return to_compact, recent


async def compact_turns(
    turns_to_compact: list[Turn],
    candidate_name: Optional[str] = None,
) -> str:
    """
    Uses Claude Haiku to summarize older turns into ~200-400 tokens.
    Async — never blocks the main Sonnet response.

    Source: Architecture doc §13 implementation note.

    Args:
        turns_to_compact: older turns to summarize
        candidate_name  : for personalized summary context

    Returns:
        Summary string (~200-400 tokens)
    """
    if not turns_to_compact:
        return ""

    client = AsyncOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
    )

    # Format turns for the summary prompt
    turns_text = "\n".join([
        f"{'Candidate' if t.role == 'user' else 'Zia'}: {t.content}"
        for t in turns_to_compact
    ])

    name_context = f"The candidate's name is {candidate_name}. " if candidate_name else ""

    prompt = f"""You are summarizing a career coaching conversation between Zia (an AI career companion) and a candidate.

{name_context}Summarize the following conversation turns in 150-300 words. 

Preserve EXACTLY:
- Key facts (current role, YoE, company, salary numbers, tech stack)
- Career goals and motivations discussed
- Emotional arc (how the candidate's energy shifted)
- Open threads (topics raised but not resolved)
- Commitments made ("said they'd update resume", "agreed to research GCC roles")
- Decisions made

Do NOT preserve:
- Exact phrasing or quotes
- Small talk and pleasantries
- Repeated information

Write in third person from Zia's perspective. Be specific with numbers.

CONVERSATION:
{turns_text}

SUMMARY:"""

    try:
        response = await client.chat.completions.create(
            model=settings.CLAUDE_HAIKU_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            extra_headers={
                "HTTP-Referer": "https://employlabs.com",
                "X-Title": "Zia Compaction",
            },
        )
        return response.choices[0].message.content.strip()
    except Exception:
        # Compaction failure should never crash a live conversation
        # Fall back to a simple join of turn content
        return " | ".join([t.content[:50] for t in turns_to_compact[-5:]])


def build_compacted_history(
    turns: list[Turn],
    existing_summary: str = "",
) -> CompactedHistory:
    """
    Builds a CompactedHistory object for prompt injection.
    Uses existing_summary if available (from previous compaction runs).

    For Phase A (text testing): uses existing_summary directly.
    For Phase B+: async compact_turns() is called by conversation_engine.
    """
    _, recent = split_history(turns)

    recent_as_messages = [
        {"role": t.role, "content": t.content}
        for t in recent
    ]

    return CompactedHistory(
        compacted_summary=existing_summary,
        recent_turns=recent_as_messages,
        total_turns=len(turns),
    )