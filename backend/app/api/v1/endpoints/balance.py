from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Any

from app.api import deps
from app.models.user import User
from app.services import exchange_service

router = APIRouter()


@router.get("/", response_model=Any)
def read_exchange_balance(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve total balance from all connected exchanges for the current user.
    """
    balance = exchange_service.get_total_balance(db=db, user_id=current_user.id)
    return balance