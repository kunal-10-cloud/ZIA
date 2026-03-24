# Zia — Copilot Agent Instructions
# READ THIS ENTIRE FILE BEFORE WRITING ANY CODE

You are building **Zia**, an AI career companion for Indian software engineers.
Built by EmployLabs. This file is your permanent context — refer to it on every request.

---

## 1. What We Are Building

Zia is NOT a chatbot. She is a voice-first, relationship-driven AI character who:
- Talks to engineers on **live phone calls** (via LiveKit) and **WhatsApp**
- **Remembers** candidates across months of conversations
- **Personalizes** her tone and energy to each individual person
- Has a deep, consistent character (warm + authoritative, like a trusted senior woman)
- Has 10 career coaching "skills" she can activate mid-conversation

The core technical challenge: giving Zia her full personality (50,000 words of character docs)
without breaking latency (<2s on voice) or exploding costs.

The solution: **The Ring Architecture** — 4 concentric layers assembled at runtime.

---

## 2. The Ring Architecture — Never Violate This

```
Ring 0 — Identity Kernel     (~2,500 tokens) — STATIC, never changes
Ring 1 — Behavioral OS       (~2,000 tokens) — STATIC, never changes
Ring 2 — Candidate Context   (~2,500 tokens) — DYNAMIC per candidate
Ring 3 — Skill Execution     (~1,500 tokens) — DYNAMIC per active skill
Total prompt target: ≤ 10,700 tokens
```

### Ring 0 — WHO Zia is
- Lives in: `backend/ring0_identity/kernel.py`
- Contains: identity essence, worldview ("play the long game"), voice profile, Priyanka energy
- Rule: **ONE file, ONE constant `RING0_IDENTITY_PROMPT`**
- NEVER put timestamps, candidate data, or anything dynamic here
- NEVER split across multiple files

### Ring 1 — HOW she always behaves
- Lives in: `backend/ring1_behavior/`
- Contains: boundary rules, memory iceberg model, relationship stage rules, Voss protocol,
  nudge policy, mixing board rules
- Rule: **Static files — loaded as constants**
- Files: `boundaries.py`, `memory_rules.py`, `relationship_stages.py`,
  `voss_protocol.py`, `nudge_policy.py`, `mixing_board_rules.py`
- Each file exports a single string constant: `RING1_[NAME]_PROMPT`

### Ring 2 — WHO she's talking to (this candidate)
- Lives in: `backend/ring2_context/`
- Contains: candidate profile, mixing board directive, relationship stage, episodic memories,
  language calibration, conversation objectives
- Rule: **Always assembled fresh from DB per call**
- Key function: `context_assembler.assemble_ring2(candidate_id, conversation_id) -> str`
- Never hardcode candidate data — always fetched from database

### Ring 3 — WHAT she's doing right now
- Lives in: `backend/ring3_skills/`
- Contains: one folder per skill, each with exactly 3 files:
  - `prompt_fragment.py` — 300-500 token instruction constant
  - `tools.py` — tool/function definitions the LLM can call
  - `templates.py` — example conversation flows (reference only)
- Rule: **Only 1 skill loaded per LLM call**
- NEVER load all skills simultaneously

### The Orchestrator — runs on every turn
- Lives in: `backend/orchestrator/`
- Files: `prompt_assembler.py`, `skill_router.py`, `conversation_engine.py`,
  `priority_resolver.py`, `compaction.py`, `tool_manager.py`
- Rule: **Lower ring always beats higher ring when conflicts occur**
  - Ring 1 boundary says no nudge → overrides Ring 3 skill wanting to nudge
  - Ring 1 door rule says don't surface memory → overrides Ring 2 retriever

---

## 3. KV-Cache Rules — Critical for Performance

Ring 0 + Ring 1 are **static** so they get KV-cached by Claude on every call.
This means Claude doesn't re-process these 4,500 tokens on each turn — massive latency/cost saving.

**Rules you MUST follow to preserve KV-cache:**
- NEVER put any dynamic value (timestamp, candidate name, date, turn number)
  inside Ring 0 or Ring 1 prompt strings
- NEVER change Ring 0 or Ring 1 between turns of the same conversation
- Tool definitions must be **masked/unmasked** — never added or removed mid-conversation
  (use `tool_manager.get_tools_for_skill(skill_name)` which masks unused tools)
- If you find yourself wanting to put something dynamic in Ring 0/1 — it belongs in Ring 2

---

## 4. Priority Resolution — When Rules Conflict

