#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   bash scripts/fix_noc_state.sh
#
# Objetivo:
# - Dejar main como rama única de trabajo.
# - Aplicar commits de NOC (RX/TX real, histórico/meta, ajustes/reset, refresh rápido).
# - Reiniciar servicios.
# - Verificar endpoints clave.

APP_DIR="${APP_DIR:-$HOME/netai}"
cd "$APP_DIR"

echo "==> Repo: $APP_DIR"
echo "==> 1) Actualizando refs..."
git fetch --all --prune

echo "==> 2) Limpiando estado de merge/cherry-pick si quedó a medias..."
git merge --abort >/dev/null 2>&1 || true
git cherry-pick --abort >/dev/null 2>&1 || true

echo "==> 3) Forzando main limpio desde origin/main..."
git checkout -f main
git reset --hard origin/main
git clean -fd

echo "==> 4) Aplicando commits requeridos (si faltan)..."
COMMITS=(
  "f541db4"  # RX/TX real + endpoints /ppp /interfaces + VLAN real
  "31f8bdf"  # acumulado real en /ppp/history
  "d97f43a"  # /ppp/history-meta + ajustes + reset metrics
  "cdab128"  # refresh más rápido collector/dashboard
)

for c in "${COMMITS[@]}"; do
  if git merge-base --is-ancestor "$c" HEAD 2>/dev/null; then
    echo "   - $c ya está en main, skip"
    continue
  fi

  if git cat-file -e "$c^{commit}" 2>/dev/null; then
    echo "   - cherry-pick $c"
    git cherry-pick "$c"
    continue
  fi

  # Si el hash no existe local, intentar desde rama remota conocida.
  if git cat-file -e "origin/codex/review-code-and-create-unique-branch^{commit}" 2>/dev/null; then
    RESOLVED="$(git rev-list --all | grep "^$c" || true)"
    if [[ -n "$RESOLVED" ]]; then
      echo "   - cherry-pick $RESOLVED"
      git cherry-pick "$RESOLVED"
      continue
    fi
  fi

  echo "ERROR: no encuentro commit $c en el repo local/remoto."
  exit 1
done

echo "==> 5) Compilación rápida..."
python -m py_compile api.py collectors/mikrotik.py collector_loop.py

echo "==> 6) Verificando que no haya marcadores de conflicto..."
if grep -nE '^(<<<<<<<|=======|>>>>>>>)' api.py collectors/mikrotik.py dashboard/index.html; then
  echo "ERROR: hay marcadores de conflicto."
  exit 1
fi

echo "==> 7) Push main..."
git push origin main

echo "==> 8) Reiniciando servicios..."
sudo systemctl restart netai-api netai-collector
sudo systemctl --no-pager --full status netai-api | head -n 20 || true
sudo systemctl --no-pager --full status netai-collector | head -n 20 || true

echo "==> 9) Verificación endpoints..."
curl -fsS http://127.0.0.1:8000/version >/dev/null
curl -fsS http://127.0.0.1:8000/ppp/summary >/dev/null
curl -fsS http://127.0.0.1:8000/ppp/history-meta >/dev/null
curl -fsS http://127.0.0.1:8000/ppp/top-rx >/dev/null
curl -fsS -X POST http://127.0.0.1:8000/admin/reset-metrics >/dev/null

echo
echo "✅ NOC listo."
echo "Dashboard: http://$(hostname -I | awk '{print $1}'):8000/dashboard"
echo
echo "Si querés que collector vaya más rápido:"
echo "  export COLLECTOR_INTERVAL_SEC=0.5"
