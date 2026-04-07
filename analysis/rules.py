def evaluar_reglas(data, scores):
    acciones = []

    for u in data:
        score_user = next((s["score"] for s in scores if s["usuario"] == u["usuario"]), 0)

        if score_user >= 8:
            accion = "LIMITAR_2MB"
        elif score_user >= 6:
            accion = "MONITOREAR"
        else:
            continue

        acciones.append({
            "usuario": u["usuario"],
            "accion": accion
        })

    # =========================
# IA TIEMPO REAL (NUEVO)
# =========================
def evaluar_reglas(data, scores):

    acciones = []

    for u in data:

        score_user = next(
            (s["score"] for s in scores if s["usuario"] == u["usuario"]),
            0
        )

        if score_user >= 8:
            acciones.append({
                "usuario": u["usuario"],
                "accion": "LIMITAR_2MB"
            })

        elif score_user >= 6:
            acciones.append({
                "usuario": u["usuario"],
                "accion": "MONITOREAR"
            })

    return acciones