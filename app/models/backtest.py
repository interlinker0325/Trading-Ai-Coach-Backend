from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum


class BacktestStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AssetType(str, enum.Enum):
    STOCKS = "stocks"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITIES = "commodities"
    OPTIONS = "options"
    FUTURES = "futures"


class BacktestStrategy(Base):
    __tablename__ = "backtest_strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    symbol = Column(String, nullable=False)
    asset_type = Column(
        Enum(AssetType, name="asset_type_enum", values_callable=lambda enum: [e.value for e in enum]),
        nullable=False
    )
    timeframe = Column(String, nullable=False)  # e.g., "1m", "5m", "1h", "1d"
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    initial_capital = Column(Float, nullable=False, default=100000.0)
    
    # Strategy configuration
    indicators = Column(JSON, nullable=True)  # List of selected indicators
    entry_rules = Column(Text, nullable=True)  # Entry condition rules
    exit_rules = Column(Text, nullable=True)  # Exit condition rules
    stop_loss = Column(Float, nullable=True)  # Stop loss percentage
    take_profit = Column(Float, nullable=True)  # Take profit percentage
    position_size = Column(Float, nullable=True)  # Position size percentage
    trade_direction = Column(String, nullable=True, default="long")  # "long", "short", or "both"
    
    # Natural language query (for AI-generated strategies)
    natural_language_query = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="backtest_strategies")
    results = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("backtest_strategies.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Status
    status = Column(
        Enum(BacktestStatus, name="backtest_status_enum", values_callable=lambda enum: [e.value for e in enum]),
        nullable=False,
        default=BacktestStatus.PENDING
    )
    
    # Performance metrics
    total_return = Column(Float, nullable=True)  # Total return percentage
    annualized_return = Column(Float, nullable=True)  # Annualized return percentage
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    calmar_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)  # Maximum drawdown percentage
    win_rate = Column(Float, nullable=True)  # Win rate percentage
    profit_factor = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True, default=0)
    winning_trades = Column(Integer, nullable=True, default=0)
    losing_trades = Column(Integer, nullable=True, default=0)
    avg_win = Column(Float, nullable=True)
    avg_loss = Column(Float, nullable=True)
    largest_win = Column(Float, nullable=True)
    largest_loss = Column(Float, nullable=True)
    consecutive_wins = Column(Integer, nullable=True, default=0)
    consecutive_losses = Column(Integer, nullable=True, default=0)
    volatility = Column(Float, nullable=True)
    
    # Equity curve data (stored as JSON array)
    equity_curve = Column(JSON, nullable=True)  # Array of {date, value, drawdown}
    
    # Error message if failed
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    strategy = relationship("BacktestStrategy", back_populates="results")
    user = relationship("User", backref="backtest_results")
    trades = relationship("BacktestTrade", back_populates="result", cascade="all, delete-orphan")


class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(Integer, ForeignKey("backtest_results.id"), nullable=False, index=True)
    
    # Trade details
    entry_date = Column(DateTime(timezone=True), nullable=False)
    exit_date = Column(DateTime(timezone=True), nullable=True)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    trade_type = Column(String, nullable=False)  # "buy" or "sell"
    
    # Trade metrics
    pnl = Column(Float, nullable=True)  # Profit/Loss in dollars
    pnl_percentage = Column(Float, nullable=True)  # Profit/Loss percentage
    duration_days = Column(Float, nullable=True)  # Trade duration in days
    
    # Stop loss and take profit
    stop_loss_price = Column(Float, nullable=True)
    take_profit_price = Column(Float, nullable=True)
    
    # Exit reason
    exit_reason = Column(String, nullable=True)  # "stop_loss", "take_profit", "signal", "end_of_period"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    result = relationship("BacktestResult", back_populates="trades")

