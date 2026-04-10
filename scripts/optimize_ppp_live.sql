-- Optimización para tablas ppp_live grandes
-- Ejecutar en DB host: sudo -u postgres psql -d netmonitor -f scripts/optimize_ppp_live.sql

CREATE INDEX IF NOT EXISTS idx_ppp_live_ts ON ppp_live (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ppp_live_router_user_ts ON ppp_live (router_id, username, timestamp DESC);
ANALYZE ppp_live;
