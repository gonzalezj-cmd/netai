#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/netai}"
BRANCH="${BRANCH:-main}"
USER_NAME="${USER_NAME:-$USER}"

cat > "$APP_DIR/deploy.sh" <<EOF
#!/bin/bash
set -e
cd $APP_DIR
git fetch origin
LOCAL=\$(git rev-parse @)
REMOTE=\$(git rev-parse origin/$BRANCH)
if [ "\$LOCAL" != "\$REMOTE" ]; then
  git reset --hard origin/$BRANCH
  source venv/bin/activate
  sudo systemctl restart netai-api netai-collector
  echo "\$(date) deploy ok \$REMOTE" >> $APP_DIR/deploy.log
fi
EOF
chmod +x "$APP_DIR/deploy.sh"

sudo tee /etc/systemd/system/netai-deploy.service >/dev/null <<EOF
[Unit]
Description=NetAI auto deploy

[Service]
Type=oneshot
User=$USER_NAME
ExecStart=$APP_DIR/deploy.sh
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

echo "✅ Auto deploy timer activo"
sudo systemctl --no-pager status netai-deploy.timer | head -n 20 || true
