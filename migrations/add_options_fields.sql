-- Migration: Add options-specific fields to backtest_strategies table
-- Date: 2025-01-XX
-- Description: Adds support for options backtesting with strike price, option type, expiration, contracts, leverage, and margin

-- Add strike_price column
ALTER TABLE backtest_strategies 
ADD COLUMN IF NOT EXISTS strike_price DOUBLE PRECISION;

-- Add option_type column (call or put)
ALTER TABLE backtest_strategies 
ADD COLUMN IF NOT EXISTS option_type VARCHAR;

-- Add expiration_date column
ALTER TABLE backtest_strategies 
ADD COLUMN IF NOT EXISTS expiration_date TIMESTAMP WITH TIME ZONE;

-- Add contracts_per_trade column
ALTER TABLE backtest_strategies 
ADD COLUMN IF NOT EXISTS contracts_per_trade INTEGER;

-- Add leverage column with default 1.0 (no leverage)
ALTER TABLE backtest_strategies 
ADD COLUMN IF NOT EXISTS leverage DOUBLE PRECISION DEFAULT 1.0;

-- Add margin_requirement column
ALTER TABLE backtest_strategies 
ADD COLUMN IF NOT EXISTS margin_requirement DOUBLE PRECISION;

