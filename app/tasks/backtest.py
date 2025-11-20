from app.tasks.celery_app import celery_app
from app.core.database import get_db_session
from app.services.backtest_service import BacktestService
from app.models.backtest import BacktestStatus
from app.crud import backtest as crud
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="backtest.run_backtest")
def run_backtest_task(self, strategy_id: int, result_id: int):
    """
    Celery task to run a backtest asynchronously.
    This task creates its own database session and handles the async backtest execution.
    """
    db = get_db_session()
    try:
        # Update task status
        self.update_state(state='PROGRESS', meta={'status': 'Starting backtest...'})
        
        # Create BacktestService with new database session
        backtest_service = BacktestService(db)
        
        # Run the async backtest - Celery tasks are sync, so we need to run async code
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(backtest_service.run_backtest(strategy_id, result_id))
        finally:
            loop.close()
        
        return {
            'status': 'completed',
            'result_id': result_id,
            'strategy_id': strategy_id
        }
    except Exception as e:
        # Update result with error
        try:
            crud.update_backtest_result(
                db, result_id, {
                    "status": BacktestStatus.FAILED,
                    "error_message": str(e),
                }
            )
            db.commit()
        except Exception as db_error:
            logger.error(f"Error updating backtest result: {db_error}")
        
        # Re-raise to mark task as failed (don't retry backtests automatically)
        raise
    finally:
        db.close()

