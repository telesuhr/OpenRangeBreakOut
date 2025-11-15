-- ティックデータ（5分足）保存テーブル
CREATE TABLE IF NOT EXISTS intraday_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open NUMERIC(12, 2),
    high NUMERIC(12, 2),
    low NUMERIC(12, 2),
    close NUMERIC(12, 2),
    volume BIGINT,
    interval VARCHAR(10) DEFAULT '5min',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp, interval)
);

-- 検索高速化のためのインデックス
CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON intraday_data(symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_timestamp ON intraday_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_symbol ON intraday_data(symbol);

-- データ取得ログテーブル（デバッグ用）
CREATE TABLE IF NOT EXISTS data_fetch_log (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    interval VARCHAR(10),
    source VARCHAR(20), -- 'api' or 'cache'
    records_count INT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- インデックス
CREATE INDEX IF NOT EXISTS idx_fetch_log_symbol ON data_fetch_log(symbol, fetched_at);