```python
# Priority order (lower number = higher priority = wins)
1. Ring 0 — identity (highest)
2. Ring 1 — behavioral rules
3. Ring 2 — candidate context
4. Ring 3 — active skill (lowest)

# Examples:
# Ring 3 career_guide wants to mention assessment
# Ring 1 nudge_policy.can_nudge() == False
# → Ring 1 wins. No nudge. Do not override.

# Ring 2 has a memory of candidate's divorce
# Ring 1 door_rule says candidate hasn't opened this topic
# → Ring 1 wins. Do not surface the memory.
```

The priority resolver lives in `backend/orchestrator/priority_resolver.py`.
**Always call priority_resolver before final prompt assembly.**

---

## 5. The Skill Router — How Zia Switches Modes

`backend/orchestrator/skill_router.py` decides which Ring 3 skill is active.

```
Phase 1: Hard rules (~0ms)     — deterministic keyword triggers
Phase 2: Intent match (~5ms)   — keyword scanning with confidence score
Phase 3: Sticky rule (~0ms)    — keep current skill if no clear shift
Phase 4: Haiku fallback (~300ms) — only when phases 1-3 all fail
```

**Skill trigger keywords (hard-coded, never use LLM for these):**
```python
NOTICE_PERIOD_TRIGGERS = ["resigned", "serving notice", "counter offer",
                           "counter-offer", "notice period", "last day", "buyout"]
OFFER_TRIGGERS = ["got an offer", "offer letter", "CTC breakdown", "joining bonus"]
SALARY_TRIGGERS = ["salary", "CTC", "compensation", "package", "₹", "lakhs",
                   "hike", "appraisal", "in-hand", "ctc"]
WORK_MENTOR_TRIGGERS = ["manager", "conflict", "stuck", "politics", "toxic",
                         "promotion", "team issue"]
```

**Sticky rule**: If no trigger fires AND current skill is active, **keep it**.
Never switch skills on ambiguous turns. Jarring skill transitions break the conversation.

---

## 6. Memory System — The Iceberg Model

```
STORE everything → SURFACE only what's relevant
```

**Three categories:**
1. **Surface freely** — career facts, recent decisions, open threads
2. **Door rule** — personal context (family, stress) — only surface if candidate opens the door
3. **Silent** — behavioral patterns (Hinglish level, humor preference) — never mentioned, always active

**Rules you must enforce in code:**
```python
# Door rule — if candidate didn't bring it up this turn, don't surface it
# Friend test — would a thoughtful friend say this right now? If weird → don't
# Forget rule — "please forget that" = immediate deletion, no confirmation dialog
# Never store: passwords, Aadhaar/PAN, gossip about named colleagues
```

Memory retriever lives in `backend/memory/retriever.py`.
Phase A: keyword matching. Phase B+: pgvector cosine similarity.

---

## 7. The Mixing Board — Zia's Personality Knobs

Two dimensions, each 0.0 → 1.0:
- **Priyanka (Sovereign Confidence)**: authority, competence, challenge
- **Sister (Protective Warmth)**: care, safety, emotional investment

```python
# Stored in CompanionProfile.mixing_board_state as JSON: {"priyanka": 0.6, "sister": 0.5}
# Converted to LLM instructions by mixing_board.generate_mixing_board_directive()
# Updated incrementally by async task mixing_board_updater.py after each turn

# Priority hierarchy for determining current values:
# 1. Relationship stage (interaction 1 → always start warm regardless)
# 2. Emotional state (nervous candidate → warmth wins)
# 3. Personalized equilibrium (candidate's stored mix)
# 4. Scenario (counter-offer → more authority)
# 5. Gender register (final subtle adjustment)
```

**NEVER start a first interaction with high Priyanka.** Priyanka earns its way in.
Interaction 1 default: `{"priyanka": 0.2, "sister": 0.8}`

---

## 8. Relationship Stages

```python
STAGES = {
    1: "Stranger",          # interactions 0-1: warm ONLY, no teasing, no assessment mention
    2: "Acquaintance",      # interactions 2-4: authority rises, light teasing ok
    3: "Trusted Advisor",   # interactions 5-10: full range, inside references
    4: "Inner Circle",      # interactions 10+: inside jokes, tough love
    5: "Life Companion",    # ongoing: milestone memory, alumni engagement
}
# Transitions are TRUST-BASED, not time-based
# A candidate who opens up deeply in interaction 2 can reach Stage 3 early
# Stage is stored in CompanionProfile.relationship_stage (int 1-5)
```

---

## 9. Database Models — What Gets Stored Where

All models in `backend/models/`, using SQLAlchemy + Alembic.

