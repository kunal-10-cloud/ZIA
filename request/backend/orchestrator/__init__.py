"""
Orchestrator package.
Source: Architecture doc §12, §21 orchestrator/

Files (architecture doc §21):
    skill_router.py       — which Ring 3 skill activates
    priority_resolver.py  — Ring conflict resolution
    prompt_assembler.py   — Ring 0+1+2+3 → system prompt
    tool_manager.py       — hierarchical tool space (§14)
    compaction.py         — history compaction (§13)
    guardrails.py         — post-processing checks
    conversation_engine.py — turn management
    livekit_adapter.py    — LiveKit voice integration (Phase C)
"""