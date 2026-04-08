#!/bin/bash
set -euo pipefail

cat > ~/netai/deploy.sh <<'EOF'
#!/bin/bash
set -e
cd ~/netai
git fetch origin
git reset --hard origin/main
source venv/bin/activate
sudo systemctl restart netai-api netai-collector
echo "$(date) deploy ok $(git rev-parse --short HEAD)" >> ~/netai/deploy.log
EOF
chmod +x ~/netai/deploy.sh

sudo tee /etc/systemd/system/netai-deploy.service >/dev/null <<'EOF'
[Unit]
Description=NetAI Deploy
[Service]
Type=oneshot
User=ubuntu
ExecStart=/home/ubuntu/netai/deploy.sh
EOF

sudo tee /etc/systemd/system/netai-deploy.timer >/dev/null <<'EOF'
[Unit]
Description=Run NetAI deploy every minute
[Timer]
OnBootSec=30s
OnUnitActiveSec=60s
Unit=netai-deploy.service
[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now netai-deploy.timer
