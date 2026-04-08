# Deploy rápido NetAI

## 1) Bootstrap limpio (servicios + venv)
```bash
cd ~/netai
chmod +x scripts/bootstrap_server.sh
./scripts/bootstrap_server.sh
```

## 2) Activar autodeploy por timer (cada 60s)
```bash
cd ~/netai
chmod +x scripts/setup_autodeploy_timer.sh
./scripts/setup_autodeploy_timer.sh
```

## 3) Verificar
```bash
curl -s http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/dashboard/data
sudo systemctl status netai-api --no-pager
sudo systemctl status netai-collector --no-pager
sudo systemctl status netai-deploy.timer --no-pager
```

## Nota
El timer hace `git fetch/reset` contra `origin/main` y reinicia servicios cuando hay commit nuevo.
