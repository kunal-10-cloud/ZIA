# Zia — Makefile
# All dev commands. Run from project root.
# Usage: make <command>

.PHONY: help dev stop shell migrate-up migrate-create \
        test test-ring0 test-ring1 test-ring2 test-ring3 \
        test-router test-assembler test-mixing-board test-priority \
        test-skills test-e2e test-calibration test-all \
        eval eval-nightly lint format logs clean

# ─── Colors ───────────────────────────────────────────────────────────────────
CYAN  = \033[0;36m
GREEN = \033[0;32m
RESET = \033[0m

# ─── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "$(CYAN)Zia Development Commands$(RESET)"
	@echo ""
	@echo "$(GREEN)Environment:$(RESET)"
	@echo "  make dev              Start all services (postgres, redis, api, celery, dashboard)"
	@echo "  make stop             Stop all services"
	@echo "  make shell            Open Python shell inside backend container"
	@echo "  make logs             Tail logs for all services"
	@echo "  make logs-api         Tail API logs only"
	@echo "  make logs-celery      Tail Celery worker logs only"
	@echo ""
	@echo "$(GREEN)Database:$(RESET)"
	@echo "  make migrate-up       Apply all pending migrations"
	@echo "  make migrate-down     Rollback last migration"
	@echo "  make migrate-create name=<name>  Create new migration file"
	@echo "  make db-reset         Drop and recreate database (DESTRUCTIVE)"
	@echo "  make db-seed          Seed salary benchmark data"
	@echo ""
	@echo "$(GREEN)Testing — Unit:$(RESET)"
	@echo "  make test             Run all unit tests"
	@echo "  make test-router      Test skill router accuracy"
	@echo "  make test-assembler   Test prompt assembler token budget"
	@echo "  make test-mixing-board  Test mixing board directive generation"
	@echo "  make test-priority    Test priority resolver conflict resolution"
	@echo "  make test-db          Test database models and migrations"
	@echo "  make test-skills      Test individual skill prompt fragments"
	@echo "  make test-e2e         End-to-end conversation test (requires API key)"
	@echo ""
	@echo "$(GREEN)Testing — Character Eval:$(RESET)"
	@echo "  make eval-ring0       Ring 0 hard-fail tests (identity)"
	@echo "  make eval-ring1       Ring 1 hard-fail tests (boundaries)"
	@echo "  make eval-ring2       Ring 2 soft-score tests (personalization)"
	@echo "  make eval-ring3       Ring 3 soft-score tests (skills)"
	@echo "  make eval-calibration Run all 12 Character Bible calibration checks"
	@echo "  make eval-all         Run full eval suite"
	@echo "  make eval-nightly     Nightly pipeline — saves report to eval_reports/"
	@echo ""
	@echo "$(GREEN)Code Quality:$(RESET)"
	@echo "  make lint             Run ruff linter"
	@echo "  make format           Auto-format with black + isort"
	@echo "  make typecheck        Run mypy type checker"
	@echo ""
	@echo "$(GREEN)Utilities:$(RESET)"
	@echo "  make clean            Remove __pycache__, .pyc files, test artifacts"
	@echo "  make token-count      Count tokens in Ring 0+1 prompts"
	@echo "  make check-kv-cache   Verify Ring 0+1 are identical across candidates"

# ─── Environment ──────────────────────────────────────────────────────────────
dev:
	@echo "$(CYAN)Starting all Zia services...$(RESET)"
	docker compose up --build -d
	@echo "$(GREEN)Services started:$(RESET)"
	@echo "  API:       http://localhost:8000"
	@echo "  API docs:  http://localhost:8000/docs"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  Postgres:  localhost:5432"
	@echo "  Redis:     localhost:6379"

stop:
	docker compose down

shell:
	docker compose exec backend python

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f backend

logs-celery:
	docker compose logs -f celery_worker

# ─── Database ─────────────────────────────────────────────────────────────────
migrate-up:
	docker compose exec backend alembic upgrade head

migrate-down:
	docker compose exec backend alembic downgrade -1

migrate-create:
	@if [ -z "$(name)" ]; then echo "Usage: make migrate-create name=your_migration_name"; exit 1; fi
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

db-reset:
	@echo "$(CYAN)Resetting database...$(RESET)"
	docker compose exec backend python -c "from backend.config.settings import settings; print('DB:', settings.DATABASE_URL)"
	docker compose exec backend alembic downgrade base
	docker compose exec backend alembic upgrade head
	@echo "$(GREEN)Database reset complete$(RESET)"

db-seed:
	@echo "$(CYAN)Seeding salary benchmark data...$(RESET)"
	docker compose exec backend python -m backend.scripts.seed_salary_data
	@echo "$(GREEN)Salary data seeded$(RESET)"

# ─── Unit Tests ───────────────────────────────────────────────────────────────
test:
	docker compose exec backend pytest backend/tests/ -v

test-router:
	@echo "$(CYAN)Testing skill router accuracy...$(RESET)"
	docker compose exec backend pytest backend/tests/test_skill_router.py -v

test-assembler:
	@echo "$(CYAN)Testing prompt assembler token budget...$(RESET)"
	docker compose exec backend pytest backend/tests/test_prompt_assembler.py -v
	@echo "$(CYAN)Checking KV-cache prefix consistency...$(RESET)"
	docker compose exec backend python -m backend.tests.check_kv_cache_prefix

test-mixing-board:
	@echo "$(CYAN)Testing mixing board directive generation...$(RESET)"
	docker compose exec backend pytest backend/tests/test_mixing_board.py -v
	@echo "$(CYAN)Running A/B blind rating test...$(RESET)"
	docker compose exec backend python -m backend.tests.mixing_board_ab_test

test-priority:
	docker compose exec backend pytest backend/tests/test_priority_resolver.py -v

test-db:
	docker compose exec backend pytest backend/tests/test_models.py -v

test-skills:
	docker compose exec backend pytest backend/tests/test_skills.py -v

test-e2e:
	@echo "$(CYAN)Running end-to-end conversation test...$(RESET)"
	@echo "Requires: ANTHROPIC_API_KEY in .env"
	docker compose exec backend pytest backend/tests/test_e2e.py -v -s

# ─── Character Eval ───────────────────────────────────────────────────────────
eval-ring0:
	@echo "$(CYAN)Running Ring 0 hard-fail eval...$(RESET)"
	docker compose exec backend python -m backend.eval.pipeline --rings=0
	@echo "$(CYAN)ANY FAILURE = deploy blocked$(RESET)"

eval-ring1:
	@echo "$(CYAN)Running Ring 1 hard-fail eval...$(RESET)"
	docker compose exec backend python -m backend.eval.pipeline --rings=1
	@echo "$(CYAN)Caste, nudge timing, company opinions, Nyra framing tests$(RESET)"

eval-ring2:
	@echo "$(CYAN)Running Ring 2 soft-score eval...$(RESET)"
	docker compose exec backend python -m backend.eval.pipeline --rings=2

eval-ring3:
	@echo "$(CYAN)Running Ring 3 soft-score eval...$(RESET)"
	docker compose exec backend python -m backend.eval.pipeline --rings=3

eval-calibration:
	@echo "$(CYAN)Running 12 Character Bible calibration checks...$(RESET)"
	docker compose exec backend python -m backend.eval.calibration_checks --verbose
	@echo ""
	@echo "$(CYAN)PHASE A GATE: must pass ≥11/12$(RESET)"

eval-all:
	@echo "$(CYAN)Running full eval suite...$(RESET)"
	docker compose exec backend python -m backend.eval.pipeline --rings=0,1,2,3

eval-nightly:
	@echo "$(CYAN)Running nightly eval pipeline...$(RESET)"
	docker compose exec backend python -m backend.eval.pipeline --rings=0,1,2,3 \
		--output=eval_reports/$(shell date +%Y-%m-%d).json \
		--compare-yesterday

# ─── Code Quality ─────────────────────────────────────────────────────────────
lint:
	docker compose exec backend ruff check backend/

format:
	docker compose exec backend black backend/
	docker compose exec backend isort backend/

typecheck:
	docker compose exec backend mypy backend/ --ignore-missing-imports

# ─── Utilities ────────────────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Cleaned$(RESET)"

token-count:
	@echo "$(CYAN)Counting tokens in Ring 0 + Ring 1 prompts...$(RESET)"
	docker compose exec backend python -c "\
from backend.ring0_identity.kernel import RING0_IDENTITY_PROMPT; \
from backend.ring1_behavior.boundaries import RING1_BOUNDARIES_PROMPT; \
from backend.ring1_behavior.memory_rules import RING1_MEMORY_RULES_PROMPT; \
from backend.ring1_behavior.relationship_stages import RING1_RELATIONSHIP_STAGES_PROMPT; \
from backend.ring1_behavior.voss_protocol import RING1_VOSS_PROTOCOL_PROMPT; \
from backend.ring1_behavior.nudge_policy import RING1_NUDGE_POLICY_PROMPT; \
from backend.ring1_behavior.mixing_board_rules import RING1_MIXING_BOARD_RULES_PROMPT; \
import anthropic; \
client = anthropic.Anthropic(); \
all_text = '\n'.join([RING0_IDENTITY_PROMPT, RING1_BOUNDARIES_PROMPT, \
    RING1_MEMORY_RULES_PROMPT, RING1_RELATIONSHIP_STAGES_PROMPT, \
    RING1_VOSS_PROTOCOL_PROMPT, RING1_NUDGE_POLICY_PROMPT, \
    RING1_MIXING_BOARD_RULES_PROMPT]); \
print(f'Ring 0+1 combined tokens: ~{len(all_text.split()) * 1.3:.0f}'); \
print(f'Target: ≤4,500 tokens'); \
"

check-kv-cache:
	@echo "$(CYAN)Verifying Ring 0+1 are identical across candidates...$(RESET)"
	docker compose exec backend python -c "\
from backend.orchestrator.prompt_assembler import assemble_prompt; \
import uuid; \
p1 = assemble_prompt(uuid.uuid4(), 'career_guide', uuid.uuid4()); \
p2 = assemble_prompt(uuid.uuid4(), 'career_guide', uuid.uuid4()); \
r0_1 = p1.split('RING 2')[0]; \
r0_2 = p2.split('RING 2')[0]; \
if r0_1 == r0_2: print('PASS: Ring 0+1 prefix is identical across candidates'); \
else: print('FAIL: Ring 0+1 differ between candidates — KV-cache broken'); \
"
