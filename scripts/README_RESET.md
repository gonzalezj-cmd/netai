# Reset limpio (sin histórico)

Este flujo borra todo y recrea la base de datos mínima para NetAI.

## 1) En host de DB
```bash
cd ~/netai
bash scripts/reset_netmonitor.sh
```

> Si `netai-api` no existe en ese host, ignora ese paso.

### Si falla `DROP DATABASE` (DB en uso)
Usa reset en sitio:
```bash
sudo -u postgres psql -d netmonitor -f scripts/reset_netmonitor_inplace.sql
```

## 2) En host de APP
Asegura que el servicio use la DB correcta (`NETAI_DB_HOST`, `NETAI_DB_NAME`, etc.) y reinicia:
```bash
sudo systemctl daemon-reload
sudo systemctl restart netai-api
```

## 3) Cargar routers
Abrir:
- `http://<HOST_APP>:8000/dashboard_static/add_router.html`

## 4) Colectar datos de inmediato
```bash
curl -X POST http://127.0.0.1:8000/collect/now
```

## 5) Validar dashboard
```bash
curl -s http://127.0.0.1:8000/ppp/summary
curl -s http://127.0.0.1:8000/dashboard/data
```
