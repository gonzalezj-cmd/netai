# ==================================================
# ENGINE IA ROBUSTO
# ==================================================

from analysis.anomaly import detectar_anomalias
from analysis.abuse import detectar_abuso
from analysis.rules import evaluar_reglas

from ai.scoring import calcular_score
from ai.revendedores import detectar_revendedores
from ai.revendedores_ai import analizar_revendedores


def ejecutar_ia(data):

    try:

        if not data:
            return {"error": "Sin datos"}

        data_ok = []

        for u in data:

            try:
                usuario = str(u.get("usuario", ""))

                rx = u.get("rx", 0)
                tx = u.get("tx", 0)

                # 🔥 NORMALIZACIÓN CRÍTICA
                rx = int(rx) if str(rx).isdigit() else 0
                tx = int(tx) if str(tx).isdigit() else 0

                data_ok.append({
                    "usuario": usuario,
                    "rx": rx,
                    "tx": tx,
                    "uptime": u.get("uptime", 0),
                    "router": u.get("router", "N/A")
                })

            except:
                continue

        # 🔍 IA
        anomalias = detectar_anomalias(data_ok)
        abuso = detectar_abuso(data_ok)
        scores = calcular_score(data_ok, anomalias, abuso)
        revendedores = detectar_revendedores(data_ok, scores)
        revendedores_ai = analizar_revendedores(data_ok)
        acciones = evaluar_reglas(data_ok, scores)

        return {
            "total": len(data_ok),
            "anomalias": anomalias,
            "abuso": abuso,
            "scores": scores,
            "revendedores": revendedores,
            "revendedores_ai": revendedores_ai,
            "acciones": acciones
        }

    except Exception as e:
        return {
            "error": str(e),
            "tipo": "engine_error"
        }
