from database.postgres import get_connection

conn = get_connection()
cur = conn.cursor()

print("📊 Generando resumen diario...")

cur.execute("""
INSERT INTO ppp_daily
SELECT
    CURRENT_DATE,
    username,
    pppoe_server,
    vlan,
    AVG(rx_bps),
    MAX(rx_bps),
    SUM(rx_bps)
FROM ppp_live
GROUP BY username, pppoe_server, vlan
""")

conn.commit()

cur.close()
conn.close()

print("✅ Resumen guardado")