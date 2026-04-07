# ==================================================
# FILE: ai/revenedores.py
# ==================================================

def detectar_revendedores(data, scores):

    sospechosos = []

    for u in data:

        usuario = u["usuario"]
        rx = int(u.get("rx", 0))
        tx = int(u.get("tx", 0))

        total = rx + tx
        ratio = tx / (rx + 1)

        score_user = next(
            (s["score"] for s in scores if s["usuario"] == usuario),
            0
        )

        # 🔥 NUEVA LÓGICA REALISTA ISP

        # 🔴 MUCHO UPLOAD + CONSUMO
        if ratio > 1.2 and total > 500_000_000:
            riesgo = "ALTO"

        # 🟠 consumo alto normal
        elif total > 1_000_000_000:
            riesgo = "MEDIO"

        else:
            continue

        sospechosos.append({
            "usuario": usuario,
            "score": score_user,
            "ratio": round(ratio, 2),
            "consumo": total,
            "riesgo": riesgo,
            "router": u.get("router", "N/A")
        })

    return sospechosos