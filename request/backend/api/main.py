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
import os

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from alembic.config import Config
from alembic import command

from backend.orchestrator.conversation_engine import (
    ConversationEngine,
    create_session,
)
from backend.api.session_store import SessionStore
from backend.config.settings import settings
from backend.api.feedback_store import record_feedback, get_feedback_summary
from backend.models import CompanionProfile, CompanionConversation, ConversationFeedback
from backend.models.base import AsyncSessionLocal

logger = logging.getLogger(__name__)


# ── Auto-run migrations on startup ─────────────────────────────────────────────

def run_migrations():
    """Run Alembic migrations on app startup"""
    try:
        # Find alembic.ini by searching upward from this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_ini = None
        
        for _ in range(5):  # Search up to 5 levels
            test_path = os.path.join(current_dir, "alembic.ini")
            if os.path.exists(test_path):
                alembic_ini = test_path
                break
            current_dir = os.path.dirname(current_dir)
        
        if not alembic_ini:
            logger.warning("Could not find alembic.ini anywhere in parent directories")
            return
        
        migrations_dir = os.path.join(os.path.dirname(alembic_ini), "migrations")
        
        if not os.path.exists(migrations_dir):
            logger.warning(f"migrations directory not found at {migrations_dir}")
            return
        
        alembic_cfg = Config(alembic_ini)
        alembic_cfg.set_main_option("script_location", migrations_dir)
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        command.upgrade(alembic_cfg, "head")
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.warning(f"Migration error: {e}")


