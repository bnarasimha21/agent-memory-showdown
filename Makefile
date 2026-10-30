.PHONY: run build up down clean run-local run-quick run-fake venv test test-unit test-integration test-services-up test-services-down

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

# Quick smoke test (2 runs, 10 turns, buffer + summary only)
run-quick:
	$(PYTHON) run_benchmark.py --runs 2 --turns 10 --backends buffer summary

# Free offline run with the deterministic fake LLM and embeddings (services must be up)
run-fake:
	LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake $(PYTHON) run_benchmark.py --runs 2 --turns 20 --checkpoints 10 20

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
