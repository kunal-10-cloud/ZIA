"""
Ring 3 Skills — Tests
======================
Run: docker compose exec backend python backend/ring3_skills/test_ring3.py

Tests:
  - Skill loader: all skills return non-empty prompt strings
  - Career Guide: key behaviors present in prompt
  - Salary Navigator: key behaviors present in prompt
  - Token budget: no single skill prompt exceeds Ring 3 budget
  - Fallback: unknown skill name falls back to career_guide
"""

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


from backend.ring3_skills import (
    load_skill_prompt, get_available_skills,
    CAREER_GUIDE, SALARY_NAVIGATOR, WORK_MENTOR,
    NOTICE_PERIOD, OFFER_EVALUATION,
)
from backend.ring3_skills.career_guide.prompt_fragment import CAREER_GUIDE_PROMPT
from backend.ring3_skills.salary_navigator.prompt_fragment import SALARY_NAVIGATOR_PROMPT
from backend.orchestrator.prompt_assembler import estimate_tokens

# ── Skill loader ───────────────────────────────────────────────────────────────
print("\n── Skill loader ──\n")

skills = get_available_skills()
check("All 5 Phase A skills registered",
    all(s in skills for s in [
        CAREER_GUIDE, SALARY_NAVIGATOR, WORK_MENTOR,
        NOTICE_PERIOD, OFFER_EVALUATION,
    ]),
    f"Got: {skills}")

for skill in [CAREER_GUIDE, SALARY_NAVIGATOR, WORK_MENTOR, NOTICE_PERIOD, OFFER_EVALUATION]:
    prompt = load_skill_prompt(skill)
    check(f"{skill} — returns non-empty string", bool(prompt and len(prompt) > 50))

# Unknown skill falls back to career_guide (not a crash)
fallback = load_skill_prompt("nonexistent_skill")
check("Unknown skill falls back to career_guide prompt",
    fallback == CAREER_GUIDE_PROMPT)

# ── Token budget checks ────────────────────────────────────────────────────────
print("\n── Token budget (Ring 3 max: 1,500 tokens) ──\n")

RING3_BUDGET = 1500

for skill in [CAREER_GUIDE, SALARY_NAVIGATOR]:
    prompt = load_skill_prompt(skill)
    tokens = estimate_tokens(prompt)
    check(f"{skill} — within 1,500 token budget ({tokens} tokens)",
        tokens <= RING3_BUDGET,
        f"Got {tokens} tokens — trim the prompt")

# ── Career Guide content checks ────────────────────────────────────────────────
print("\n── Career Guide — content checks ──\n")

cg = CAREER_GUIDE_PROMPT

check("Career Guide — has skill header",
    "[ACTIVE SKILL: Career Guide]" in cg)
check("Career Guide — width vs depth framework present",
    "width" in cg.lower() and "depth" in cg.lower())
check("Career Guide — specific rupee example present",
    "₹" in cg)
check("Career Guide — get_salary_benchmarks tool listed",
    "get_salary_benchmarks" in cg)
check("Career Guide — get_demand_signals tool listed",
    "get_demand_signals" in cg)
check("Career Guide — log_behavioral_signal tool listed",
    "log_behavioral_signal" in cg)
check("Career Guide — no 'you should' language (Ring 0 violation)",
    "you should" not in cg.lower())
check("Career Guide — no company opinions (Ring 1 violation)",
    "good company" not in cg.lower() and "bad company" not in cg.lower())
check("Career Guide — references frontier positioning",
    "frontier" in cg.lower())
check("Career Guide — play the long game worldview present",
    "long game" in cg.lower() or "compound" in cg.lower())

# ── Salary Navigator content checks ───────────────────────────────────────────
print("\n── Salary Navigator — content checks ──\n")

sn = SALARY_NAVIGATOR_PROMPT

check("Salary Navigator — has skill header",
    "[ACTIVE SKILL: Salary Navigator]" in sn)
check("Salary Navigator — CTC decode logic present",
    "decode" in sn.lower() or "ctc" in sn.lower())
check("Salary Navigator — specific rupee ranges present",
    "₹" in sn)
check("Salary Navigator — get_salary_benchmarks tool listed",
    "get_salary_benchmarks" in sn)
check("Salary Navigator — decode_ctc_structure tool listed",
    "decode_ctc_structure" in sn)
check("Salary Navigator — city-wise differentiation present",
    "bangalore" in sn.lower() or "hyderabad" in sn.lower())
check("Salary Navigator — negotiation framework present",
    "negotiat" in sn.lower())
check("Salary Navigator — no 'you should' language (Ring 0 violation)",
    "you should" not in sn.lower())
check("Salary Navigator — no company quality opinions (Ring 1 violation)",
    "good company" not in sn.lower() and "bad company" not in sn.lower())
check("Salary Navigator — variable pay distinction present",
    "variable" in sn.lower())

# ── Summary ────────────────────────────────────────────────────────────────────
print(f"\n── Results: {passed} passed, {failed} failed ──\n")

if failed == 0:
    print("A.7 + A.8 complete: Career Guide and Salary Navigator ready.")
    print("Move to A.10 — Conversation Engine.\n")
else:
    print("Fix failures above.\n")