-- Migration: Remove options-related columns and enum value from backtest_strategies
-- Run this script in your SQL editor to migrate the database

-- Step 1: Drop options-related columns from backtest_strategies table
-- Note: These commands will fail gracefully if columns don't exist

ALTER TABLE backtest_strategies 
DROP COLUMN IF EXISTS strike_price,
DROP COLUMN IF EXISTS option_type,
DROP COLUMN IF EXISTS expiration_date,
DROP COLUMN IF EXISTS contracts_per_trade,
DROP COLUMN IF EXISTS leverage,
DROP COLUMN IF EXISTS margin_requirement;

-- Step 2: Add trade_direction column if it doesn't exist
-- (This column exists in the model but might not be in the database)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'backtest_strategies' 
        AND column_name = 'trade_direction'
    ) THEN
        ALTER TABLE backtest_strategies 
        ADD COLUMN trade_direction VARCHAR DEFAULT 'long';
    END IF;
END $$;

-- Step 3: Remove 'options' from asset_type_enum
-- PostgreSQL doesn't support removing enum values directly, so we need to recreate the enum

-- First, check if there are any strategies using 'options' asset_type
DO $$
DECLARE
    options_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO options_count 
    FROM backtest_strategies 
    WHERE asset_type::text = 'options';
    
    IF options_count > 0 THEN
        RAISE EXCEPTION 'Cannot remove options enum value: % strategies still use options asset_type. Please update or delete these strategies first.', options_count;
    END IF;
END $$;

-- Remove 'options' from enum by recreating it
DO $$ 
BEGIN
    -- Check if 'options' exists in the enum
    IF EXISTS (
        SELECT 1 FROM pg_enum 
        WHERE enumlabel = 'options' 
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'asset_type_enum')
    ) THEN
        -- Create new enum type without 'options'
        CREATE TYPE asset_type_enum_new AS ENUM ('stocks', 'crypto', 'forex', 'commodities', 'futures');
        
        -- Alter table to use new enum
        ALTER TABLE backtest_strategies 
        ALTER COLUMN asset_type TYPE asset_type_enum_new 
        USING asset_type::text::asset_type_enum_new;
        
        -- Drop old enum
        DROP TYPE asset_type_enum;
        
        -- Rename new enum to original name
        ALTER TYPE asset_type_enum_new RENAME TO asset_type_enum;
        
        RAISE NOTICE 'Successfully removed ''options'' from asset_type_enum';
    ELSE
        RAISE NOTICE '''options'' value not found in asset_type_enum, skipping enum migration';
    END IF;
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Enum migration already completed or in progress';
END $$;

-- Verification queries (optional - run these to verify the migration)
-- SELECT column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'backtest_strategies' 
-- ORDER BY ordinal_position;

-- SELECT unnest(enum_range(NULL::asset_type_enum)) AS asset_type_values;

