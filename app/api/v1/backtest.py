from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.crud import backtest as crud
from app.schemas.backtest import (
    BacktestStrategyCreate,
    BacktestStrategyUpdate,
    BacktestStrategyResponse,
    BacktestResultResponse,
    BacktestResultWithTrades,
    BacktestTradeResponse,
    BacktestRunRequest,
    BacktestRunResponse,
)
from app.models.backtest import BacktestStatus
from app.tasks.backtest import run_backtest_task

router = APIRouter()


# Strategy Endpoints
@router.post("/strategies", response_model=BacktestStrategyResponse, status_code=status.HTTP_201_CREATED)
def create_strategy(
    strategy: BacktestStrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new backtest strategy"""
    return crud.create_backtest_strategy(db, strategy, current_user.id)


@router.get("/strategies", response_model=List[BacktestStrategyResponse])
def list_strategies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all backtest strategies for the current user"""
    return crud.get_backtest_strategies(db, current_user.id, skip=skip, limit=limit)


@router.get("/strategies/{strategy_id}", response_model=BacktestStrategyResponse)
def get_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific backtest strategy"""
    strategy = crud.get_backtest_strategy(db, strategy_id, current_user.id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    return strategy


@router.put("/strategies/{strategy_id}", response_model=BacktestStrategyResponse)
def update_strategy(
    strategy_id: int,
    strategy_update: BacktestStrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a backtest strategy"""
    strategy = crud.update_backtest_strategy(db, strategy_id, strategy_update, current_user.id)
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    return strategy


@router.delete("/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a backtest strategy"""
    success = crud.delete_backtest_strategy(db, strategy_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )


# Backtest Run Endpoints
@router.post("/run", response_model=BacktestRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_backtest(
    request: BacktestRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run a backtest (creates strategy if needed, then runs backtest)"""
    from app.services.backtest_service import BacktestService
    backtest_service = BacktestService(db)
    
    # If strategy_id provided, use existing strategy
    if request.strategy_id:
        strategy = crud.get_backtest_strategy(db, request.strategy_id, current_user.id)
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found"
            )
    # If strategy provided, create new strategy
    elif request.strategy:
        strategy = crud.create_backtest_strategy(db, request.strategy, current_user.id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either strategy_id or strategy must be provided"
        )
    
    # Create result record
    result = crud.create_backtest_result(
        db, strategy.id, current_user.id, BacktestStatus.PENDING
    )
    
    # Run backtest (async or sync)
    if request.run_async:
        # Use Celery for async execution
        celery_task = run_backtest_task.delay(strategy.id, result.id)
        
        return BacktestRunResponse(
            result_id=result.id,
            status=BacktestStatus.PENDING,
            message="Backtest started. Check status using the result_id.",
            estimated_completion_time=300  # 5 minutes estimate
        )
    else:
        # Run synchronously (for small backtests)
        import asyncio
        try:
            asyncio.run(backtest_service.run_backtest(strategy.id, result.id))
            db.refresh(result)
            return BacktestRunResponse(
                result_id=result.id,
                status=result.status,
                message="Backtest completed successfully" if result.status == BacktestStatus.COMPLETED else "Backtest failed",
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Backtest failed: {str(e)}"
            )


# Result Endpoints
@router.get("/results", response_model=List[BacktestResultResponse])
def list_results(
    strategy_id: Optional[int] = Query(None, description="Filter by strategy ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all backtest results for the current user"""
    return crud.get_backtest_results(db, current_user.id, strategy_id=strategy_id, skip=skip, limit=limit)


@router.get("/results/{result_id}", response_model=BacktestResultWithTrades)
def get_result(
    result_id: int,
    include_trades: bool = Query(True, description="Include trade details"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific backtest result with optional trades"""
    result = crud.get_backtest_result(db, result_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    # Convert to response model
    result_data = BacktestResultResponse.model_validate(result)
    
    trades = []
    if include_trades:
        trade_models = crud.get_backtest_trades(db, result_id)
        trades = [BacktestTradeResponse.model_validate(trade) for trade in trade_models]
    
    return BacktestResultWithTrades(**result_data.model_dump(), trades=trades)


@router.get("/results/{result_id}/trades", response_model=List[BacktestTradeResponse])
def get_result_trades(
    result_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all trades for a specific backtest result"""
    # Verify result belongs to user
    result = crud.get_backtest_result(db, result_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    
    trades = crud.get_backtest_trades(db, result_id, skip=skip, limit=limit)
    return [BacktestTradeResponse.model_validate(trade) for trade in trades]


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a backtest result"""
    success = crud.delete_backtest_result(db, result_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )

