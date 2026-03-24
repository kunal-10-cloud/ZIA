"""
Orchestrator — Tool Manager
=============================
Source: Architecture doc §14 — Hierarchical Tool Space

Three-level tool hierarchy to maximise KV-cache reuse.
Level 1 — Core tools:       always registered, never change
Level 2 — Skill tools:      registered at session start, MASKED not removed
Level 3 — Computation:      LLM writes code inline, no tool definition needed

Key rule (from Manus): MASK tools when inactive, never REMOVE them.
Removal changes the context prefix → invalidates KV-cache.
Masking only changes which tools the model can SELECT.
"""

from typing import Optional
from backend.orchestrator.skill_router import (
    CAREER_GUIDE, SALARY_NAVIGATOR, WORK_MENTOR,
    NOTICE_PERIOD, OFFER_EVALUATION,
)

# ── Level 1 — Core tools (always registered, architecture doc §14) ────────────
# These 8 tools never change within or between conversations.
# Maximum KV-cache reuse.

CORE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "log_behavioral_signal",
            "description": "Record a behavioral observation about the candidate this turn (e.g. hinglish_detected, voss_moment, challenge_responded).",
            "parameters": {
                "type": "object",
                "properties": {
                    "signal_type": {"type": "string", "description": "Signal type from SignalType constants"},
                    "signal_value": {"type": "number", "description": "Signal strength 0.0-1.0"},
                    "notes": {"type": "string", "description": "Optional observation note"},
                },
                "required": ["signal_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_followup",
            "description": "Schedule the next conversation or follow-up message with the candidate.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_from_now": {"type": "integer", "description": "Days until follow-up"},
                    "reason": {"type": "string", "description": "Why this follow-up is scheduled"},
                    "channel": {"type": "string", "enum": ["whatsapp_text", "whatsapp_voice_note", "voice_call"], "description": "Channel to use"},
                },
                "required": ["days_from_now", "reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "route_to_dashboard",
            "description": "Send the candidate a link to their EmployLabs dashboard (opportunity cards, assessment results, career profile).",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {"type": "string", "enum": ["opportunities", "assessment", "profile"], "description": "Which dashboard section to open"},
                },
                "required": ["section"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handoff_to_nyra",
            "description": "Schedule the candidate for Nyra's technical and behavioural assessment. Use only after Ring 1 nudge policy approves.",
            "parameters": {
                "type": "object",
                "properties": {
                    "preferred_time": {"type": "string", "description": "Candidate's preferred time (optional)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_candidate_profile",
            "description": "Retrieve the candidate's current profile data (role, YoE, comp, tech stack, goals).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_market_data",
            "description": "Query EmployLabs market intelligence for salary benchmarks, demand signals, or company data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to look up (e.g. 'GCC backend engineer Bangalore 6 YoE salary')"},
                    "data_type": {"type": "string", "enum": ["salary", "demand", "company", "roles"], "description": "Type of market data needed"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Send a WhatsApp text or voice note to the candidate (summary, data, follow-up).",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message content to send"},
                    "type": {"type": "string", "enum": ["text", "voice_note"], "description": "Message type"},
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_conversation_state",
            "description": "Update session state (e.g. mark objective done, record a decision, save an open thread).",
            "parameters": {
                "type": "object",
                "properties": {
                    "update_type": {"type": "string", "enum": ["objective_done", "decision_recorded", "open_thread", "commitment_made"], "description": "Type of update"},
                    "content": {"type": "string", "description": "What to record"},
                },
                "required": ["update_type", "content"],
            },
        },
    },
]

# ── Level 2 — Skill-specific tools (architecture doc §14) ─────────────────────
# Registered ONCE at session start. Masked when skill is not active.
# Never added or removed mid-conversation.

SKILL_TOOLS = {
    CAREER_GUIDE: [
        {
            "type": "function",
            "function": {
                "name": "get_salary_benchmarks",
                "description": "Get salary benchmarks for a specific profile (role, YoE, location, company type).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "yoe": {"type": "number"},
                        "location": {"type": "string"},
                        "company_type": {"type": "string", "enum": ["services", "product", "gcc", "startup"]},
                    },
                    "required": ["role", "yoe"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_demand_signals",
                "description": "Get current market demand signals for a tech profile or skill set.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "tech_stack": {"type": "string", "description": "Comma-separated tech skills"},
                        "location": {"type": "string"},
                    },
                    "required": ["tech_stack"],
                },
            },
        },
    ],
    NOTICE_PERIOD: [
        {
            "type": "function",
            "function": {
                "name": "calculate_buyout",
                "description": "Calculate notice period buyout cost given current salary and notice period length.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "monthly_ctc": {"type": "number", "description": "Monthly CTC in rupees"},
                        "notice_days": {"type": "integer", "description": "Notice period in days"},
                        "days_served": {"type": "integer", "description": "Days already served"},
                    },
                    "required": ["monthly_ctc", "notice_days"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_notice_templates",
                "description": "Get resignation letter or notice period negotiation templates.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_type": {"type": "string", "enum": ["resignation_letter", "negotiation_email", "counter_offer_response"]},
                    },
                    "required": ["template_type"],
                },
            },
        },
    ],
    OFFER_EVALUATION: [
        {
            "type": "function",
            "function": {
                "name": "decode_ctc_structure",
                "description": "Break down a CTC structure into fixed, variable, benefits, and in-hand components.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "total_ctc": {"type": "number", "description": "Total CTC in rupees"},
                        "fixed_component": {"type": "number"},
                        "variable_component": {"type": "number"},
                        "joining_bonus": {"type": "number"},
                    },
                    "required": ["total_ctc"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "compare_offers",
                "description": "Compare two job offers across CTC, role scope, company type, and growth trajectory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "offer_a": {"type": "object", "description": "First offer details"},
                        "offer_b": {"type": "object", "description": "Second offer details"},
                    },
                    "required": ["offer_a", "offer_b"],
                },
            },
        },
    ],
    SALARY_NAVIGATOR: [
        {
            "type": "function",
            "function": {
                "name": "get_salary_benchmarks",
                "description": "Get salary benchmarks for a specific profile.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string"},
                        "yoe": {"type": "number"},
                        "location": {"type": "string"},
                        "company_type": {"type": "string"},
                    },
                    "required": ["role", "yoe"],
                },
            },
        },
    ],
    WORK_MENTOR: [],  # Work Mentor uses core tools only (search_market_data covers its needs)
}


def get_tools_for_session(active_skill: str) -> list[dict]:
    """
    Returns the full tool list for an LLM call.

    Implements the masking strategy:
    - Core tools: always included (Level 1)
    - Skill tools: only the ACTIVE skill's tools are included (masking)
    - Other skills' tools: excluded this call (masked, not removed)

    This is called once per turn with the current active skill.
    The tool list changes only when the skill changes — giving good
    KV-cache hit rate within a continuous skill segment.

    Args:
        active_skill: currently active skill name

    Returns:
        Combined list of core tools + active skill's tools
    """
    skill_tools = SKILL_TOOLS.get(active_skill, [])
    return CORE_TOOLS + skill_tools


def get_all_tools_for_session() -> list[dict]:
    """
    Returns ALL tools (core + all skill tools).
    Used only for session initialization — never per-turn.
    This is what gets registered at session start.
    """
    all_skill_tools = []
    seen_names = set()
    for tools in SKILL_TOOLS.values():
        for tool in tools:
            name = tool["function"]["name"]
            if name not in seen_names:
                all_skill_tools.append(tool)
                seen_names.add(name)
    return CORE_TOOLS + all_skill_tools