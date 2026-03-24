"""
Models package — all models imported here so Alembic discovers them.

Architecture doc §21 specifies these exact files:
  companion_profile.py
  companion_conversation.py
  behavioral_signal_log.py
  candidate_identity.py
  opportunity_card.py

memory.py is an additional model (memory store from services layer).
base.py provides Base, get_db, async_engine.

If a model is not imported here, Alembic won't see its table
and won't generate a migration for it.
"""

from backend.models.base import Base, get_db, async_engine, AsyncSessionLocal
from backend.models.companion_profile import CompanionProfile
from backend.models.companion_conversation import CompanionConversation
from backend.models.behavioral_signal_log import BehavioralSignalLog, SignalType
from backend.models.candidate_identity import CandidateIdentity, IdentifierType
from backend.models.opportunity_card import OpportunityCard
from backend.models.memory import Memory, MemoryCategory
from backend.models.conversation_feedback import ConversationFeedback

__all__ = [
    "Base",
    "get_db",
    "async_engine",
    "AsyncSessionLocal",
    "CompanionProfile",
    "CompanionConversation",
    "BehavioralSignalLog",
    "SignalType",
    "CandidateIdentity",
    "IdentifierType",
    "OpportunityCard",
    "Memory",
    "MemoryCategory",
    "ConversationFeedback",
]