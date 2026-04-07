from database.postgres import get_connection

conn = get_connection()
cur = conn.cursor()

print("🧹 Limpiando ppp_live...")

cur.execute("""
DELETE FROM ppp_live
WHERE timestamp < NOW() - INTERVAL '10 minutes'
""")

conn.commit()

cur.close()
conn.close()

print("✅ Limpieza OK")