```python
# CompanionProfile — one row per candidate
# Fields: id, phone, name, current_role, yoe, tech_stack, company, comp_current,
#         comp_target, location, goals, mixing_board_state (JSON),
#         relationship_stage (int), assessment_status, nudge_count,
#         nudge_last_declined_at, last_interaction_at

# CompanionConversation — one row per conversation session
# Fields: id, candidate_id (FK), channel, started_at, ended_at,
#         turn_count, compacted_summary, skill_sequence (JSON), key_moments (JSON)

# BehavioralSignalLog — many rows per conversation turn
# Fields: id, candidate_id (FK), conversation_id (FK), signal_type,
#         signal_value, turn_number, created_at

# Memory — one row per stored memory
# Fields: id, candidate_id (FK), category, content (text), embedding (vector),
#         surfaced_count, last_surfaced_at, created_at
#         category options: career_fact, trajectory, conversation, personal, behavioral

# OpportunityCard — one row per matched opportunity
# Fields: id, candidate_id (FK), role_title, company_type, location,
#         ctc_range_min, ctc_range_max, match_score, shown_in_dashboard,
#         candidate_response
```

---

## 10. Async Tasks — Never Block the Conversation

After every LLM response is delivered, queue these tasks via Celery:
```python
# ALWAYS fire after every turn:
extract_behavioral_signals.delay(candidate_id, conversation_id, turn_text)

# Fire every 3rd turn only (cost control):
if turn_number % 3 == 0:
    run_cultural_profiler.delay(candidate_id, conversation_id)

# Fire after cultural profiler completes:
update_mixing_board.delay(candidate_id)

# Fire after conversation ends:
compact_conversation.delay(conversation_id)
save_episodic_memory.delay(candidate_id, conversation_id)
```

Cultural profiler uses **Claude Haiku** (not Sonnet) — it's analytical, not conversational.
**NEVER run cultural profiler in-context** (inside the main conversation prompt).
It must be a separate async LLM call.

---

## 11. Assessment Nudge Rules — Hard Rules, Never Break

```python
# From nudge_policy.can_nudge():
# Rule 1: No mention before 10 minutes elapsed in ANY conversation
# Rule 2: Maximum 1 nudge per conversation session
# Rule 3: If declined, never re-nudge in same conversation
# Rule 4: After 2 lifetime declines → 30-day cooldown
# Rule 5: ALWAYS frame as "my colleague Nyra handles assessments"
# Rule 6: NEVER tie relationship quality to assessment completion
```

---

## 12. Channel Adapters

```
Voice:     backend/channels/voice/   (LiveKit + Deepgram STT + ElevenLabs TTS)
WhatsApp:  backend/channels/whatsapp/ (Twilio)
```

**TTS is abstracted** — `tts_adapter.synthesize(text) -> audio_bytes`.
Phase A-C: ElevenLabs. Phase D+: swap to Cartesia Sonic-3.
Changing TTS provider = changing ONE file only.

**WhatsApp text formatting rules:**
- Max 5 lines per message. If longer → generate voice note instead
- Max 1 emoji per message. Never use 🔥💪🎯✨
- Data delivery format for numbers/comps: line breaks, clean layout

---

## 13. Eval System — How We Test Zia's Character

NOT standard unit tests. These test whether Zia BEHAVES correctly.

```
backend/eval/
├── ring0_tests/     — Hard fail. Any failure = deploy blocked. Run on every commit.
├── ring1_tests/     — Hard fail. Any failure = deploy blocked. Run on every commit.
├── ring2_tests/     — Soft score (1-5). Target ≥3.5. Run weekly.
├── ring3_tests/     — Soft score (1-5). Target ≥3.5. Run on skill change.
├── calibration_checks.py  — The 12 checks from Character Bible §14
└── pipeline.py     — Nightly automated run, generates quality report
```

**Hard fail examples (Ring 1):**
- Caste inference in any form → FAIL
- Assessment mention before 10 min → FAIL
- Company opinion (not fact) → FAIL
- Nyra not called "colleague Nyra" → FAIL

**Phase A gate**: `run_calibration_checks()` must pass ≥11/12 before Phase B starts.

---

## 14. Current Build Phase

**We are in: PHASE A — Architecture Core (Weeks 1-4)**

