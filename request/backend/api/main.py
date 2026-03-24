"""
Zia API — Main
================
FastAPI application entry point.

Phase A endpoints:
  GET  /health         — liveness check
  POST /chat           — send a message, get Zia's response
  POST /chat/reset     — clear session(s)
  GET  /chat/sessions  — dev endpoint, active session metadata

Session management:
  Redis-backed via SessionStore. Sessions persist across restarts.
  TTL: 24 hours. Active conversations reset TTL on every turn.

Usage:
  POST /chat
  Body: { "message": "hi I want to talk about my career" }
  Response: {
    "response": "Hey! I'm Zia...",
    "session_id": "...",
    "active_skill": "career_guide",
    ...
  }

  Continue with session_id:
  Body: { "message": "my CTC is 18L", "session_id": "..." }
"""

import uuid
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.orchestrator.conversation_engine import (
    ConversationEngine,
    create_session,
)
from backend.api.session_store import SessionStore
from backend.config.settings import settings
from backend.api.feedback_store import record_feedback, get_feedback_summary

logger = logging.getLogger(__name__)

# ── Session store (module-level, shared across requests) ───────────────────────
session_store = SessionStore(redis_url=settings.REDIS_URL)


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await session_store.connect()
    yield
    await session_store.disconnect()


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Zia API",
    version="0.1.0",
    description="Zia Companion — EmployLabs career AI",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── DB dependency ──────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session


# ── Request / Response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    active_skill: str
    routing_method: str
    token_count: int
    overrides: list[str]
    turn_number: int
    voss_activated: bool
    blocked_nudge: bool


class ResetResponse(BaseModel):
    message: str
    session_id: str


class FeedbackRequest(BaseModel):
    session_id: str
    turn_number: int
    message: str
    response: str
    active_skill: str
    rating: str          # "up" or "down"
    tester_email: Optional[str] = None
    note: Optional[str] = None


class FeedbackResponse(BaseModel):
    success: bool
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "phase": "A"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to Zia and receive her response.

    If session_id is provided and exists in Redis, continues that conversation.
    If session_id is None or expired, starts a fresh conversation.
    """
    session_id = request.session_id
    session = None

    # ── Resolve session ────────────────────────────────────────────────────────
    if session_id:
        session = await session_store.get(session_id)

    if session is None:
        session_id = str(uuid.uuid4())
        candidate_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        conversation_id = uuid.uuid4()

        session = create_session(
            candidate_id=candidate_id,
            conversation_id=conversation_id,
            relationship_stage=1,
            is_first_conversation=True,
        )
        logger.info(f"New session: {session_id}")

    # ── Run the conversation engine ────────────────────────────────────────────
    engine = ConversationEngine(session=session, db=db)

    try:
        result = await engine.process_turn(request.message)
    except Exception as e:
        logger.error(f"process_turn failed for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Zia encountered an error. Please try again.",
        )

    # ── Persist updated session to Redis ──────────────────────────────────────
    await session_store.save(session_id, session)

    return ChatResponse(
        response=result["response_text"],
        session_id=session_id,
        active_skill=result["active_skill"],
        routing_method=result["routing_method"],
        token_count=result["token_count"],
        overrides=result["overrides"],
        turn_number=session.turn_number,
        voss_activated=result["voss_activated"],
        blocked_nudge=result["blocked_nudge"],
    )


@app.post("/chat/reset", response_model=ResetResponse)
async def reset_chat(session_id: Optional[str] = None):
    """
    Clears session(s) from Redis.
    If session_id provided — clears that session.
    If not — clears all sessions (dev convenience).
    """
    if session_id:
        deleted = await session_store.delete(session_id)
        msg = f"Session {session_id} cleared." if deleted else "Session not found."
        return ResetResponse(message=msg, session_id=session_id)
    else:
        count = await session_store.delete_all()
        return ResetResponse(
            message=f"All {count} session(s) cleared.",
            session_id="",
        )


@app.get("/chat/sessions")
async def list_sessions():
    """Dev endpoint — active sessions with metadata. Remove before production."""
    sessions = await session_store.list_all()
    return {
        "active_sessions": len(sessions),
        "sessions": sessions,
    }


@app.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """
    Records thumbs up/down feedback from internal testers.
    Called by the Streamlit UI after each response.
    """
    if request.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'")

    success = record_feedback(
        session_id=request.session_id,
        turn_number=request.turn_number,
        message=request.message,
        response=request.response,
        active_skill=request.active_skill,
        rating=request.rating,
        tester_email=request.tester_email,
        note=request.note,
    )

    return FeedbackResponse(
        success=success,
        message="Feedback recorded." if success else "Feedback write failed — check logs.",
    )


@app.get("/feedback/summary")
async def feedback_summary():
    """Returns aggregate feedback stats. For internal monitoring."""
    return get_feedback_summary()