from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import datetime
import subprocess
import time

from database.dashboard_repo import get_latest_ppp_live

app = FastAPI(title="NetAI NOC v2", version="3.0")
app.mount("/dashboard_static", StaticFiles(directory="dashboard"), name="dashboard")


@app.get("/health")
def health():
    data = get_latest_ppp_live()
    return {
        "status": "ok",
        "sessions": len(data),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


@app.get("/")
def home():
    return {"status": "NetAI v2 running"}


@app.get("/version")
def version():
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        commit = "unknown"
    return {"app": "NetAI NOC v2", "commit": commit, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}


@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard/index.html")


@app.get("/dashboard/data")
def dashboard_data(
    include: str | None = Query(default=None),
    routers: str | None = Query(default=None)
):
    data = get_latest_ppp_live()

    if routers:
        allowed = {x.strip() for x in routers.split(",") if x.strip()}
        data = [u for u in data if u.get("router") in allowed]

    by_router = {}
    for u in data:
        r = u.get("router", "UNKNOWN")
        by_router[r] = by_router.get(r, 0) + 1

    result = {
        "ppp_activos": len(data),
        "usuarios_por_router": by_router,
        "total_rx_bps": sum(u.get("rx", 0) for u in data),
        "total_tx_bps": sum(u.get("tx", 0) for u in data),
        "top_rx_user": max(data, key=lambda x: x.get("rx", 0), default={}).get("usuario"),
        "top_tx_user": max(data, key=lambda x: x.get("tx", 0), default={}).get("usuario"),
    }

    if not include:
        return result

    requested = [k.strip() for k in include.split(",") if k.strip()]
    return {k: result.get(k) for k in requested if k in result}


@app.get("/ppp/summary")
def ppp_summary():
    data = get_latest_ppp_live()
    by_server = {}
    for u in data:
        srv = u.get("router", "UNKNOWN")
        by_server[srv] = by_server.get(srv, 0) + 1
    return {
        "total": len(data),
        "by_server": [{"pppoe": k, "users": v} for k, v in by_server.items()]
    }


@app.get("/ppp/top-rx")
def top_rx():
    data = get_latest_ppp_live()
    top = sorted(data, key=lambda x: x.get("rx", 0), reverse=True)[:20]
    return [{"user": u.get("usuario"), "rx": u.get("rx", 0), "pppoe": u.get("router", "UNKNOWN"), "vlan": u.get("vlan", 0)} for u in top]


@app.get("/ppp/top-tx")
def top_tx():
    data = get_latest_ppp_live()
    top = sorted(data, key=lambda x: x.get("tx", 0), reverse=True)[:20]
    return [{"user": u.get("usuario"), "tx": u.get("tx", 0), "pppoe": u.get("router", "UNKNOWN"), "vlan": u.get("vlan", 0)} for u in top]


@app.get("/ppp/by-vlan")
def by_vlan():
    data = get_latest_ppp_live()
    by = {}
    for u in data:
        vlan = int(u.get("vlan", 0) or 0)
        by[vlan] = by.get(vlan, 0) + 1
    return [{"vlan": k, "users": v} for k, v in sorted(by.items(), key=lambda x: x[0])]


@app.get("/ppp/by-server")
def by_server():
    data = get_latest_ppp_live()
    by = {}
    for u in data:
        p = u.get("router", "UNKNOWN")
        by[p] = by.get(p, 0) + 1
    return [{"pppoe": k, "users": v} for k, v in by.items()]


@app.get("/ppp/history")
def history():
    data = get_latest_ppp_live()
    return [{
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "rx": sum(u.get("rx", 0) for u in data),
        "tx": sum(u.get("tx", 0) for u in data),
    }]