What Phase A builds:
- [ ] Ring 0 kernel prompt (`ring0_identity/kernel.py`)
- [ ] Ring 1 all behavior files (`ring1_behavior/*.py`)
- [ ] Mixing board quantification (`ring2_context/mixing_board.py`)
- [ ] Skill router (`orchestrator/skill_router.py`)
- [ ] Prompt assembler (`orchestrator/prompt_assembler.py`)
- [ ] Priority resolver (`orchestrator/priority_resolver.py`)
- [ ] Conversation engine skeleton (`orchestrator/conversation_engine.py`)
- [ ] Career Guide skill (`ring3_skills/career_guide/`)
- [ ] Salary Navigator skill (`ring3_skills/salary_navigator/`)
- [ ] Calibration checks (`eval/calibration_checks.py`)
- [ ] Salary data seed (`data/salary_benchmarks/`)

Phase A exit gate:
- Calibration checks pass ≥11/12
- Mixing board produces measurably different responses at 0.3 vs 0.8
- Assembled prompt stays ≤10,700 tokens
- End-to-end text response ≤3 seconds
- All Ring 1 hard-fail tests pass 100%

---

## 15. Tech Stack Quick Reference

```
Language:      Python 3.12
Web framework: FastAPI (async)
Database:      PostgreSQL + pgvector extension
ORM:           SQLAlchemy 2.0 (async) + Alembic migrations
Cache/Queue:   Redis + Celery
LLM:           Anthropic Claude Sonnet 4.6 (conversations)
               Anthropic Claude Haiku 4.5 (classification, profiling)
STT:           Deepgram Nova-2
TTS:           ElevenLabs (Phase A-C), Cartesia Sonic-3 (Phase D+)
Voice infra:   LiveKit Agents SDK
WhatsApp:      Twilio
Frontend:      Next.js 14 + TypeScript + Tailwind + shadcn/ui
Containerized: Docker + Docker Compose
Hosting:       Railway (dev/prod)
```

---

## 16. Coding Conventions

```python
# Naming
RING0_IDENTITY_PROMPT = "..."          # Ring 0/1 constants: SCREAMING_SNAKE_CASE
ring2_context/context_assembler.py     # Ring 2/3 files: snake_case
CareerGuideSkill                       # Classes: PascalCase
assemble_ring2(candidate_id, ...)      # Functions: snake_case with typed params

# Typing — always use type hints
def assemble_ring2(candidate_id: UUID, conversation_id: UUID) -> str: ...
def can_nudge(candidate_id: UUID, conversation_id: UUID) -> bool: ...

# Never hardcode
# BAD:  model = "claude-sonnet-4-6"
# GOOD: model = settings.CLAUDE_SONNET_MODEL

# Always use settings for config
from backend.config.settings import settings

# Async everywhere in FastAPI routes and DB calls
async def get_candidate(candidate_id: UUID, db: AsyncSession = Depends(get_db)):

# Log with context
logger.info("skill_routed", extra={
    "candidate_id": str(candidate_id),
    "skill": skill_name,
    "latency_ms": elapsed,
    "method": "keyword_match"
})
```

---

## 17. File Creation Rules

When asked to create a new file, always ask yourself:
1. Which ring does this belong to? Put it in the right folder.
2. Is it static (Ring 0/1) or dynamic (Ring 2/3)?
3. Does it respect the token budget? Ring 3 prompt fragments must be 300-500 tokens max.
4. Does it need a corresponding eval test?

When creating a new Ring 3 skill, always create ALL THREE files:
```
ring3_skills/[skill_name]/
├── prompt_fragment.py   ← 300-500 token LLM instruction constant
├── tools.py             ← Tool/function definitions
└── templates.py         ← Example conversation flows (reference only)
```

When creating a new Ring 1 behavior rule, always:
1. Add the rule to the appropriate `ring1_behavior/` file
2. Add a hard-fail eval test in `eval/ring1_tests/`
3. Add the conflict scenario to `priority_resolver.py`

---

## 18. What NOT to Do — Common Mistakes

```
❌ NEVER put dynamic data (timestamps, candidate names) in Ring 0 or Ring 1
❌ NEVER load more than 1 Ring 3 skill at the same time
❌ NEVER add or remove tools mid-conversation (only mask/unmask)
❌ NEVER run the cultural profiler inside the main conversation prompt
❌ NEVER mention assessment before 10 minutes have elapsed
❌ NEVER infer or reference caste, community, or surname patterns
❌ NEVER share opinions on specific companies (facts only)
❌ NEVER start Interaction 1 with high Priyanka authority energy
❌ NEVER use "you need to" — always "we need to" (partnership language)
❌ NEVER make Ring 2 or Ring 3 changes to fix a Ring 0 or Ring 1 problem
```

---

*This file is the source of truth for all architectural decisions.
When in doubt, refer back here before writing code.*
