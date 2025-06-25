from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.schemas import bot as bot_schemas
from app.api import deps
from app.services import bot_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/", response_model=bot_schemas.Bot)
def create_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_in: bot_schemas.BotCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> models.Bot:
    """
    Create new bot.
    """
    bot = bot_service.create_with_owner(db=db, obj_in=bot_in, owner_id=current_user.id)
    return bot


@router.get("/", response_model=List[bot_schemas.Bot])
def read_bots(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> List[models.Bot]:
    """
    Retrieve user's bots.
    """
    bots = bot_service.get_multi_by_owner(db=db, owner_id=current_user.id, skip=skip, limit=limit)
    return bots


@router.get("/{bot_id}", response_model=bot_schemas.Bot)
def read_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> models.Bot:
    """
    Get bot by ID.
    """
    bot = bot_service.get_by_owner(db=db, id=bot_id, owner_id=current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot


@router.put("/{bot_id}", response_model=bot_schemas.Bot)
def update_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    bot_in: bot_schemas.BotUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> models.Bot:
    """
    Update bot.
    """
    bot = bot_service.get_by_owner(db=db, id=bot_id, owner_id=current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot = bot_service.update(db=db, db_obj=bot, obj_in=bot_in)
    return bot


@router.delete("/{bot_id}")
def delete_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Delete bot.
    """
    bot = bot_service.get_by_owner(db=db, id=bot_id, owner_id=current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    bot_service.remove(db=db, id=bot_id)
    return {"ok": True}


@router.post("/{bot_id}/start")
def start_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Start a trading bot.
    """
    bot = bot_service.get_by_owner(db=db, id=bot_id, owner_id=current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    result = bot_service.start_bot(db=db, bot=bot)
    
    if not result["success"]:
        if "Celery service not available" in result.get("error", ""):
            raise HTTPException(status_code=503, detail="Bot scheduling service unavailable")
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    
    return {"message": result["message"], "task_id": result.get("task_id")}


@router.post("/{bot_id}/stop")
def stop_bot(
    *,
    db: Session = Depends(deps.get_db),
    bot_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Stop a trading bot.
    """
    bot = bot_service.get_by_owner(db=db, id=bot_id, owner_id=current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    result = bot_service.stop_bot(db=db, bot=bot)
    
    if not result["success"]:
        if "Celery service not available" in result.get("error", ""):
            raise HTTPException(status_code=503, detail="Bot scheduling service unavailable")
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    
    return {"message": result["message"]} 