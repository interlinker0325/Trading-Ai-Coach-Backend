-- Create backtest tables
-- This script creates all necessary tables and enums for the backtest functionality

-- Create asset_type_enum
DO $$ BEGIN
    CREATE TYPE asset_type_enum AS ENUM ('stocks', 'crypto', 'forex', 'commodities', 'options', 'futures');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create backtest_status_enum
DO $$ BEGIN
    CREATE TYPE backtest_status_enum AS ENUM ('pending', 'running', 'completed', 'failed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create backtest_strategies table
CREATE TABLE IF NOT EXISTS backtest_strategies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    symbol VARCHAR NOT NULL,
    asset_type asset_type_enum NOT NULL,
    timeframe VARCHAR NOT NULL,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    initial_capital DOUBLE PRECISION NOT NULL DEFAULT 100000.0,
    indicators JSONB,
    entry_rules TEXT,
    exit_rules TEXT,
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,
    position_size DOUBLE PRECISION,
    natural_language_query TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_backtest_strategies_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_backtest_strategies_id ON backtest_strategies(id);
CREATE INDEX IF NOT EXISTS ix_backtest_strategies_user_id ON backtest_strategies(user_id);

-- Create backtest_results table
CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status backtest_status_enum NOT NULL DEFAULT 'pending',
    total_return DOUBLE PRECISION,
    annualized_return DOUBLE PRECISION,
    sharpe_ratio DOUBLE PRECISION,
    sortino_ratio DOUBLE PRECISION,
    calmar_ratio DOUBLE PRECISION,
    max_drawdown DOUBLE PRECISION,
    win_rate DOUBLE PRECISION,
    profit_factor DOUBLE PRECISION,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    avg_win DOUBLE PRECISION,
    avg_loss DOUBLE PRECISION,
    largest_win DOUBLE PRECISION,
    largest_loss DOUBLE PRECISION,
    consecutive_wins INTEGER DEFAULT 0,
    consecutive_losses INTEGER DEFAULT 0,
    volatility DOUBLE PRECISION,
    equity_curve JSONB,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_backtest_results_strategy FOREIGN KEY (strategy_id) REFERENCES backtest_strategies(id) ON DELETE CASCADE,
    CONSTRAINT fk_backtest_results_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_backtest_results_id ON backtest_results(id);
CREATE INDEX IF NOT EXISTS ix_backtest_results_strategy_id ON backtest_results(strategy_id);
CREATE INDEX IF NOT EXISTS ix_backtest_results_user_id ON backtest_results(user_id);

-- Create backtest_trades table
CREATE TABLE IF NOT EXISTS backtest_trades (
    id SERIAL PRIMARY KEY,
    result_id INTEGER NOT NULL,
    entry_date TIMESTAMP WITH TIME ZONE NOT NULL,
    exit_date TIMESTAMP WITH TIME ZONE,
    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION,
    quantity DOUBLE PRECISION NOT NULL,
    trade_type VARCHAR NOT NULL,
    pnl DOUBLE PRECISION,
    pnl_percentage DOUBLE PRECISION,
    duration_days DOUBLE PRECISION,
    stop_loss_price DOUBLE PRECISION,
    take_profit_price DOUBLE PRECISION,
    exit_reason VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_backtest_trades_result FOREIGN KEY (result_id) REFERENCES backtest_results(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_backtest_trades_id ON backtest_trades(id);
CREATE INDEX IF NOT EXISTS ix_backtest_trades_result_id ON backtest_trades(result_id);

