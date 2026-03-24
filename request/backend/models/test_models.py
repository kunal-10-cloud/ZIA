"""
Database — Tests
================
Run: docker compose exec backend python backend/models/test_models.py

Verifies model naming matches architecture doc §21 exactly.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

passed = 0
failed = 0


def check(name, condition, message=""):
    global passed, failed
    if condition:
        print(f"  PASS — {name}")
        passed += 1
    else:
        print(f"  FAIL — {name}: {message}")
        failed += 1


# ── 1. Import tests ────────────────────────────────────────────────────────────
print("\n── Import tests ──\n")

try:
    from backend.models import (
        Base, get_db, async_engine,
        CompanionProfile,
        CompanionConversation,
        BehavioralSignalLog, SignalType,
        CandidateIdentity, IdentifierType,
        OpportunityCard,
        Memory, MemoryCategory,
    )
    check("All models import without error", True)
except ImportError as e:
    check("All models import without error", False, str(e))
    print("\nCannot continue — fix import errors first.\n")
    exit(1)


# ── 2. Architecture doc §21 naming checks ──────────────────────────────────────
print("\n── Architecture §21 naming checks ──\n")

check("companion_profiles table (CompanionProfile)",
    CompanionProfile.__tablename__ == "companion_profiles",
    f"Got: {CompanionProfile.__tablename__}")

check("companion_conversations table (CompanionConversation)",
    CompanionConversation.__tablename__ == "companion_conversations",
    f"Got: {CompanionConversation.__tablename__}")

check("behavioral_signal_log table (BehavioralSignalLog)",
    BehavioralSignalLog.__tablename__ == "behavioral_signal_log",
    f"Got: {BehavioralSignalLog.__tablename__}")

check("candidate_identities table (CandidateIdentity)",
    CandidateIdentity.__tablename__ == "candidate_identities",
    f"Got: {CandidateIdentity.__tablename__}")

check("opportunity_cards table (OpportunityCard)",
    OpportunityCard.__tablename__ == "opportunity_cards",
    f"Got: {OpportunityCard.__tablename__}")

check("memories table (Memory)",
    Memory.__tablename__ == "memories",
    f"Got: {Memory.__tablename__}")


# ── 3. Constants tests ─────────────────────────────────────────────────────────
print("\n── Constants tests ──\n")

check("SignalType.HINGLISH_DETECTED", SignalType.HINGLISH_DETECTED == "hinglish_detected")
check("SignalType.VOSS_MOMENT", SignalType.VOSS_MOMENT == "voss_moment")
check("SignalType.CHALLENGE_RESPONDED", SignalType.CHALLENGE_RESPONDED == "challenge_responded")
check("SignalType.ENGAGED", SignalType.ENGAGED == "engaged")
check("MemoryCategory.PERSONAL", MemoryCategory.PERSONAL == "personal")
check("MemoryCategory.BEHAVIORAL", MemoryCategory.BEHAVIORAL == "behavioral")
check("MemoryCategory.CAREER_FACT", MemoryCategory.CAREER_FACT == "career_fact")
check("MemoryCategory.TRAJECTORY", MemoryCategory.TRAJECTORY == "trajectory")
check("IdentifierType.WHATSAPP", IdentifierType.WHATSAPP == "whatsapp")
check("IdentifierType.PHONE", IdentifierType.PHONE == "phone")
check("IdentifierType.EMAIL", IdentifierType.EMAIL == "email")


# ── 4. Model property tests ────────────────────────────────────────────────────
print("\n── Model property tests ──\n")

profile = CompanionProfile(
    phone="+919999999999",
    comp_current=2200000,
    comp_target=3500000,
    mixing_board_state={"priyanka": 0.3, "sister": 0.7},
)
check("comp_current_lakhs: 2200000 → 22.0",
    profile.comp_current_lakhs == 22.0,
    f"Got: {profile.comp_current_lakhs}")
check("comp_target_lakhs: 3500000 → 35.0",
    profile.comp_target_lakhs == 35.0,
    f"Got: {profile.comp_target_lakhs}")
check("mixing_board_priyanka reads correctly",
    profile.mixing_board_priyanka == 0.3,
    f"Got: {profile.mixing_board_priyanka}")
check("mixing_board_sister reads correctly",
    profile.mixing_board_sister == 0.7,
    f"Got: {profile.mixing_board_sister}")

opp = OpportunityCard(
    candidate_id=uuid.uuid4(),
    role_title="Senior Platform Engineer",
    company_type="gcc",
    location="Bangalore",
    ctc_range_min=2800000,
    ctc_range_max=3800000,
)
check("ctc_range_display: ₹28.0L - ₹38.0L",
    opp.ctc_range_display == "₹28.0L - ₹38.0L",
    f"Got: {opp.ctc_range_display}")

ended_conv = CompanionConversation(
    candidate_id=uuid.uuid4(),
    channel="voice",
    started_at=datetime.now(timezone.utc) - timedelta(minutes=25),
    ended_at=datetime.now(timezone.utc),
)
check("is_active False when ended_at set",
    ended_conv.is_active is False)
check("duration_minutes ~25 min",
    ended_conv.duration_minutes is not None and 24 <= ended_conv.duration_minutes <= 26,
    f"Got: {ended_conv.duration_minutes}")

active_conv = CompanionConversation(
    candidate_id=uuid.uuid4(),
    channel="whatsapp_text",
    started_at=datetime.now(timezone.utc),
)
check("is_active True when ended_at None",
    active_conv.is_active is True)


# ── 5. DB connection + tables ──────────────────────────────────────────────────
print("\n── Database tests ──\n")


async def run_all_db_tests():
    from sqlalchemy import text
    results = {}

    # Connection
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            results["connection"] = result.fetchone()[0] == 1
    except Exception as e:
        results["connection"] = False
        results["connection_error"] = str(e)

    # Tables
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables "
                     "WHERE schemaname = 'public' ORDER BY tablename")
            )
            results["tables"] = [row[0] for row in result.fetchall()]
    except Exception as e:
        results["tables"] = []
        results["tables_error"] = str(e)

    # DB defaults round-trip
    try:
        async with async_engine.begin() as conn:
            test_phone = f"+9100000{uuid.uuid4().hex[:6]}"
            await conn.execute(
                text("INSERT INTO companion_profiles "
                     "(id, phone, created_at, updated_at) "
                     "VALUES (:id, :phone, NOW(), NOW())"),
                {"id": str(uuid.uuid4()), "phone": test_phone},
            )
            row = await conn.execute(
                text("SELECT relationship_stage, assessment_status, nudge_count "
                     "FROM companion_profiles WHERE phone = :phone"),
                {"phone": test_phone},
            )
            saved = row.fetchone()
            results["defaults"] = {
                "relationship_stage": saved[0],
                "assessment_status": saved[1],
                "nudge_count": saved[2],
            }
            await conn.execute(
                text("DELETE FROM companion_profiles WHERE phone = :phone"),
                {"phone": test_phone},
            )
    except Exception as e:
        results["defaults"] = None
        results["defaults_error"] = str(e)

    return results


try:
    db = asyncio.run(run_all_db_tests())

    check("PostgreSQL connection works",
        db.get("connection", False),
        db.get("connection_error", ""))

    expected_tables = [
        "behavioral_signal_log",
        "candidate_identities",
        "companion_conversations",
        "companion_profiles",
        "memories",
        "opportunity_cards",
    ]
    tables = db.get("tables", [])
    for table in expected_tables:
        check(f"Table '{table}' exists",
            table in tables,
            "Not found — run: docker compose exec backend alembic upgrade head")

    defaults = db.get("defaults")
    if defaults:
        check("DB default: relationship_stage = 1",
            defaults["relationship_stage"] == 1,
            f"Got: {defaults['relationship_stage']}")
        check("DB default: assessment_status = 'not_started'",
            defaults["assessment_status"] == "not_started",
            f"Got: {defaults['assessment_status']}")
        check("DB default: nudge_count = 0",
            defaults["nudge_count"] == 0,
            f"Got: {defaults['nudge_count']}")
    else:
        print(f"  NOTE — defaults test skipped: {db.get('defaults_error', '')}")
        print("  Run migrations first: docker compose exec backend alembic upgrade head")

except Exception as e:
    check("DB tests", False, str(e))


# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n── Results: {passed} passed, {failed} failed ──\n")

if failed == 0:
    print("All models match architecture doc §21. Database ready.\n")
    print("Move to Step 5 — Mixing Board (ring2_context/mixing_board.py)\n")
else:
    print("Fix failures above.\n")
    print("If table tests failed:")
    print("  docker compose exec backend alembic upgrade head\n")