-- Migration: Add trade_direction column to backtest_strategies table
-- Date: 2025-01-XX
-- Description: Adds support for long, short, or both trade directions

-- Add trade_direction column with default value 'long'
ALTER TABLE backtest_strategies 
ADD COLUMN IF NOT EXISTS trade_direction VARCHAR DEFAULT 'long';

-- Update existing records to have 'long' as default (if column was just added)
UPDATE backtest_strategies 
SET trade_direction = 'long' 
WHERE trade_direction IS NULL;

