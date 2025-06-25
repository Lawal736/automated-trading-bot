from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api import deps
from app.schemas.user import User
from app.models.user import User as UserModel
from app.services import user_service

router = APIRouter()


@router.get("/me", response_model=User)
async def read_users_me(current_user: UserModel = Depends(deps.get_current_active_user)):
    """
    Get current user.
    """
    return current_user


@router.get("/{user_id}", response_model=User)
async def read_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: UserModel = Depends(deps.get_current_active_user),
):
    """
    Get a specific user by id.
    """
    user = await user_service.get_user_by_id(db, user_id=user_id)
    if user == current_user:
        return user
    if not current_user.role == "admin": # Or some other role check
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return user 