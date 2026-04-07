# ==================================================
# LOOP PRINCIPAL DE COLECTORES
# COLLECTOR_LOOP.PY
# ==================================================

import time
from collectors.core_collector import collect_all
from collectors.mikrotik import connect_to_router
from database.postgres import get_connection

def get_routers():

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, ip, username, password, port FROM routers")

    routers = []

    for r in cur.fetchall():
        routers.append({
            "id": r[0],
            "ip": r[1],
            "username": r[2],
            "password": r[3],
            "port": r[4]
        })

    cur.close()
    conn.close()

    return routers


while True:

    routers = get_routers()

    for r in routers:

        try:
            print(f"Conectando a {r['ip']}")

            api = connect_to_router(r)

            collect_all(r, api)

        except Exception as e:
            print("ERROR:", e)

    time.sleep(3)