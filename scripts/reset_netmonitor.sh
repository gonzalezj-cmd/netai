#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v psql >/dev/null 2>&1; then
  echo "psql no encontrado. Instala postgresql-client." >&2
  exit 1
fi

echo "[1/4] Reseteando DB netmonitor..."
sudo -u postgres psql -d postgres -f "$SCRIPT_DIR/reset_netmonitor.sql"

echo "[2/4] Reiniciando API..."
sudo systemctl restart netai-api || true

echo "[3/4] Esperando 2s..."
sleep 2

echo "[4/4] Estado API"
sudo systemctl status netai-api --no-pager || true

echo "Listo. Ahora carga routers desde /dashboard_static/add_router.html y ejecuta POST /collect/now"
