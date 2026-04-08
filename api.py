# ==================================================
# API FINAL LIMPIO - NETAI
# ==================================================

from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import threading
import time
import datetime
import subprocess
from pathlib import Path

from database.postgres import get_connection
from ai.engine import ejecutar_ia
from collectors.mikrotik import obtener_datos


# =========================
# CACHE IA
# =========================
CACHE_IA = {
    "data": None,
    "last_update": None,
    "status": "inicializando"
}


def safe_obtener_datos():
    # 1) Fuente principal: BD ppp_live + ppp_sessions + routers
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (pl.router_id, pl.username)
                pl.username,
                COALESCE(pl.rx_bps, 0) AS rx_bps,
                COALESCE(pl.tx_bps, 0) AS tx_bps,
                COALESCE(pl.pppoe_server, r.name, 'UNKNOWN') AS router_name
            FROM ppp_live pl
            LEFT JOIN routers r ON r.id = pl.router_id
            ORDER BY pl.router_id, pl.username, pl.timestamp DESC
        """)
        rows = cur.fetchall()

        if rows:
            return [
                {
                    "usuario": r[0],
                    "rx": int(r[1] or 0),
                    "tx": int(r[2] or 0),
                    "router": r[3] or "UNKNOWN",
                    "uptime": "0s"
                }
                for r in rows
            ]
    except Exception as e:
        print(f"⚠️ Error leyendo ppp_live desde BD: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    # 2) Fallback: collector mikrotik directo
    try:
        data = obtener_datos()
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"⚠️ Error leyendo datos de collectors: {e}")
        return []


# =========================
# APP
# =========================
app = FastAPI(title="NetAI NOC", version="2.0")
BASE_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = BASE_DIR / "dashboard"

app.mount("/dashboard_static", StaticFiles(directory=str(DASHBOARD_DIR)), name="dashboard")


@app.middleware("http")
async def disable_dashboard_cache(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/dashboard") or request.url.path.startswith("/dashboard_static"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# =========================
# MODELO
# =========================
class RouterCreate(BaseModel):
    name: str
    ip: str
    username: str
    password: str
    port: int = 8728
    description: str = ""


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {
        "status": "NetAI running 🚀",
        "ia_status": CACHE_IA["status"],
        "last_update": CACHE_IA["last_update"]
    }


@app.get("/version")
def version():
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True
        ).strip()
    except Exception:
        commit = "unknown"

    return {
        "app": "NetAI NOC",
        "commit": commit,
        "ts": time.strftime("%Y-%m-%d %H:%M:%S")
    }


# =========================
# DASHBOARD
# =========================
@app.get("/dashboard")
def dashboard():
    return FileResponse(str(DASHBOARD_DIR / "index.html"))


@app.get("/ai_page")
def ai_page():
    return FileResponse(str(DASHBOARD_DIR / "ai.html"))


# =========================
# IA
# =========================
@app.get("/ia/full")
def ia_full():
    return CACHE_IA["data"] or {
        "status": CACHE_IA["status"],
        "message": "IA cargando..."
    }


# =========================
# LOOP IA
# =========================
def loop_ia():

    while True:
        try:
            print("🔄 Ejecutando IA...")

            CACHE_IA["status"] = "procesando"

            data = safe_obtener_datos()

            if not data:
                CACHE_IA["status"] = "sin_datos"
                time.sleep(10)
                continue

            data = data[:300]

            resultado = ejecutar_ia(data)

            CACHE_IA["data"] = resultado
            CACHE_IA["last_update"] = time.strftime("%Y-%m-%d %H:%M:%S")
            CACHE_IA["status"] = "ok"

            print(f"✅ IA OK | usuarios: {len(data)}")

        except Exception as e:
            print("❌ ERROR IA:", e)
            CACHE_IA["status"] = str(e)

        time.sleep(20)


threading.Thread(target=loop_ia, daemon=True).start()


# =========================
# ROUTERS
# =========================
@app.get("/routers")
def get_routers():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, ip, username, port, description
        FROM routers
        ORDER BY id DESC
    """)

    data = [
        {
            "id": r[0],
            "name": r[1],
            "ip": r[2],
            "username": r[3],
            "port": r[4],
            "description": r[5]
        }
        for r in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return data


@app.put("/routers/{router_id}")
def update_router(router_id: int, router: RouterCreate):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE routers
        SET name=%s, ip=%s, username=%s, password=%s, port=%s, description=%s
        WHERE id=%s
    """, (
        router.name,
        router.ip,
        router.username,
        router.password,
        router.port,
        router.description,
        router_id
    ))

    conn.commit()
    cur.close()
    conn.close()

    return {"status": "ok"}


# =========================
# DASHBOARD DATA
# =========================
@app.get("/dashboard/data")
def dashboard_data(
    include: str | None = Query(default=None, description="Campos separados por coma"),
    routers: str | None = Query(default=None, description="Routers separados por coma")
):

    data = safe_obtener_datos()

    if routers:
        allowed = {r.strip() for r in routers.split(",") if r.strip()}
        data = [u for u in data if u.get("router", "N/A") in allowed]

    total = len(data)

    por_router = {}

    for u in data:
        r = u.get("router", "N/A")
        por_router[r] = por_router.get(r, 0) + 1

    result = {
        "ppp_activos": total,
        "usuarios_por_router": por_router,
        "total_rx_bps": sum(u.get("rx", 0) for u in data),
        "total_tx_bps": sum(u.get("tx", 0) for u in data),
        "top_rx_user": max(data, key=lambda x: x.get("rx", 0), default={}).get("usuario"),
        "top_tx_user": max(data, key=lambda x: x.get("tx", 0), default={}).get("usuario")
    }

    if not include:
        return result

    requested = [k.strip() for k in include.split(",") if k.strip()]
    return {k: result.get(k) for k in requested if k in result}


# =========================
# PPP SUMMARY
# =========================
@app.get("/ppp/summary")
def ppp_summary():

    data = safe_obtener_datos()

    total = len(data)

    by_server = {}

    for u in data:
        srv = u.get("router", "UNKNOWN")
        by_server[srv] = by_server.get(srv, 0) + 1

    return {
        "total": total,
        "by_server": [
            {"pppoe": k, "users": v}
            for k, v in by_server.items()
        ]
    }


# =========================
# TOP RX
# =========================
@app.get("/ppp/top-rx")
def top_rx():

    data = safe_obtener_datos()

    sorted_data = sorted(data, key=lambda x: x.get("rx", 0), reverse=True)[:20]

    return [
        {
            "user": u.get("usuario"),
            "rx": u.get("rx", 0),
            "pppoe": u.get("router", "N/A"),
            "vlan": 0
        }
        for u in sorted_data
    ]


# =========================
# TOP TX
# =========================
@app.get("/ppp/top-tx")
def top_tx():

    data = safe_obtener_datos()

    sorted_data = sorted(data, key=lambda x: x.get("tx", 0), reverse=True)[:20]

    return [
        {
            "user": u.get("usuario"),
            "tx": u.get("tx", 0),
            "pppoe": u.get("router", "N/A"),
            "vlan": 0
        }
        for u in sorted_data
    ]


# =========================
# VLAN
# =========================
@app.get("/ppp/by-vlan")
def by_vlan():

    data = safe_obtener_datos()

    return [{"vlan": 0, "users": len(data)}]


# =========================
# SERVER
# =========================
@app.get("/ppp/by-server")
def by_server():

    data = safe_obtener_datos()

    result = {}

    for u in data:
        srv = u.get("router", "UNKNOWN")
        result[srv] = result.get(srv, 0) + 1

    return [
        {"pppoe": k, "users": v}
        for k, v in result.items()
    ]


# =========================
# HISTORICO
# =========================
@app.get("/ppp/history")
def history():

    data = safe_obtener_datos()

    total_rx = sum(u.get("rx", 0) for u in data)
    total_tx = sum(u.get("tx", 0) for u in data)

    now = datetime.datetime.now().strftime("%H:%M:%S")

    return [{
        "time": now,
        "rx": total_rx,
        "tx": total_tx
    }]
