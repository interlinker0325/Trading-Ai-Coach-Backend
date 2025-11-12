from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from app.models.backtest import BacktestStrategy, BacktestResult, BacktestTrade, BacktestStatus
from app.schemas.backtest import (
    BacktestStrategyCreate,
    BacktestStrategyUpdate,
    BacktestResultBase,
)


# Strategy CRUD
def create_backtest_strategy(
    db: Session, strategy: BacktestStrategyCreate, user_id: int
) -> BacktestStrategy:
    """Create a new backtest strategy"""
    db_strategy = BacktestStrategy(
        user_id=user_id,
        **strategy.model_dump()
    )
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy


def get_backtest_strategy(
    db: Session, strategy_id: int, user_id: Optional[int] = None
) -> Optional[BacktestStrategy]:
    """Get a backtest strategy by ID"""
    query = db.query(BacktestStrategy).filter(BacktestStrategy.id == strategy_id)
    if user_id:
        query = query.filter(BacktestStrategy.user_id == user_id)
    return query.first()


def get_backtest_strategies(
    db: Session, user_id: int, skip: int = 0, limit: int = 100
) -> List[BacktestStrategy]:
    """Get all backtest strategies for a user"""
    return (
        db.query(BacktestStrategy)
        .filter(BacktestStrategy.user_id == user_id)
        .order_by(desc(BacktestStrategy.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_backtest_strategy(
    db: Session,
    strategy_id: int,
    strategy_update: BacktestStrategyUpdate,
    user_id: int,
) -> Optional[BacktestStrategy]:
    """Update a backtest strategy"""
    strategy = get_backtest_strategy(db, strategy_id, user_id)
    if not strategy:
        return None
    
    update_data = strategy_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(strategy, field, value)
    
    db.commit()
    db.refresh(strategy)
    return strategy


def delete_backtest_strategy(
    db: Session, strategy_id: int, user_id: int
) -> bool:
    """Delete a backtest strategy"""
    strategy = get_backtest_strategy(db, strategy_id, user_id)
    if not strategy:
        return False
    
    db.delete(strategy)
    db.commit()
    return True


# Result CRUD
def create_backtest_result(
    db: Session, strategy_id: int, user_id: int, status: BacktestStatus = BacktestStatus.PENDING
) -> BacktestResult:
    """Create a new backtest result"""
    db_result = BacktestResult(
        strategy_id=strategy_id,
        user_id=user_id,
        status=status,
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


def get_backtest_result(
    db: Session, result_id: int, user_id: Optional[int] = None
) -> Optional[BacktestResult]:
    """Get a backtest result by ID"""
    query = db.query(BacktestResult).filter(BacktestResult.id == result_id)
    if user_id:
        query = query.filter(BacktestResult.user_id == user_id)
    return query.first()


def get_backtest_results(
    db: Session, user_id: int, strategy_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[BacktestResult]:
    """Get all backtest results for a user"""
    query = db.query(BacktestResult).filter(BacktestResult.user_id == user_id)
    if strategy_id:
        query = query.filter(BacktestResult.strategy_id == strategy_id)
    return (
        query.order_by(desc(BacktestResult.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_backtest_result(
    db: Session, result_id: int, result_data: dict, user_id: Optional[int] = None
) -> Optional[BacktestResult]:
    """Update a backtest result"""
    result = get_backtest_result(db, result_id, user_id)
    if not result:
        return None
    
    for field, value in result_data.items():
        setattr(result, field, value)
    
    db.commit()
    db.refresh(result)
    return result


def delete_backtest_result(
    db: Session, result_id: int, user_id: int
) -> bool:
    """Delete a backtest result"""
    result = get_backtest_result(db, result_id, user_id)
    if not result:
        return False
    
    db.delete(result)
    db.commit()
    return True


# Trade CRUD
def create_backtest_trade(
    db: Session, result_id: int, trade_data: dict
) -> BacktestTrade:
    """Create a new backtest trade"""
    db_trade = BacktestTrade(
        result_id=result_id,
        **trade_data
    )
    db.add(db_trade)
    db.commit()
    db.refresh(db_trade)
    return db_trade


def get_backtest_trades(
    db: Session, result_id: int, skip: int = 0, limit: int = 1000
) -> List[BacktestTrade]:
    """Get all trades for a backtest result"""
    return (
        db.query(BacktestTrade)
        .filter(BacktestTrade.result_id == result_id)
        .order_by(BacktestTrade.entry_date)
        .offset(skip)
        .limit(limit)
        .all()
    )


def bulk_create_backtest_trades(
    db: Session, result_id: int, trades: List[dict]
) -> List[BacktestTrade]:
    """Bulk create backtest trades"""
    db_trades = [
        BacktestTrade(result_id=result_id, **trade_data)
        for trade_data in trades
    ]
    db.bulk_save_objects(db_trades)
    db.commit()
    return db_trades

