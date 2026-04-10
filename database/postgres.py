import os
import atexit
from psycopg2 import pool

_DB_HOST = os.getenv("NETAI_DB_HOST", "10.226.4.46")
_DB_NAME = os.getenv("NETAI_DB_NAME", "netmonitor")
_DB_USER = os.getenv("NETAI_DB_USER", "netai")
_DB_PASSWORD = os.getenv("NETAI_DB_PASSWORD", "Ultra101")
_DB_MIN_CONN = int(os.getenv("NETAI_DB_POOL_MIN", "1"))
_DB_MAX_CONN = int(os.getenv("NETAI_DB_POOL_MAX", "8"))


_connection_pool = pool.ThreadedConnectionPool(
    _DB_MIN_CONN,
    _DB_MAX_CONN,
    host=_DB_HOST,
    database=_DB_NAME,
    user=_DB_USER,
    password=_DB_PASSWORD,
)


class _PooledConnectionProxy:
    def __init__(self, raw_conn):
        self._raw_conn = raw_conn
        self._released = False

    def __getattr__(self, name):
        return getattr(self._raw_conn, name)

    def close(self):
        if not self._released:
            _connection_pool.putconn(self._raw_conn)
            self._released = True


def get_connection():
    return _PooledConnectionProxy(_connection_pool.getconn())


def close_pool():
    _connection_pool.closeall()


atexit.register(close_pool)
