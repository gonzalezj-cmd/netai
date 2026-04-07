# ==================================================
# DETECCION DE ABUSOS (ISP LEVEL)
# ==================================================

from database.postgres import get_connection


def detect_abuse():

    conn = get_connection()
    cur = conn.cursor()

    alerts = []

    # =========================
    # TOP PPPoE CONSUMO
    # =========================
    cur.execute("""
    SELECT interface, rx_bps, tx_bps
    FROM interface_traffic
    WHERE interface LIKE 'pppoe%'
    ORDER BY rx_bps DESC
    LIMIT 20
    """)

    rows = cur.fetchall()

    for r in rows:

        user = r[0]
        rx = r[1] or 0

        # 🔥 ABUSO DURO
        if rx > 100_000_000:  # 100 Mbps
            alerts.append((
                "CRITICO",
                f"ABUSO: {user} consumiendo {round(rx/1e6,2)} Mbps"
            ))

        # ⚠️ ABUSO MEDIO
        elif rx > 50_000_000:
            alerts.append((
                "WARNING",
                f"Alto consumo: {user} ({round(rx/1e6,2)} Mbps)"
            ))

    # =========================
    # VLAN SATURADAS
    # =========================
    cur.execute("""
    SELECT interface, rx_bps
    FROM interface_traffic
    WHERE interface LIKE 'vlan%'
    ORDER BY rx_bps DESC
    LIMIT 10
    """)

    for r in cur.fetchall():

        vlan = r[0]
        rx = r[1] or 0

        if rx > 900_000_000:
            alerts.append((
                "CRITICO",
                f"VLAN saturada: {vlan}"
            ))

    # =========================
    # GUARDAR
    # =========================
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
def detectar_abuso(data):

    alertas = []

    for u in data:

        rx = int(u.get("rx", 0))
        tx = int(u.get("tx", 0))

        total = rx + tx

        if total > 8_000_000_000:
            alertas.append({"usuario": u["usuario"], "tipo": "CONSUMO_EXTREMO"})

    return alertas