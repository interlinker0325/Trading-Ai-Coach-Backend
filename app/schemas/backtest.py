from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.backtest import BacktestStatus, AssetType


# Strategy Schemas
class BacktestStrategyBase(BaseModel):
    name: str
    symbol: str
    asset_type: AssetType
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    indicators: Optional[List[str]] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None


class BacktestStrategyCreate(BacktestStrategyBase):
    pass


class BacktestStrategyUpdate(BaseModel):
    name: Optional[str] = None
    symbol: Optional[str] = None
    asset_type: Optional[AssetType] = None
    timeframe: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: Optional[float] = None
    indicators: Optional[List[str]] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    position_size: Optional[float] = None


class BacktestStrategyResponse(BacktestStrategyBase):
    id: int
    user_id: int
    natural_language_query: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Natural Language Backtest Request
class NaturalLanguageBacktestRequest(BaseModel):
    query: str = Field(..., description="Natural language description of the backtest strategy")
    symbol: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_capital: Optional[float] = 100000.0


# Result Schemas
class BacktestResultBase(BaseModel):
    strategy_id: int
    status: BacktestStatus
    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    total_trades: Optional[int] = None
    winning_trades: Optional[int] = None
    losing_trades: Optional[int] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    largest_win: Optional[float] = None
    largest_loss: Optional[float] = None
    consecutive_wins: Optional[int] = None
    consecutive_losses: Optional[int] = None
    volatility: Optional[float] = None
    equity_curve: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None


class BacktestResultResponse(BacktestResultBase):
    id: int
    user_id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Trade Schemas
class BacktestTradeResponse(BaseModel):
    id: int
    result_id: int
    entry_date: datetime
    exit_date: Optional[datetime] = None
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float
    trade_type: str
    pnl: Optional[float] = None
    pnl_percentage: Optional[float] = None
    duration_days: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Backtest Run Request
class BacktestRunRequest(BaseModel):
    strategy_id: Optional[int] = None  # If provided, use existing strategy
    strategy: Optional[BacktestStrategyCreate] = None  # If provided, create new strategy and run
    run_async: bool = True  # Run in background or wait for completion


# Backtest Run Response
class BacktestRunResponse(BaseModel):
    result_id: int
    status: BacktestStatus
    message: str
    estimated_completion_time: Optional[int] = None  # Seconds


# Full Backtest Result with Trades
class BacktestResultWithTrades(BacktestResultResponse):
    trades: List[BacktestTradeResponse] = []

