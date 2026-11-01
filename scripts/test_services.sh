#!/usr/bin/env bash
# Start or stop the throwaway Qdrant + Postgres stack used by the integration
# tests. Uses `docker compose -p ams-test` when the compose plugin is present,
# otherwise plain `docker run` with the same images. Either way the containers
# are named/projected `ams-test` and listen on non-default host ports, so they
# never collide with a benchmark stack on 6333/5432.
#
#   scripts/test_services.sh up|down
set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT="${TEST_PROJECT:-ams-test}"
QDRANT_PORT="${TEST_QDRANT_PORT:-16333}"
POSTGRES_PORT="${TEST_POSTGRES_PORT:-15432}"
PG_USER="${POSTGRES_USER:-benchmark}"
PG_PASSWORD="${POSTGRES_PASSWORD:-benchmark}"
PG_DB="${POSTGRES_DB:-memory_bench}"

QDRANT_IMAGE="$(awk '/^  qdrant:/{f=1} f&&/image:/{print $2; exit}' docker-compose.yml)"
POSTGRES_IMAGE="$(awk '/^  postgres:/{f=1} f&&/image:/{print $2; exit}' docker-compose.yml)"

have_compose() { docker compose version >/dev/null 2>&1; }

compose() {
  QDRANT_HOST_PORT="$QDRANT_PORT" POSTGRES_HOST_PORT="$POSTGRES_PORT" \
    docker compose -p "$PROJECT" "$@"
}

wait_ready() {
  for _ in $(seq 1 60); do
    if curl -fsS "http://localhost:${QDRANT_PORT}/readyz" >/dev/null 2>&1 \
      && docker exec "${PROJECT}-postgres" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "test services did not become ready" >&2
  return 1
}

up() {
  if have_compose; then
    compose up -d --wait qdrant postgres
    return
  fi
  down >/dev/null 2>&1 || true
  docker run -d --name "${PROJECT}-qdrant" --label "ams-test=1" \
    -p "${QDRANT_PORT}:6333" "$QDRANT_IMAGE" >/dev/null
  docker run -d --name "${PROJECT}-postgres" --label "ams-test=1" \
    -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB="$PG_DB" \
    -v "$PWD/scripts/init_pgvector.sql:/docker-entrypoint-initdb.d/init.sql:ro" \
    -p "${POSTGRES_PORT}:5432" "$POSTGRES_IMAGE" >/dev/null
  wait_ready
}

down() {
  if have_compose; then
    compose down -v
    return
  fi
  docker rm -f -v "${PROJECT}-qdrant" "${PROJECT}-postgres" >/dev/null 2>&1 || true
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  *) echo "usage: $0 up|down" >&2; exit 2 ;;
esac
