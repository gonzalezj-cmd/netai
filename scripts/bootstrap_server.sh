#!/bin/bash
set -euo pipefail

cd ~/netai
python3 -m venv venv || true
source venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn psycopg2-binary routeros-api

sudo tee /etc/systemd/system/netai-api.service >/dev/null <<'EOF'
[Unit]
Description=NetAI API
After=network.target
[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/netai
Environment=PATH=/home/ubuntu/netai/venv/bin
ExecStart=/home/ubuntu/netai/venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/netai-collector.service >/dev/null <<'EOF'
[Unit]
Description=NetAI Collector
After=network.target
[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/netai
Environment=PATH=/home/ubuntu/netai/venv/bin
ExecStart=/home/ubuntu/netai/venv/bin/python /home/ubuntu/netai/collector_loop.py
Restart=always
RestartSec=3
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now netai-api netai-collector
