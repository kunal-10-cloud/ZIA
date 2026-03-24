"""
Feedback Store
===============
Stores thumbs up/down feedback from internal testers.

Phase A: writes to a simple JSON log file that persists in the
Docker volume. No DB migration needed — feedback is append-only.

Phase B: move to a proper DB table once schema is stable.

Log location: /app/data/feedback_log.jsonl
One JSON object per line (JSONL format).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

FEEDBACK_LOG_PATH = Path("/app/data/feedback_log.jsonl")


def record_feedback(
    session_id: str,
    turn_number: int,
    message: str,
    response: str,
    active_skill: str,
    rating: str,  # "up" or "down"
    tester_email: Optional[str] = None,
    note: Optional[str] = None,
) -> bool:
    """
    Appends one feedback entry to the JSONL log.
    Returns True on success, False on failure.
    Never raises — feedback failure must not crash a conversation.
    """
    try:
        FEEDBACK_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp"   : datetime.now(timezone.utc).isoformat(),
            "session_id"  : session_id,
            "turn_number" : turn_number,
            "rating"      : rating,
            "active_skill": active_skill,
            "message"     : message[:500],    # cap length
            "response"    : response[:1000],  # cap length
            "tester_email": tester_email,
            "note"        : note,
        }

        with open(FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return True

    except Exception as e:
        logger.error(f"Feedback write failed: {e}")
        return False


def get_feedback_summary() -> dict:
    """Returns aggregate stats from the feedback log."""
    try:
        if not FEEDBACK_LOG_PATH.exists():
            return {"total": 0, "up": 0, "down": 0, "by_skill": {}}

        entries = []
        with open(FEEDBACK_LOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

        up   = sum(1 for e in entries if e.get("rating") == "up")
        down = sum(1 for e in entries if e.get("rating") == "down")

        by_skill: dict[str, dict] = {}
        for e in entries:
            skill = e.get("active_skill", "unknown")
            if skill not in by_skill:
                by_skill[skill] = {"up": 0, "down": 0}
            by_skill[skill][e.get("rating", "down")] += 1

        return {
            "total"   : len(entries),
            "up"      : up,
            "down"    : down,
            "by_skill": by_skill,
        }

    except Exception as e:
        logger.error(f"Feedback summary failed: {e}")
        return {"total": 0, "up": 0, "down": 0, "by_skill": {}}