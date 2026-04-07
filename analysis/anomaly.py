# ==================================================
# FILE: netai/analysis/anomaly.py
# ==================================================

from database.postgres import get_connection
from config.rules import RULES


def run_auto_analysis():

    conn = get_connection()
    cur = conn.cursor()

    alerts = []

    # PPP
    cur.execute("SELECT COUNT(*) FROM ppp_sessions")
    ppp = cur.fetchone()[0]

    if ppp > RULES["ppp_critical"]:
        alerts.append(("CRITICO", f"PPP alto: {ppp}"))

    elif ppp > RULES["ppp_warning"]:
        alerts.append(("WARNING", f"PPP elevado: {ppp}"))

    # Interfaces
    cur.execute("""
    SELECT interface, rx_bps
    FROM interface_traffic
    ORDER BY timestamp DESC
    LIMIT 20
    """)

    for r in cur.fetchall():

        iface = r[0]
        rx = r[1] or 0

        # ejemplo simple (adaptamos después)
        if rx > 1_000_000_000:  # 1Gbps
            alerts.append(("CRITICO", f"{iface} alto trafico"))

    # Guardar
    for nivel, mensaje in alerts:

        cur.execute("""
        INSERT INTO ai_logs (nivel,mensaje,origen)
        VALUES (%s,%s,%s)
        """, (nivel, mensaje, "AUTO"))

    conn.commit()
    cur.close()
    conn.close()

    # =========================
# IA TIEMPO REAL (NUEVO)
# =========================
def detectar_anomalias(data):

    alertas = []

    for u in data:

        rx = int(u.get("rx", 0))
        tx = int(u.get("tx", 0))

        if rx > 5_000_000_000:
            alertas.append({"usuario": u["usuario"], "tipo": "ALTO_RX"})

        if tx > rx * 1.5:
            alertas.append({"usuario": u["usuario"], "tipo": "UPLOAD_SOSPECHOSO"})

    return alertas