# ==================================================
# CORE_COLLECTOR.py (ISP LEVEL - VLAN REAL FINAL OK)
# ==================================================

from database.postgres import get_connection
import time
import re
import os

CACHE_INTERFACES = {}
CACHE_PPP = {}
MAX_USER_BPS = int(os.getenv("NETAI_MAX_USER_BPS", "1024000000"))


def calcular_bps(prev, curr, seconds):
    if prev is None or seconds <= 0:
        return 0

    delta = curr - prev
    if delta < 0:
        return 0

    return (delta * 8) / seconds


def clean_name(name):
    if not name:
        return ""
    return name.replace("<", "").replace(">", "")


def extract_vlan_id(text):
    if not text:
        return None
    m = re.search(r'vlan[-_]?(\d+)', str(text).lower())
    if m:
        return m.group(1)
    return None


def parse_rate_to_bps(value):
    if value is None:
        return 0
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
    try:
        return int(float(txt) * mult)
    except Exception:
        return 0


def parse_rate_pair(rate_value):
    # Algunos RouterOS entregan "rate" como "tx/rx" o "rx/tx".
    if not rate_value:
        return 0, 0
    parts = str(rate_value).split("/")
    if len(parts) != 2:
        return 0, 0
    a = parse_rate_to_bps(parts[0])
    b = parse_rate_to_bps(parts[1])
    return a, b


def get_router_name(api):
    try:
        identity = api.get_resource('/system/identity').get()
        return identity[0].get("name", "unknown")
    except:
        return "unknown"


# ==================================================
# MAIN
# ==================================================
def collect_all(router, api):

    conn = get_connection()
    cur = conn.cursor()

    now = time.time()
    router_name = get_router_name(api)

    # ===============================
    # PPP ACTIVE
    # ===============================
    ppp = api.get_resource('/ppp/active').get()

    # Mapa service-name -> VLAN desde configuración PPPoE server.
    pppoe_server_map = {}
    try:
        pppoe_servers = api.get_resource('/interface/pppoe-server/server').get()
        for srv in pppoe_servers:
            service_name = (srv.get("service-name") or "").strip()
            iface_name = srv.get("interface")
            vlan_id = extract_vlan_id(iface_name)
            if service_name and vlan_id:
                pppoe_server_map[service_name] = vlan_id
    except Exception:
        pppoe_server_map = {}

    cur.execute("DELETE FROM ppp_sessions WHERE router_id = %s", (router["id"],))

    ppp_users = set()
    user_vlan_from_service = {}
    user_live_rates = {}

    for s in ppp:
        user = s.get("name")
        address = s.get("address")
        interface = s.get("interface")
        uptime = s.get("uptime")
        service_name = (s.get("service") or "").strip()

        ppp_users.add(user)
        if user and service_name in pppoe_server_map:
            user_vlan_from_service[user] = pppoe_server_map[service_name]

        if user:
            live_rx = parse_rate_to_bps(s.get("rx-bits-per-second") or s.get("rx_bps"))
            live_tx = parse_rate_to_bps(s.get("tx-bits-per-second") or s.get("tx_bps"))
            if live_rx == 0 and live_tx == 0:
                p1, p2 = parse_rate_pair(s.get("rate"))
                # En la mayoría de equipos viene como tx/rx.
                if p1 > 0 or p2 > 0:
                    live_tx, live_rx = p1, p2
            user_live_rates[user] = (live_rx, live_tx)

        cur.execute("""
        INSERT INTO ppp_sessions
        (router_id, username, address, interface, uptime)
        VALUES (%s,%s,%s,%s,%s)
        """, (
            router["id"],
            user,
            address,
            interface,
            uptime
        ))

    print(f"[PPP] activos: {len(ppp)}")

    # ===============================
    # VLAN REAL (🔥 CLAVE)
    # ===============================
    vlan_table = api.get_resource('/interface/vlan').get()

    vlan_map = {}

    for v in vlan_table:
        name = v.get("name", "").lower()
        vlan_id = v.get("vlan-id")

        if name and vlan_id:
            vlan_map[name] = str(vlan_id)

    print("VLAN MAP:", vlan_map)

    # ===============================
    # INTERFACES
    # ===============================
    interfaces = api.get_resource('/interface').get()

    for i in interfaces:

        name = clean_name(i.get("name"))
        rx_bytes = int(i.get("rx-byte", 0))
        tx_bytes = int(i.get("tx-byte", 0))

        # ===============================
        # PPP USERS
        # ===============================
        if "pppoe-" in name:

            user = name.replace("pppoe-", "")

            # ================= VLAN REAL =================
            vlan = user_vlan_from_service.get(user)

            # 🔥 Buscar coincidencia con nombre VLAN
            if not vlan:
                for vlan_name, vlan_id in vlan_map.items():

                    # ejemplo: vlan-102-dslam
                    if user in vlan_name:
                        vlan = vlan_id
                        break

            # 🔥 fallback: intentar por patrón
            if not vlan:
                for vlan_name, vlan_id in vlan_map.items():
                    if "vlan" in vlan_name:
                        vlan = vlan_id
                        break

            # ❌ nunca guardar 0
            if vlan in [None, "", "0"]:
                vlan = None

            # ================= TRAFICO =================
            prev = CACHE_PPP.get(user)

            if prev:
                seconds = now - prev["time"]
                rx_bps = calcular_bps(prev["rx"], rx_bytes, seconds)
                tx_bps = calcular_bps(prev["tx"], tx_bytes, seconds)
            else:
                rx_bps = 0
                tx_bps = 0

            # Preferir tasa en vivo reportada por PPP active cuando esté disponible.
            live_rx, live_tx = user_live_rates.get(user, (0, 0))
            if live_rx > 0 or live_tx > 0:
                rx_bps = live_rx
                tx_bps = live_tx

            CACHE_PPP[user] = {
                "rx": rx_bytes,
                "tx": tx_bytes,
                "time": now
            }

            if rx_bps > MAX_USER_BPS:
                rx_bps = 0
            if tx_bps > MAX_USER_BPS:
                tx_bps = 0

            cur.execute("""
            INSERT INTO ppp_live
            (router_id, username, rx_bps, tx_bps, pppoe_server, vlan, timestamp)
            VALUES (%s,%s,%s,%s,%s,%s, NOW())
            """, (
                router["id"],
                user,
                int(rx_bps),
                int(tx_bps),
                router_name,
                vlan
            ))

            print(f"[PPP LIVE] {user} | VLAN {vlan}")

        # ===============================
        # INTERFACES CORE
        # ===============================
        prev = CACHE_INTERFACES.get(name)

        if prev:
            seconds = now - prev["time"]
            rx_bps = calcular_bps(prev["rx"], rx_bytes, seconds)
            tx_bps = calcular_bps(prev["tx"], tx_bytes, seconds)
        else:
            rx_bps = 0
            tx_bps = 0

        CACHE_INTERFACES[name] = {
            "rx": rx_bytes,
            "tx": tx_bytes,
            "time": now
        }

        if rx_bps > MAX_USER_BPS:
            rx_bps = 0
        if tx_bps > MAX_USER_BPS:
            tx_bps = 0

        cur.execute("""
        INSERT INTO interface_traffic
        (router_id, interface, rx_bps, tx_bps)
        VALUES (%s,%s,%s,%s)
        """, (
            router["id"],
            name,
            int(rx_bps),
            int(tx_bps)
        ))

    conn.commit()
    cur.close()
    conn.close()

    print("✔ Collector OK (VLAN REAL FINAL)")
