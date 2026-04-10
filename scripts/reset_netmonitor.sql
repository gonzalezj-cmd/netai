-- RESET TOTAL DE NETMONITOR (BORRA HISTORICO)
-- Ejecutar como postgres: psql -d postgres -f scripts/reset_netmonitor.sql

DROP DATABASE IF EXISTS netmonitor;
DROP ROLE IF EXISTS netai;

CREATE ROLE netai LOGIN PASSWORD 'Ultra101';
CREATE DATABASE netmonitor OWNER netai;

\connect netmonitor

CREATE TABLE routers (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    ip INET NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 8728,
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ppp_sessions (
    id BIGSERIAL PRIMARY KEY,
    router_id BIGINT REFERENCES routers(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    address TEXT,
    interface TEXT,
    uptime TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ppp_live (
    id BIGSERIAL PRIMARY KEY,
    router_id BIGINT REFERENCES routers(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    rx_bps BIGINT NOT NULL DEFAULT 0,
    tx_bps BIGINT NOT NULL DEFAULT 0,
    pppoe_server TEXT,
    vlan TEXT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE interface_traffic (
    id BIGSERIAL PRIMARY KEY,
    router_id BIGINT REFERENCES routers(id) ON DELETE CASCADE,
    interface TEXT NOT NULL,
    rx_bps BIGINT NOT NULL DEFAULT 0,
    tx_bps BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ai_logs (
    id BIGSERIAL PRIMARY KEY,
    nivel TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    origen TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ppp_live_router_user_ts ON ppp_live(router_id, username, timestamp DESC);
CREATE INDEX idx_ppp_sessions_router_user ON ppp_sessions(router_id, username);
CREATE INDEX idx_interface_traffic_router_time ON interface_traffic(router_id, created_at DESC);

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO netai;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO netai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO netai;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO netai;
