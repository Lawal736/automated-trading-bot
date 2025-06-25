from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import models
from app.schemas import backtest as backtest_schemas
from app.api import deps
from app.services.backtest_service import BacktestService
from app.services.exchange_service import ExchangeService

router = APIRouter()

@router.post("", response_model=backtest_schemas.BacktestResult)
def run_backtest(
    *,
    db: Session = Depends(deps.get_db),
    backtest_request: backtest_schemas.BacktestRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Run a backtest for a given strategy.
    """
    exchange_service = ExchangeService(db)
    backtest_service = BacktestService(exchange_service)
    
    try:
        result = backtest_service.run_backtest(request=backtest_request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 