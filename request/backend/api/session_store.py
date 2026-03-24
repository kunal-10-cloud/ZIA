"""
Session Store — Redis-backed session persistence
==================================================
Replaces the in-memory _sessions dict in main.py.

Stores SessionState as JSON in Redis with a 24-hour TTL.
Sessions survive server restarts and deploys.

Key format : session:{session_id}
TTL        : 24 hours (configurable)
Serializer : custom — handles UUID, Turn dataclass, float timestamps

Phase A: stores all SessionState fields except objectives (always None).
Phase B: extend _serialize / _deserialize when objectives gets real data.
"""

import json
import uuid
import logging
from typing import Optional

import redis.asyncio as aioredis

from backend.orchestrator.conversation_engine import SessionState, create_session
from backend.orchestrator.compaction import Turn

logger = logging.getLogger(__name__)

# TTL for sessions — 24 hours
SESSION_TTL_SECONDS = 86400
KEY_PREFIX = "session:"


# ── Serialization ──────────────────────────────────────────────────────────────

def _serialize(session: SessionState) -> str:
    """Converts SessionState to a JSON string for Redis storage."""
    data = {
        "candidate_id"             : str(session.candidate_id),
        "conversation_id"          : str(session.conversation_id),
        "turn_number"              : session.turn_number,
        "session_start_time"       : session.session_start_time,
        "current_skill"            : session.current_skill,
        "is_first_conversation"    : session.is_first_conversation,
        "assessment_just_completed": session.assessment_just_completed,
        "nudge_sent_this_session"  : session.nudge_sent_this_session,
        "relationship_stage"       : session.relationship_stage,
        "compacted_summary"        : session.compacted_summary,
        "all_turns"                : [
            {
                "role"        : t.role,
                "content"     : t.content,
                "turn_number" : t.turn_number,
            }
            for t in session.all_turns
        ],
    }
    return json.dumps(data, ensure_ascii=False)


def _deserialize(raw: str) -> SessionState:
    """Reconstructs a SessionState from a JSON string retrieved from Redis."""
    data = json.loads(raw)

    session = create_session(
        candidate_id=uuid.UUID(data["candidate_id"]),
        conversation_id=uuid.UUID(data["conversation_id"]),
        relationship_stage=data["relationship_stage"],
        is_first_conversation=data["is_first_conversation"],
        assessment_just_completed=data["assessment_just_completed"],
    )

    # Restore mutable fields that create_session doesn't set
    session.turn_number            = data["turn_number"]
    session.session_start_time     = data["session_start_time"]
    session.current_skill          = data["current_skill"]
    session.nudge_sent_this_session= data["nudge_sent_this_session"]
    session.compacted_summary      = data["compacted_summary"]
    session.all_turns              = [
        Turn(
            role=t["role"],
            content=t["content"],
            turn_number=t["turn_number"],
        )
        for t in data["all_turns"]
    ]

    return session


# ── SessionStore ───────────────────────────────────────────────────────────────

class SessionStore:
    """
    Redis-backed session store.
    One instance shared across the FastAPI app (created at startup).

    Usage:
        store = SessionStore(redis_url)
        await store.connect()

        session = await store.get(session_id)
        await store.save(session_id, session)
        await store.delete(session_id)
        await store.list_all()
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Creates the Redis connection. Called at FastAPI startup."""
        self._client = aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        # Verify connection
        await self._client.ping()
        logger.info(f"SessionStore connected to Redis: {self.redis_url}")

    async def disconnect(self) -> None:
        """Closes the Redis connection. Called at FastAPI shutdown."""
        if self._client:
            await self._client.aclose()
            logger.info("SessionStore disconnected from Redis")

    def _key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}{session_id}"

    async def get(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieves a session by ID.
        Returns None if session doesn't exist or has expired.
        """
        try:
            raw = await self._client.get(self._key(session_id))
            if raw is None:
                return None
            return _deserialize(raw)
        except Exception as e:
            logger.error(f"SessionStore.get failed for {session_id}: {e}")
            return None

    async def save(self, session_id: str, session: SessionState) -> None:
        """
        Saves or updates a session.
        Resets the TTL on every save — active conversations stay alive.
        """
        try:
            raw = _serialize(session)
            await self._client.setex(
                self._key(session_id),
                SESSION_TTL_SECONDS,
                raw,
            )
        except Exception as e:
            logger.error(f"SessionStore.save failed for {session_id}: {e}")

    async def delete(self, session_id: str) -> bool:
        """Deletes a session. Returns True if it existed."""
        try:
            result = await self._client.delete(self._key(session_id))
            return result > 0
        except Exception as e:
            logger.error(f"SessionStore.delete failed for {session_id}: {e}")
            return False

    async def delete_all(self) -> int:
        """Deletes all sessions. Returns count deleted. Dev only."""
        try:
            keys = await self._client.keys(f"{KEY_PREFIX}*")
            if not keys:
                return 0
            return await self._client.delete(*keys)
        except Exception as e:
            logger.error(f"SessionStore.delete_all failed: {e}")
            return 0

    async def list_all(self) -> list[dict]:
        """
        Returns metadata for all active sessions.
        Used by the /chat/sessions dev endpoint.
        """
        try:
            keys = await self._client.keys(f"{KEY_PREFIX}*")
            sessions = []
            for key in keys:
                raw = await self._client.get(key)
                if raw:
                    try:
                        s = _deserialize(raw)
                        ttl = await self._client.ttl(key)
                        sessions.append({
                            "session_id"       : key.replace(KEY_PREFIX, ""),
                            "turn_number"      : s.turn_number,
                            "current_skill"    : s.current_skill,
                            "elapsed_minutes"  : round(s.elapsed_minutes, 1),
                            "relationship_stage": s.relationship_stage,
                            "ttl_seconds"      : ttl,
                        })
                    except Exception:
                        pass
            return sessions
        except Exception as e:
            logger.error(f"SessionStore.list_all failed: {e}")
            return []