# ==================================================
# CONEXION MIKROTIK
# ==================================================

try:
    from routeros_api import RouterOsApiPool
except Exception:
    RouterOsApiPool = None


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


# ==================================================
# OBTENER PPP ACTIVOS (REAL)
# ==================================================
def obtener_ppp_activos():

    # 🔴 CONFIGURÁ ESTO (temporal)
    router = {
        "ip": "10.226.0.99",   # ← CAMBIAR POR TU MIKROTIK
        "username": "chichi",
        "password": "yobancoalremisero",
        "port": 8728
    }

    try:
        api = connect_to_router(router)
        ppp_active = api.get_resource('/ppp/active')
        usuarios = ppp_active.get()
    except Exception as e:
        print(f"⚠️ Error obteniendo PPP activos desde MikroTik: {e}")
        return []

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

    try:
        raw_data = obtener_ppp_activos()
    except Exception as e:
        print(f"⚠️ Error en obtener_datos(): {e}")
        return []

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
