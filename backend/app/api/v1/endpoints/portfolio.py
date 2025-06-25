from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from .... import models, schemas
from ....api import deps
from ....services import portfolio_service
from app.schemas.position import Position
from app.models.trading import Position as PositionModel

router = APIRouter()


@router.get("/", response_model=schemas.portfolio.Portfolio)
def read_portfolio(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve portfolio data for the current user.
    """
    portfolio = portfolio_service.get_portfolio_data(db=db, user_id=current_user.id)
    return portfolio

@router.get("/positions/", response_model=List[Position])
def get_open_positions(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get all open positions for the current user.
    """
    positions = db.query(PositionModel).filter_by(user_id=current_user.id, is_open=True).all()
    return positions 