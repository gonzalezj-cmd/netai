from database.postgres import get_connection


def get_latest_ppp_live():
    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT ON (pl.router_id, pl.username)
                pl.username,
                COALESCE(pl.rx_bps, 0) AS rx_bps,
                COALESCE(pl.tx_bps, 0) AS tx_bps,
                COALESCE(pl.pppoe_server, r.name, 'UNKNOWN') AS pppoe,
                CASE
                    WHEN pl.vlan ~ '^[0-9]+$' THEN pl.vlan::int
                    ELSE 0
                END AS vlan,
                COALESCE(ps.uptime, '0s') AS uptime
            FROM ppp_live pl
            LEFT JOIN routers r ON r.id = pl.router_id
            LEFT JOIN ppp_sessions ps
                ON ps.router_id = pl.router_id
               AND ps.username = pl.username
            ORDER BY pl.router_id, pl.username, pl.timestamp DESC
        """)

        rows = cur.fetchall()
        return [
            {
                "usuario": r[0],
                "rx": int(r[1] or 0),
                "tx": int(r[2] or 0),
                "router": r[3] or "UNKNOWN",
                "vlan": int(r[4] or 0),
                "uptime": r[5],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"❌ dashboard_repo get_latest_ppp_live: {e}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
