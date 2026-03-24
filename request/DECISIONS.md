# Zia — Architectural Decision Log
# Every major decision is recorded here with WHY it was made.
# Agent: if you're about to suggest changing something in this file, STOP.
# These decisions are finalized. Do not revisit them.

---

## D1 — Ring Model over flat prompt
**Decision:** 4-ring layered architecture instead of one large system prompt.
**Why:** 50K tokens of personality docs → context rot, signal dilution, latency, cost.
The ring model produces ~10,500 token prompts — compact, fast, precise.
**What would change this:** Infinite context with zero quality degradation + near-zero cost. Not true in 2026.

---

## D2 — Ring 0+1 are static (never dynamic)
**Decision:** Ring 0 and Ring 1 prompt strings are Python constants loaded from files. They never change between turns or between candidates.
**Why:** KV-cache. Claude caches the processed result of the system prompt prefix. If Ring 0+1 are always identical, ~4,500 tokens are cached on every single turn — saving ~1-1.5 seconds of prefill latency and significant cost.
**What would change this:** Provider-level partial KV-cache invalidation support. Not available in 2026.

---

## D3 — Context engineering over fine-tuning
**Decision:** Prompt-based ring architecture, not fine-tuned weights.
**Why:** (1) Ship improvements in hours not weeks. (2) Model-agnostic — when Claude 4.7 drops, zero re-training. (3) A/B testable. (4) A Ring 0 personality tweak deploys in minutes.
**What would change this:** Stable product + 10K+ conversation training data + dedicated ML team. Maybe 2028.

---

## D4 — Single LLM call per turn
**Decision:** One Claude Sonnet call per conversation turn. Persona + boundaries + context + skill all enter Claude together in one prompt.
**Why:** Voice-first product, <2 second latency target. Multi-agent or chain-of-thought adds 500ms-2s per additional call. On a live phone call, that's dead air.
**What would change this:** Real-time voice latency tolerance increasing to 5+ seconds. Not acceptable.

---

## D5 — Voss protocol is Ring 1, not Ring 3
**Decision:** Voss negotiation techniques live in Ring 1 (behavioral rules), not as a separate Ring 3 skill.
**Why:** Voss is a communication MODE, not a capability. It needs to layer on top of ANY active skill — you might be in the middle of a salary discussion (Ring 3: Salary Navigator) when a counter-offer is revealed. Voss activates without a skill switch. If it were Ring 3, it would compete for the active skill slot.
**This decision is permanent — never move Voss to Ring 3.**

---

## D6 — Cultural Profiler runs async, not in-context
**Decision:** The Cultural Profiler is a SEPARATE Claude Haiku call that runs as a background task (Celery), every 3rd turn.
**Why:** Competing objectives. The main conversation must be warm, funny, and emotionally present. A Cultural Profiler running in the same context window would extract analytical data while Zia is mid-conversation — degrading both. Separate call, separate concern.
**What would change this:** A model that genuinely handles dual objectives without quality loss.

---

## D7 — Tool masking over tool addition/removal
**Decision:** All tools are always REGISTERED with Claude. Skill-specific tools are masked/unmasked per active skill. No tools are ever added or removed mid-conversation.
**Why:** Adding/removing tool definitions mid-conversation invalidates the KV-cache for all subsequent turns. Also confuses the model when previous turns reference tools no longer defined.
**Implementation:** `tool_manager.get_tools_for_skill(skill_name)` returns the full list but with inactive-skill tools masked (empty description, disabled).

---

## D8 — Salary Navigator needs seed data in Phase A
**Decision:** Real salary data must be seeded before the Salary Navigator can be meaningfully tested. Even 50-100 real data points per city beats nothing.
**Why:** The entire Salary Navigator value proposition is specificity. "₹32-38L for your profile in Bangalore this quarter" vs "engineers typically earn ₹15-40L." Without data, the skill produces the same generic answer ChatGPT would. This is a Phase A blocker, not "fix later."
**Data format:** See `backend/data/salary_benchmarks/` — JSON files per city.

---

## D9 — PostgreSQL + pgvector (not a separate vector database)
**Decision:** Memory similarity search uses pgvector extension on the existing PostgreSQL database. No Pinecone, Weaviate, or other vector DB.
**Why:** At this scale (0-500 candidates), a separate vector database is unnecessary complexity and cost. pgvector handles millions of vectors efficiently. One database = simpler ops, simpler debugging, lower cost.
**What would change this:** Tens of thousands of candidates with millions of memory entries. That's Phase G/H territory.

---

## D10 — LiveKit over Vapi
**Decision:** LiveKit for voice infrastructure, not Vapi.
**Why:** Better real-time audio control (needed for Voss silence timing — 3-5 second tactical pauses). More mature infrastructure. Open source and self-hostable. Vapi abstracts away controls we need.

---

## D11 — Railway over AWS/GCP/Render for hosting
**Decision:** Railway for deployment (dev through early production).
**Why:** Connect GitHub repo, auto-deploys on push, has built-in Postgres and Redis, scales automatically, starts at $5/month. AWS/GCP are overkill at this stage and add weeks of DevOps complexity. Migrate to AWS when you hit Railway's limits (hundreds of thousands of requests/day).

---

## D12 — TTS adapter abstraction
**Decision:** The TTS integration is behind an adapter interface (`tts_adapter.synthesize(text) -> bytes`). Phase A-C uses ElevenLabs. Phase D+ swaps to Cartesia Sonic-3.
**Why:** ElevenLabs has limited Hinglish support. Cartesia Sonic-3 handles natural Hindi particles. We need to swap without touching any other code. The adapter pattern ensures the swap is one file change.
**File:** `backend/channels/voice/tts_adapter.py`

---

## D13 — Haiku for routing/profiling, Sonnet for conversations
**Decision:** Claude Haiku 4.5 handles: skill router fallback classification, cultural profiler background analysis. Claude Sonnet 4.6 handles: all actual conversations.
**Why:** Classification tasks don't need Sonnet quality. Haiku is ~10x cheaper. On skill routing: Haiku fires <5% of turns (most routes via keyword rules). On cultural profiling: every 3rd turn × $0.0001 = negligible cost vs the quality improvement.

---

## D14 — Assessment nudge is Ring 1, not Ring 3
**Decision:** The assessment nudge is a sub-routine governed by Ring 1 policy, callable by any Ring 3 skill. Not a standalone skill.
**Why:** Multiple skills need to invoke it (Career Guide, Salary Navigator, Super Connector). It's a 2-3 turn interjection, not a full conversation flow. Its rules (10-min timer, max 1/conversation) are behavioral rules → Ring 1.
**Implementation:** `ring1_behavior/nudge_policy.py` exports `can_nudge()` and `nudge_templates`. Any skill calls `can_nudge()` before injecting a nudge.

---

*New decisions: add here with D[N] numbering. Never remove existing entries.*
