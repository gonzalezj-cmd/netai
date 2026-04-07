# ==================================================
# CONEXION MIKROTIK
# ==================================================

from routeros_api import RouterOsApiPool


# 🔌 conexión
def connect_to_router(router):

    connection = RouterOsApiPool(
        router["ip"],
        username=router["username"],
        password=router["password"],
        port=router.get("port", 8728),
        plaintext_login=True
    )

    api = connection.get_api()
    return api


# ==================================================
# OBTENER PPP ACTIVOS (REAL)
# ==================================================
def obtener_ppp_activos():

    # 🔴 CONFIGURÁ ESTO (temporal)
    router = {
        "ip": "127.0.0.1",   # ← CAMBIAR POR TU MIKROTIK
        "username": "admin",
        "password": "admin",
        "port": 8728
    }

    api = connect_to_router(router)

    ppp_active = api.get_resource('/ppp/active')
    usuarios = ppp_active.get()

    resultado = []

    for u in usuarios:
        resultado.append({
            "username": u.get("name"),
            "rx_bps": int(u.get("rx-byte", 0)),
            "tx_bps": int(u.get("tx-byte", 0)),
            "uptime": u.get("uptime", 0)
        })

    return resultado


# ==================================================
# WRAPPER IA (FINAL)
# ==================================================
def obtener_datos():

    raw_data = obtener_ppp_activos()

    resultado = []

    for u in raw_data:
        try:
            resultado.append({
                "usuario": u.get("username"),
                "rx": int(u.get("rx_bps", 0)),
                "tx": int(u.get("tx_bps", 0)),
                "uptime": u.get("uptime", 0),
                # Campos opcionales para IA de revendedores
                "ips_detectadas": u.get("ips_detectadas", u.get("ip_count", 1)),
                "conexiones": u.get("conexiones", u.get("connection_count", 0)),
                "uso_constante": u.get("uso_constante", False)
            })
        except:
            continue

    return resultado
