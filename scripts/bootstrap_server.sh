#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/netai}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
USER_NAME="${USER_NAME:-$USER}"

cd "$APP_DIR"

$PYTHON_BIN -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn psycopg2-binary routeros-api

sudo tee /etc/systemd/system/netai-api.service >/dev/null <<EOF
[Unit]
Description=NetAI API
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/netai-collector.service >/dev/null <<EOF
[Unit]
Description=NetAI Collector Loop
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/collector_loop.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now netai-api netai-collector

echo "✅ Bootstrap completo"
sudo systemctl --no-pager status netai-api | head -n 15 || true
sudo systemctl --no-pager status netai-collector | head -n 15 || true
