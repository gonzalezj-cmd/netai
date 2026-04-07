import psycopg2


def get_connection():

    conn = psycopg2.connect(
        host="10.226.4.46",
        database="netmonitor",
        user="netai",
        password="Ultra101"
    )

    return conn