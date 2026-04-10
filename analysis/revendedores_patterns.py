def _to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "si", "sí", "yes"}
    return bool(value)


def preparar_cliente_revendedor(cliente):
    """
    Normaliza campos desde collectors para el motor de revendedores.
    """
    rx_bps = _to_float(cliente.get("rx", 0))
    tx_bps = _to_float(cliente.get("tx", 0))

    subida_mbps = _to_float(
        cliente.get("trafico_subida", cliente.get("tx_mbps", tx_bps / 1e6))
    )
    bajada_mbps = _to_float(
        cliente.get("trafico_bajada", cliente.get("rx_mbps", rx_bps / 1e6))
    )

    ips_detectadas = _to_int(
        cliente.get("ips_detectadas", cliente.get("ip_count", 1))
    )
    conexiones = _to_int(
        cliente.get("conexiones", cliente.get("connection_count", 0))
    )
    uso_constante = _to_bool(cliente.get("uso_constante", False))

    return {
        "usuario": cliente.get("usuario", "N/A"),
        "router": cliente.get("router", "N/A"),
        "trafico_subida": subida_mbps,
        "trafico_bajada": bajada_mbps,
        "ips_detectadas": ips_detectadas,
        "conexiones": conexiones,
        "uso_constante": uso_constante
    }
