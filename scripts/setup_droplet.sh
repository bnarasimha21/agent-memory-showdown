#!/usr/bin/env bash
set -euo pipefail

# Provision a DigitalOcean Droplet (Ubuntu 24.04) with Docker, Qdrant, and PostgreSQL+pgvector.
# Run this script on a fresh Droplet via: bash setup_droplet.sh

echo "==> Updating system packages"
apt-get update && apt-get upgrade -y

echo "==> Installing prerequisites"
apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    python3.11 \
    python3.11-venv \
    python3-pip \
    libpq-dev \
    gcc

echo "==> Installing Docker"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker
systemctl start docker

echo "==> Pulling Qdrant image"
docker pull qdrant/qdrant:v1.20.0

echo "==> Starting Qdrant container"
docker run -d \
    --name qdrant \
    --restart unless-stopped \
    -p 6333:6333 \
    -p 6334:6334 \
    -v qdrant_data:/qdrant/storage \
    qdrant/qdrant:v1.20.0

echo "==> Installing PostgreSQL 16 with pgvector"
apt-get install -y postgresql-common
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
apt-get install -y postgresql-16 postgresql-16-pgvector

echo "==> Configuring PostgreSQL"
PG_USER="${POSTGRES_USER:-benchmark}"
PG_PASS="${POSTGRES_PASSWORD:-benchmark}"
PG_DB="${POSTGRES_DB:-memory_bench}"

sudo -u postgres psql <<SQL
CREATE USER ${PG_USER} WITH PASSWORD '${PG_PASS}';
CREATE DATABASE ${PG_DB} OWNER ${PG_USER};
\c ${PG_DB}
CREATE EXTENSION IF NOT EXISTS vector;
SQL

echo "==> Allowing password auth for local connections"
PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)
sed -i 's/local\s\+all\s\+all\s\+peer/local all all md5/' "$PG_HBA"
echo "host all all 0.0.0.0/0 md5" >> "$PG_HBA"

PG_CONF=$(find /etc/postgresql -name postgresql.conf | head -1)
echo "listen_addresses = '*'" >> "$PG_CONF"

systemctl restart postgresql

echo "==> Initializing pgvector schema"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/init_pgvector.sql" ]; then
    PGPASSWORD="${PG_PASS}" psql -h localhost -U "${PG_USER}" -d "${PG_DB}" -f "$SCRIPT_DIR/init_pgvector.sql"
fi

echo "==> Verifying services"
docker ps --filter name=qdrant --format "Qdrant: {{.Status}}"
sudo -u postgres pg_isready && echo "PostgreSQL: ready"

echo ""
echo "=== Setup complete ==="
echo "Qdrant:     http://localhost:6333"
echo "PostgreSQL: localhost:5432  db=${PG_DB}  user=${PG_USER}"
echo ""
echo "Next steps:"
echo "  1. Clone the repo:  git clone <repo-url> && cd agent-memory-showdown"
echo "  2. Create .env:     cp .env.example .env  (set DO_API_KEY)"
echo "  3. Install deps:    pip install -r requirements.txt"
echo "  4. Run benchmark:   python run_benchmark.py"
