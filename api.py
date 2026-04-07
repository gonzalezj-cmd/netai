# ==================================================
# API FINAL LIMPIO - NETAI
# ==================================================

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import threading
import time
import datetime

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


# =========================
# APP
# =========================
app = FastAPI(title="NetAI NOC", version="2.0")

app.mount("/dashboard_static", StaticFiles(directory="dashboard"), name="dashboard")


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


# =========================
# DASHBOARD
# =========================
@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard/index.html")


@app.get("/ai_page")
def ai_page():
    return FileResponse("dashboard/ai.html")


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

            data = obtener_datos()

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
def dashboard_data():

    data = obtener_datos()

    total = len(data)

    por_router = {}

    for u in data:
        r = u.get("router", "N/A")
        por_router[r] = por_router.get(r, 0) + 1

    return {
        "ppp_activos": total,
        "usuarios_por_router": por_router
    }


# =========================
# PPP SUMMARY
# =========================
@app.get("/ppp/summary")
def ppp_summary():

    data = obtener_datos()

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

    data = obtener_datos()

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

    data = obtener_datos()

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

    data = obtener_datos()

    return [{"vlan": 0, "users": len(data)}]


# =========================
# SERVER
# =========================
@app.get("/ppp/by-server")
def by_server():

    data = obtener_datos()

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

    data = obtener_datos()

    total_rx = sum(u.get("rx", 0) for u in data)
    total_tx = sum(u.get("tx", 0) for u in data)

    now = datetime.datetime.now().strftime("%H:%M:%S")

    return [{
        "time": now,
        "rx": total_rx,
        "tx": total_tx
    }]