.PHONY: run build up down clean

# Primary entry point: bring up infra and run the benchmark
run: up
	docker compose run --rm benchmark python run_benchmark.py

# Build the benchmark image
build:
	docker compose build

# Start background services (Qdrant + Postgres)
up:
	docker compose up -d qdrant postgres
	@echo "Waiting for services to be healthy..."
	@sleep 5

# Stop all services
down:
	docker compose down

# Full teardown including volumes
clean:
	docker compose down -v

# Run locally (services must already be up, .env must be populated)
run-local:
	python run_benchmark.py

# Run with a smaller dataset for quick testing
run-quick:
	python run_benchmark.py --runs 2 --turns 10 --backends buffer summary
