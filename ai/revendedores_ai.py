from analysis.revendedores_patterns import preparar_cliente_revendedor


def _clamp(n, lo=0, hi=100):
    return max(lo, min(hi, n))


def detectar_revendedor(cliente):
    c = preparar_cliente_revendedor(cliente)
    score = 0
    motivos = []

    if c["ips_detectadas"] > 5:
        score += 30
        motivos.append(f"muchas IPs detectadas ({c['ips_detectadas']})")

    simetria = 0
    if c["trafico_bajada"] > 0:
        simetria = c["trafico_subida"] / c["trafico_bajada"]

    if c["trafico_subida"] > 50 and c["trafico_bajada"] > 50:
        if 0.8 <= simetria <= 1.25:
            score += 30
            motivos.append(
                f"picos simétricos de tráfico (up {c['trafico_subida']:.2f} / down {c['trafico_bajada']:.2f} Mbps)"
            )
        else:
            score += 15
            motivos.append(
                f"picos altos de tráfico (up {c['trafico_subida']:.2f} / down {c['trafico_bajada']:.2f} Mbps)"
            )

    if c["conexiones"] > 20:
        score += 20
        motivos.append(f"muchas conexiones concurrentes ({c['conexiones']})")

    if c["uso_constante"]:
        score += 20
        motivos.append("uso constante sin valle de consumo")

    score = _clamp(score)

    if not motivos:
        explicacion = "Sin señales claras de reventa en esta muestra."
    else:
        explicacion = "Posible patrón de reventa detectado por: " + "; ".join(motivos) + "."

    return {
        "usuario": c["usuario"],
        "router": c["router"],
        "score_sospecha": score,
        "motivo": explicacion,
        "detalles": {
            "ips_detectadas": c["ips_detectadas"],
            "trafico_subida_mbps": round(c["trafico_subida"], 2),
            "trafico_bajada_mbps": round(c["trafico_bajada"], 2),
            "conexiones": c["conexiones"],
            "uso_constante": c["uso_constante"]
        }
    }


def analizar_revendedores(clientes):
    return [detectar_revendedor(c) for c in clientes]
