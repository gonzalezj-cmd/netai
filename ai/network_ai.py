# ==================================================
# FILE: netai/ai/network_ai.py
# NOC PRO - AI ENGINE (FIXED)
# ==================================================
print("🔥 CARGANDO NETWORK_AI CORRECTO")
from openai import OpenAI
from database.postgres import get_connection
from config.config import OPENAI_API_KEY
import json
import traceback
from analysis.abuse import detect_abuse

# ==========================================
# CLIENTE IA
# ==========================================
client = OpenAI(api_key=OPENAI_API_KEY)


# ==========================================
# ANONIMIZAR INTERFACES
# ==========================================
def anonymize_interfaces(data):

    clean = []

    for i, r in enumerate(data):
        clean.append({
            "iface": f"IFACE_{i}",
            "rx": r[1] or 0,
            "tx": r[2] or 0
        })

    return clean


# ==========================================
# GUARDAR LOG
# ==========================================
def save_log(nivel, mensaje, origen="AI"):

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
        INSERT INTO ai_logs (nivel, mensaje, origen)
        VALUES (%s,%s,%s)
        """, (nivel, mensaje, origen))

        conn.commit()
        cur.close()
        conn.close()

    except Exception as e:
        print("Error guardando log:", e)


# ==========================================
# FALLBACK SIN IA
# ==========================================
def fallback_analysis(raw_interfaces, ppp_count):

    alerts = []
    estado = "OK"

    for r in raw_interfaces:

        iface = r[0]
        rx = r[1] or 0
        tx = r[2] or 0

        max_val = max(rx, tx)

        if max_val > 900_000_000:
            alerts.append({
                "nivel": "CRITICO",
                "mensaje": f"{iface} saturado ({round(max_val/1e6,2)} Mbps)"
            })
            estado = "CRITICO"

        elif max_val > 500_000_000:
            alerts.append({
                "nivel": "WARNING",
                "mensaje": f"{iface} alto trafico ({round(max_val/1e6,2)} Mbps)"
            })

    if ppp_count > 10000:
        alerts.append({
            "nivel": "CRITICO",
            "mensaje": f"PPP excesivo ({ppp_count})"
        })
        estado = "CRITICO"

    elif ppp_count > 5000:
        alerts.append({
            "nivel": "WARNING",
            "mensaje": f"PPP elevado ({ppp_count})"
        })

    return {
        "estado": estado,
        "alertas": alerts,
        "resumen": "Analisis automatico (fallback)"
    }


# ==========================================
# ANALISIS PRINCIPAL
# ==========================================
def analyze_network():

    try:

        conn = get_connection()
        cur = conn.cursor()

        # ==============================
        # TRAFICO
        # ==============================
        cur.execute("""
        SELECT interface, rx_bps, tx_bps
        FROM interface_traffic
        ORDER BY timestamp DESC
        LIMIT 20
        """)

        raw_interfaces = cur.fetchall()
        interfaces = anonymize_interfaces(raw_interfaces)

        # ==============================
        # PPP
        # ==============================
        cur.execute("""
        SELECT COUNT(*) FROM ppp_sessions
        """)

        ppp_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        # ==========================
        # ABUSE DETECTION
        # ==========================
        abuse_alerts = detect_abuse()

        for nivel, mensaje in abuse_alerts:
            save_log(nivel, mensaje, "AUTO")

        # ==============================
        # PROMPT IA
        # ==============================
        prompt = f"""
Sos un sistema NOC de ISP.

Analizá tráfico de red y detectá problemas.

Responde SOLO JSON válido.

Formato:
{{
  "estado": "OK|WARNING|CRITICO",
  "alertas": [
    {{"nivel":"CRITICO","mensaje":"texto"}}
  ],
  "resumen": "texto corto"
}}

Reglas:
- CRITICO si hay saturacion (>900 Mbps)
- WARNING si >500 Mbps
- Considerar cantidad de PPP
- Detectar patrones anormales

PPP activos: {ppp_count}

Interfaces:
{interfaces}
"""

        # ==============================
        # LLAMADA IA
        # ==============================
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt
        )

        text = response.output_text

        # ==============================
        # PARSEO
        # ==============================
        try:

            data = json.loads(text)

            for alerta in data.get("alertas", []):
                save_log(alerta["nivel"], alerta["mensaje"], "AI")

            return data

        except Exception:
            save_log("ERROR", "Error parseando IA", "AI")
            print("Respuesta IA inválida:", text)

            result = fallback_analysis(raw_interfaces, ppp_count)

            for alerta in result["alertas"]:
                save_log(alerta["nivel"], alerta["mensaje"], "AUTO")

            return result

    except Exception as e:

        error_msg = f"Error IA: {str(e)}"
        print(error_msg)
        traceback.print_exc()

        save_log("ERROR", error_msg, "AI")

        return {
            "estado": "ERROR",
            "alertas": [],
            "resumen": "Falla en motor IA"
        }