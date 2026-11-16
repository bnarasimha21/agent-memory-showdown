.PHONY: run build up down clean run-local run-quick run-fake run-v2 need-budget publish guide venv test test-unit test-integration test-services-up test-services-down site export site-check

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

# Test stack: separate compose project (or container names, when the compose
# plugin is missing) and host ports so it never collides with a benchmark
# stack on the default ports. See scripts/test_services.sh.
TEST_PROJECT ?= ams-test
TEST_QDRANT_PORT ?= 16333
TEST_POSTGRES_PORT ?= 15432
TEST_SERVICES = TEST_PROJECT=$(TEST_PROJECT) TEST_QDRANT_PORT=$(TEST_QDRANT_PORT) TEST_POSTGRES_PORT=$(TEST_POSTGRES_PORT) scripts/test_services.sh
TEST_ENV = AMS_TEST_QDRANT_URL=http://localhost:$(TEST_QDRANT_PORT) AMS_TEST_POSTGRES_PORT=$(TEST_POSTGRES_PORT)

# Primary entry point: bring up infra and run the benchmark (paid: needs DO_API_KEY)
run: up
	docker compose run --rm benchmark python run_benchmark.py

# Build the benchmark image
build:
	docker compose build

# Start background services (Qdrant + Postgres)
up:
	docker compose up -d --wait qdrant postgres

# Stop all services
down:
	docker compose down

# Full teardown including volumes
clean:
	docker compose down -v

# Run locally (services must already be up, .env must be populated)
run-local:
	$(PYTHON) run_benchmark.py

# Quick smoke test (2 runs, 10 turns, buffer + summary only, a small fact mix)
run-quick:
	$(PYTHON) run_benchmark.py --runs 2 --turns 10 --checkpoints 5 10 --backends buffer summary \
		--facts extraction=2,update=1,abstention=1

# Free offline run with the deterministic fake LLM and embeddings (services must be up)
run-fake:
	LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake JUDGE_PROVIDER=fake $(PYTHON) run_benchmark.py --runs 2 --turns 30 \
		--checkpoints 15 30 --facts extraction=1,update=1,temporal=1,multi_hop=1,abstention=1,sensitive=1

# The run that gets published (paid: needs DO_API_KEY). 5 runs of 50 turns, all
# six backends, a k sweep, a judge from a different model family than the
# answering model, and a spend ceiling. BUDGET is required and has no default:
#     make run-v2 BUDGET=150
# If it stops (budget reached, crash, kill), continue the same bundle with
#     make run-v2 BUDGET=250 RESUME=<run_id>
V2_LLM_MODEL ?= anthropic-claude-4.5-sonnet
V2_JUDGE_MODEL ?= openai-gpt-6-sol
V2_K ?= 2 4 8
V2_LABEL ?= v2
need-budget:
	@test -n "$(BUDGET)" || { echo "run-v2 needs a spend ceiling in USD, for example: make run-v2 BUDGET=150"; exit 2; }

run-v2: need-budget up
	LLM_PROVIDER=do JUDGE_PROVIDER=do EMBEDDING_PROVIDER=local JUDGE=1 \
		LLM_MODEL=$(V2_LLM_MODEL) JUDGE_MODEL=$(V2_JUDGE_MODEL) \
		$(PYTHON) run_benchmark.py --runs 5 --turns 50 --checkpoints 15 25 35 50 --k $(V2_K) --budget $(BUDGET) \
		$(if $(RESUME),--resume $(RESUME),--label $(V2_LABEL))

# Publish a finished bundle as the headline run: make publish BUNDLE=results/runs/<run_id>
# Refuses a real run whose judge was the answering model.
publish:
	@test -n "$(BUNDLE)" || { echo "usage: make publish BUNDLE=results/runs/<run_id>"; exit 2; }
	$(PYTHON) -m src.site.publish $(BUNDLE)

# Create the local virtualenv used by the test targets
venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

# Full suite: unit tests, then integration tests against a throwaway compose stack
test: test-unit test-integration

test-unit:
	$(PYTHON) -m pytest -m "not integration"

test-services-up:
	$(TEST_SERVICES) up

test-services-down:
	$(TEST_SERVICES) down

test-integration: test-services-up
	$(TEST_ENV) AMS_REQUIRE_SERVICES=1 $(PYTHON) -m pytest -m integration; \
	status=$$?; $(TEST_SERVICES) down; exit $$status

# Results site from the bundles in results/latest.json (no network, no API key)
site:
	$(PYTHON) -m src.site.build

# Regenerate the README results block, remotion/src/data/benchmarkData.ts and docs/GUIDE.md
export:
	$(PYTHON) -m src.site.export

# docs/GUIDE.md ("Which memory, when, at what cost") from the headline bundle in results/latest.json
guide:
	$(PYTHON) -m src.site.guide

# Fail if the README block, benchmarkData.ts or docs/GUIDE.md no longer match the published bundles
site-check:
	$(PYTHON) -m src.site.export --check