# ── Session store (module-level, shared across requests) ───────────────────────
session_store = SessionStore(redis_url=settings.REDIS_URL)


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
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
    allow_origins=[
        "http://localhost:3000",           # Local development
        "http://127.0.0.1:3000",           # Local development (alternate)
        "https://zia-frontend-nine.vercel.app",  # Production Vercel frontend
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
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
    phone: Optional[str] = None  # Phone number to identify candidate


class ChatResponse(BaseModel):
    response: str
    session_id: str
    active_skill: str
    routing_method: str
    token_count: int
    overrides: list[str]
    turn_number: int
    timestamp: str  # ISO 8601 timestamp
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


# ── Candidate Profile Models ───────────────────────────────────────────────────

class CreateOrGetProfileRequest(BaseModel):
    phone: str
    name: Optional[str] = None


class CompanionProfileResponse(BaseModel):
    id: str
    phone: str
    name: Optional[str] = None
    gender: str
    current_role: Optional[str] = None
    yoe: Optional[float] = None
    tech_stack: Optional[str] = None
    company: Optional[str] = None
    company_type: Optional[str] = None
    location: Optional[str] = None
    comp_current: Optional[int] = None
    comp_target: Optional[int] = None
    goals: Optional[str] = None
    relationship_stage: int
    mixing_board_state: dict
    assessment_status: str
    nudge_count: int


class UpdateProfileRequest(BaseModel):
    phone: str
    name: Optional[str] = None
    current_role: Optional[str] = None
    yoe: Optional[float] = None
    tech_stack: Optional[str] = None
    company: Optional[str] = None
    company_type: Optional[str] = None
    location: Optional[str] = None
    comp_current: Optional[int] = None
    comp_target: Optional[int] = None
    goals: Optional[str] = None


class MessageRecord(BaseModel):
    turn: int
    user_message: str
    zia_response: str
    active_skill: Optional[str] = None
    timestamp: str
    feedback: Optional[str] = None  # "up", "down", or None


class ConversationRecord(BaseModel):
    id: str
    candidate_id: str
    channel: str
    started_at: str
    ended_at: Optional[str] = None
    turn_count: int
    relationship_stage_at_start: int
    messages: list[MessageRecord] = []
    created_at: str


class SubmitFeedbackRequest(BaseModel):
    session_id: str
    turn_number: int
    rating: str  # "up" or "down"
    note: Optional[str] = None


class SubmitFeedbackResponse(BaseModel):
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
    is_new_conversation = False
    
    # Get candidate ID from phone number if provided
    candidate_id = uuid.UUID("00000000-0000-0000-0000-000000000001")  # default
    if request.phone:
        stmt = select(CompanionProfile).where(CompanionProfile.phone == request.phone)
        result_obj = await db.execute(stmt)
        profile = result_obj.scalars().first()
        if profile:
            candidate_id = profile.id

    # ── Resolve session ────────────────────────────────────────────────────────
    if session_id:
        session = await session_store.get(session_id)

    if session is None:
        session_id = str(uuid.uuid4())
        conversation_id = uuid.uuid4()
        is_new_conversation = True

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

    timestamp = datetime.now(timezone.utc).isoformat()

    # ── Save or update conversation in database ────────────────────────────────
    if is_new_conversation:
        conversation = CompanionConversation(
            id=session_id,
            candidate_id=candidate_id,
            channel="web",
            started_at=datetime.now(timezone.utc),
            turn_count=1,
            messages=[{
                "turn": 1,
                "user_message": request.message,
                "zia_response": result["response_text"],
                "active_skill": result["active_skill"],
                "timestamp": timestamp,
                "feedback": None,
            }],
        )
        db.add(conversation)
    else:
        # Update existing conversation
        stmt = select(CompanionConversation).where(CompanionConversation.id == session_id)
        result_obj = await db.execute(stmt)
        conversation = result_obj.scalars().first()
        
        if conversation:
            conversation.turn_count = session.turn_number
            # Append new message — MUST reassign entire list for SQLAlchemy to detect change
            existing_messages = conversation.messages if isinstance(conversation.messages, list) else []
            new_message = {
                "turn": session.turn_number,
                "user_message": request.message,
                "zia_response": result["response_text"],
                "active_skill": result["active_skill"],
                "timestamp": timestamp,
                "feedback": None,
            }
            conversation.messages = existing_messages + [new_message]

    await db.commit()

    return ChatResponse(
        response=result["response_text"],
        session_id=session_id,
        active_skill=result["active_skill"],
        routing_method=result["routing_method"],
        token_count=result["token_count"],
        overrides=result["overrides"],
        turn_number=session.turn_number,
        timestamp=timestamp,
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


# ────────────────────────────────────────────────────────────────────────────────
# ── NEW: Candidate Profile & Conversation Endpoints (Frontend Integration)
# ────────────────────────────────────────────────────────────────────────────────


@app.post("/candidate/profile/create-or-get", response_model=CompanionProfileResponse)
async def create_or_get_profile(
    request: CreateOrGetProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Find existing profile by phone, or create new one.
    VALIDATION: If phone exists, verify name matches exactly.
    Used during onboarding — identifies returning candidates.
    """
    # Try to find existing profile by phone
    stmt = select(CompanionProfile).where(CompanionProfile.phone == request.phone)
    result = await db.execute(stmt)
    profile = result.scalars().first()

    # If profile exists, validate name matches
    if profile:
        if profile.name.strip().lower() != request.name.strip().lower():
            raise HTTPException(
                status_code=400,
                detail=f"Phone number is already registered with a different name. Registered name: '{profile.name}'. Please use the correct name to login.",
            )
        logger.info(f"Found existing profile for phone: {request.phone}")
    else:
        # Create new profile
        profile = CompanionProfile(
            phone=request.phone,
            name=request.name,
            gender="unknown",
            relationship_stage=1,
            mixing_board_state={"priyanka": 0.2, "sister": 0.8},
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        logger.info(f"Created new profile for phone: {request.phone}, name: {request.name}")

    return CompanionProfileResponse(
        id=str(profile.id),
        phone=profile.phone,
        name=profile.name,
        gender=profile.gender,
        current_role=profile.current_role,
        yoe=profile.yoe,
        tech_stack=profile.tech_stack,
        company=profile.company,
        company_type=profile.company_type,
        location=profile.location,
        comp_current=profile.comp_current,
        comp_target=profile.comp_target,
        goals=profile.goals,
        relationship_stage=profile.relationship_stage,
        mixing_board_state=profile.mixing_board_state,
        assessment_status=profile.assessment_status,
        nudge_count=profile.nudge_count,
    )


@app.get("/candidate/profile/{phone}", response_model=CompanionProfileResponse)
async def get_profile(
    phone: str,
    db: AsyncSession = Depends(get_db),
):
    """Fetch profile by phone number."""
    stmt = select(CompanionProfile).where(CompanionProfile.phone == phone)
    result = await db.execute(stmt)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    return CompanionProfileResponse(
        id=str(profile.id),
        phone=profile.phone,
        name=profile.name,
        gender=profile.gender,
        current_role=profile.current_role,
        yoe=profile.yoe,
        tech_stack=profile.tech_stack,
        company=profile.company,
        company_type=profile.company_type,
        location=profile.location,
        comp_current=profile.comp_current,
        comp_target=profile.comp_target,
        goals=profile.goals,
        relationship_stage=profile.relationship_stage,
        mixing_board_state=profile.mixing_board_state,
        assessment_status=profile.assessment_status,
        nudge_count=profile.nudge_count,
    )


@app.post("/candidate/profile/update", response_model=CompanionProfileResponse)
async def update_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update candidate profile fields."""
    stmt = select(CompanionProfile).where(CompanionProfile.phone == request.phone)
    result = await db.execute(stmt)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Update only provided fields
    if request.name is not None:
        profile.name = request.name
    if request.current_role is not None:
        profile.current_role = request.current_role
    if request.yoe is not None:
        profile.yoe = request.yoe
    if request.tech_stack is not None:
        profile.tech_stack = request.tech_stack
    if request.company is not None:
        profile.company = request.company
    if request.company_type is not None:
        profile.company_type = request.company_type
    if request.location is not None:
        profile.location = request.location
    if request.comp_current is not None:
        profile.comp_current = request.comp_current
    if request.comp_target is not None:
        profile.comp_target = request.comp_target
    if request.goals is not None:
        profile.goals = request.goals

    await db.commit()
    await db.refresh(profile)

    return CompanionProfileResponse(
        id=str(profile.id),
        phone=profile.phone,
        name=profile.name,
        gender=profile.gender,
        current_role=profile.current_role,
        yoe=profile.yoe,
        tech_stack=profile.tech_stack,
        company=profile.company,
        company_type=profile.company_type,
        location=profile.location,
        comp_current=profile.comp_current,
        comp_target=profile.comp_target,
        goals=profile.goals,
        relationship_stage=profile.relationship_stage,
        mixing_board_state=profile.mixing_board_state,
        assessment_status=profile.assessment_status,
        nudge_count=profile.nudge_count,
    )


@app.get("/candidate/conversations/{phone}")
async def get_conversations(
    phone: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations for a candidate (by phone number)."""
    # First, get the profile
    stmt = select(CompanionProfile).where(CompanionProfile.phone == phone)
    result = await db.execute(stmt)
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # Get all conversations for this candidate
    stmt = (
        select(CompanionConversation)
        .where(CompanionConversation.candidate_id == profile.id)
        .order_by(CompanionConversation.started_at.desc())
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    return [
        ConversationRecord(
            id=str(c.id),
            candidate_id=str(c.candidate_id),
            channel=c.channel,
            started_at=c.started_at.isoformat(),
            ended_at=c.ended_at.isoformat() if c.ended_at else None,
            turn_count=c.turn_count,
            relationship_stage_at_start=c.relationship_stage_at_start,
            messages=[MessageRecord(**m) for m in c.messages],
            created_at=c.created_at.isoformat(),
        )
        for c in conversations
    ]


@app.get("/candidate/conversation/{session_id}/messages")
async def get_conversation_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get message history for a specific conversation session."""
    stmt = select(CompanionConversation).where(CompanionConversation.id == session_id)
    result = await db.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return [MessageRecord(**m) for m in conversation.messages]


@app.post("/candidate/feedback", response_model=SubmitFeedbackResponse)
async def submit_candidate_feedback(
    request: SubmitFeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit feedback (thumbs up/down) for a specific message in a conversation.
    New DB-backed endpoint (replaces JSONL logging).
    """
    if request.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'")

    try:
        # Record feedback in database
        feedback = ConversationFeedback(
            session_id=request.session_id,
            turn_number=request.turn_number,
            rating=request.rating,
            note=request.note,
        )
        db.add(feedback)
        await db.commit()

        # Also update the conversation's messages array to reflect feedback
        stmt = select(CompanionConversation).where(
            CompanionConversation.id == request.session_id
        )
        result = await db.execute(stmt)
        conversation = result.scalars().first()

        if conversation and conversation.messages:
            # Find and update the message with matching turn number
            # Create a new list with updated message to ensure SQLAlchemy detects the change
            updated_messages = []
            for msg in conversation.messages:
                if msg.get("turn") == request.turn_number:
                    # Create new dict with feedback added
                    updated_messages.append({**msg, "feedback": request.rating})
                else:
                    updated_messages.append(msg)
            # Reassign the entire list to trigger SQLAlchemy's change tracking
            conversation.messages = updated_messages
            # Explicitly mark the column as modified
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(conversation, "messages")
            await db.commit()
            logger.info(f"Feedback recorded for session {request.session_id}, turn {request.turn_number}: {request.rating}")

        return SubmitFeedbackResponse(
            success=True,
            message="Feedback recorded successfully.",
        )
    except Exception as e:
        logger.error(f"Failed to record feedback: {e}")
        return SubmitFeedbackResponse(
            success=False,
            message=f"Failed to record feedback: {str(e)}",
        )


# ────────────────────────────────────────────────────────────────────────────────
# ── ADMIN Endpoints — Dashboard Data ──────────────────────────────────────────
# ────────────────────────────────────────────────────────────────────────────────


class ConversationSummary(BaseModel):
    """Lightweight conversation summary for admin dashboard."""
    id: str
    candidate_phone: Optional[str] = None
    candidate_name: Optional[str] = None
    channel: str
    started_at: str
    turn_count: int
    message_preview: Optional[str] = None  # First user message


@app.get("/admin/conversations")
async def get_all_conversations(db: AsyncSession = Depends(get_db)):
    """
    Get ALL conversations across all candidates for admin dashboard.
    Returns lightweight summaries (no full message content).
    """
    # Get all conversations ordered by most recent first
    stmt = (
        select(CompanionConversation)
        .order_by(CompanionConversation.started_at.desc())
    )
    result = await db.execute(stmt)
    conversations = result.scalars().all()

    # For each conversation, fetch the candidate profile to get phone/name
    summaries = []
    for conv in conversations:
        # Get candidate profile
        stmt = select(CompanionProfile).where(CompanionProfile.id == conv.candidate_id)
        result = await db.execute(stmt)
        profile = result.scalars().first()
        
        candidate_phone = profile.phone if profile else None
        candidate_name = profile.name if profile else None
        
        # Get first user message as preview
        message_preview = None
        if conv.messages and len(conv.messages) > 0:
            message_preview = conv.messages[0].get("user_message", "")[:100]
        
        summaries.append(
            ConversationSummary(
                id=str(conv.id),
                candidate_phone=candidate_phone,
                candidate_name=candidate_name,
                channel=conv.channel,
                started_at=conv.started_at.isoformat(),
                turn_count=conv.turn_count,
                message_preview=message_preview,
            )
        )

    return summaries


@app.get("/admin/conversations/{session_id}")
async def get_admin_conversation_detail(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full conversation detail for admin dashboard.
    Includes all messages and feedback.
    """
    stmt = select(CompanionConversation).where(CompanionConversation.id == session_id)
    result = await db.execute(stmt)
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get candidate profile for name/phone
    stmt = select(CompanionProfile).where(CompanionProfile.id == conversation.candidate_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()

    return {
        "id": str(conversation.id),
        "candidate_id": str(conversation.candidate_id),
        "candidate_phone": profile.phone if profile else None,
        "candidate_name": profile.name if profile else None,
        "channel": conversation.channel,
        "started_at": conversation.started_at.isoformat(),
        "ended_at": conversation.ended_at.isoformat() if conversation.ended_at else None,
        "turn_count": conversation.turn_count,
        "relationship_stage_at_start": conversation.relationship_stage_at_start,
        "messages": conversation.messages if conversation.messages else [],
        "created_at": conversation.created_at.isoformat(),
    }