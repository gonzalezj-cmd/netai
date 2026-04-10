# ==================================================
# CONEXION MIKROTIK
# ==================================================
import os

try:
    from routeros_api import RouterOsApiPool
except Exception:
    RouterOsApiPool = None

from database.postgres import get_connection

LIVE_WINDOW_MINUTES = int(os.getenv("NETAI_LIVE_WINDOW_MINUTES", "30"))
MAX_USER_BPS = int(os.getenv("NETAI_MAX_USER_BPS", "1024000000"))


def _parse_numeric(value):
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)

    txt = str(value).strip().lower()
    if not txt:
        return 0

    mult = 1
    if txt.endswith("gbps") or txt.endswith("g"):
        mult = 1_000_000_000
        txt = txt.replace("gbps", "").replace("g", "")
    elif txt.endswith("mbps") or txt.endswith("m"):
        mult = 1_000_000
        txt = txt.replace("mbps", "").replace("m", "")
    elif txt.endswith("kbps") or txt.endswith("k"):
        mult = 1_000
        txt = txt.replace("kbps", "").replace("k", "")
    elif txt.endswith("bps"):
        txt = txt.replace("bps", "")

    txt = txt.strip()
    try:
        return int(float(txt) * mult)
    except Exception:
        return 0


def _parse_rate_pair(rate_value):
    # Mikrotik puede devolver "tx/rx" o "rx/tx" según recurso.
    if not rate_value:
        return 0, 0
    parts = str(rate_value).split("/")
    if len(parts) != 2:
        return 0, 0
    a = _parse_numeric(parts[0])
    b = _parse_numeric(parts[1])
    return a, b


# 🔌 conexión
def connect_to_router(router):

    if RouterOsApiPool is None:
        raise RuntimeError("routeros_api no está instalado")

    connection = RouterOsApiPool(
        router["ip"],
        username=router["username"],
        password=router["password"],
        port=router.get("port", 8728),
        plaintext_login=True
    )

    api = connection.get_api()
    return api


def obtener_routers_configurados():

    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, ip, username, password, port
            FROM routers
            ORDER BY id ASC
        """)

        rows = cur.fetchall()

        return [
            {
                "id": r[0],
                "name": r[1] or f"router-{r[0]}",
                "ip": r[2],
                "username": r[3],
                "password": r[4],
                "port": int(r[5] or 8728)
            }
            for r in rows
        ]

    except Exception as e:
        print(f"⚠️ Error leyendo routers desde BD: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def obtener_datos_desde_bd():
    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (pl.router_id, pl.username)
                pl.username,
                pl.rx_bps,
                pl.tx_bps,
                COALESCE(pl.pppoe_server, r.name, 'N/A') AS router_name,
                COALESCE(ps.uptime, '0s') AS uptime,
                COALESCE(pl.vlan, 0) AS vlan
            FROM ppp_live pl
            LEFT JOIN routers r ON r.id = pl.router_id
            LEFT JOIN ppp_sessions ps
                ON ps.router_id = pl.router_id
               AND ps.username = pl.username
            WHERE pl.timestamp >= NOW() - (%s || ' minutes')::interval
            ORDER BY pl.router_id, pl.username, pl.timestamp DESC
        """, (LIVE_WINDOW_MINUTES,))

        rows = cur.fetchall()

        return [
            {
                "usuario": r[0],
                "rx": min(_parse_numeric(r[1]), MAX_USER_BPS),
                "tx": min(_parse_numeric(r[2]), MAX_USER_BPS),
                "router": r[3] or "N/A",
                "uptime": r[4],
                "vlan": r[5] or 0
            }
            for r in rows
        ]

    except Exception as e:
        print(f"⚠️ Error leyendo ppp_live desde BD: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# ==================================================
# OBTENER PPP ACTIVOS (REAL)
# ==================================================
def obtener_ppp_activos():
    resultado = []
    routers = obtener_routers_configurados()

    if not routers:
        print("⚠️ No hay routers configurados en BD")
        return resultado

    for router in routers:
        try:
            api = connect_to_router(router)
            ppp_active = api.get_resource('/ppp/active')
            usuarios = ppp_active.get()

            for u in usuarios:
                rx = _parse_numeric(
                    u.get("rx-bits-per-second")
                    or u.get("rx_bps")
                )
                tx = _parse_numeric(
                    u.get("tx-bits-per-second")
                    or u.get("tx_bps")
                )

                # Fallback si viene como par en "rate"
                if rx == 0 and tx == 0:
                    r1, r2 = _parse_rate_pair(u.get("rate"))
                    # Alineado con collect_all: formato habitual tx/rx en RouterOS.
                    tx = r1
                    rx = r2

                resultado.append({
                    "username": u.get("name") or u.get("user") or "N/A",
                    "rx_bps": rx,
                    "tx_bps": tx,
                    "uptime": u.get("uptime", 0),
                    "router": router.get("name") or router.get("ip"),
                    "router_ip": router.get("ip")
                })

        except Exception as e:
            print(f"⚠️ Error en router {router.get('name')} ({router.get('ip')}): {e}")
            continue

    return resultado


# ==================================================
# WRAPPER IA (FINAL)
# ==================================================
def obtener_datos():

    try:
        data_bd = obtener_datos_desde_bd()
        if data_bd:
            return data_bd

        raw_data = obtener_ppp_activos()
    except Exception as e:
        print(f"⚠️ Error en obtener_datos(): {e}")
        return []

    resultado = []

    for u in raw_data:
        try:
            resultado.append({
                "usuario": u.get("username"),
                "rx": min(_parse_numeric(u.get("rx_bps", 0)), MAX_USER_BPS),
                "tx": min(_parse_numeric(u.get("tx_bps", 0)), MAX_USER_BPS),
                "uptime": u.get("uptime", 0),
                "router": u.get("router", "N/A"),
                # Campos opcionales para IA de revendedores
                "ips_detectadas": u.get("ips_detectadas", u.get("ip_count", 1)),
                "conexiones": u.get("conexiones", u.get("connection_count", 0)),
                "uso_constante": u.get("uso_constante", False)
            })
        except:
            continue

    return resultado
