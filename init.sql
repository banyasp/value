CREATE TABLE IF NOT EXISTS raw_trades (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    price NUMERIC(18, 8) NOT NULL,
    volume NUMERIC(18, 8) NOT NULL,
    trade_timestamp BIGINT NOT NULL,
    conditions JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_trades_symbol_ts ON raw_trades (symbol, trade_timestamp);

CREATE TABLE IF NOT EXISTS raw_news (
    id BIGSERIAL PRIMARY KEY,
    finnhub_id BIGINT NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    category VARCHAR(64),
    headline TEXT NOT NULL,
    summary TEXT,
    source VARCHAR(128),
    url TEXT,
    image_url TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (finnhub_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_raw_news_symbol_published_at
    ON raw_news (symbol, published_at);

CREATE TABLE IF NOT EXISTS trade_event_windows (
    id BIGSERIAL PRIMARY KEY,
    news_id BIGINT NOT NULL REFERENCES raw_news(id) ON DELETE CASCADE,
    symbol VARCHAR(32) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    trade_count INTEGER NOT NULL DEFAULT 0,
    total_volume NUMERIC(18, 8),
    vwap NUMERIC(18, 8),
    price_open NUMERIC(18, 8),
    price_close NUMERIC(18, 8),
    price_high NUMERIC(18, 8),
    price_low NUMERIC(18, 8),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (news_id, window_start, window_end)
);

CREATE INDEX IF NOT EXISTS idx_trade_event_windows_symbol_start
    ON trade_event_windows (symbol, window_start);

CREATE TABLE IF NOT EXISTS trade_summaries (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(32) NOT NULL,
    interval_start TIMESTAMPTZ NOT NULL,
    interval_minutes INTEGER NOT NULL,
    trade_count INTEGER NOT NULL DEFAULT 0,
    total_volume NUMERIC(18, 8),
    vwap NUMERIC(18, 8),
    price_open NUMERIC(18, 8),
    price_close NUMERIC(18, 8),
    price_high NUMERIC(18, 8),
    price_low NUMERIC(18, 8),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (symbol, interval_start, interval_minutes)
);

CREATE INDEX IF NOT EXISTS idx_trade_summaries_symbol_interval
    ON trade_summaries (symbol, interval_minutes, interval_start);

CREATE OR REPLACE VIEW company_event_view AS
SELECT
    symbol,
    'news' AS event_type,
    published_at AS event_time,
    headline AS description,
    NULL::numeric AS price,
    NULL::numeric AS volume
FROM raw_news
UNION ALL
SELECT
    symbol,
    'trade' AS event_type,
    TO_TIMESTAMP(trade_timestamp / 1000.0) AS event_time,
    NULL AS description,
    price,
    volume
FROM raw_trades;
