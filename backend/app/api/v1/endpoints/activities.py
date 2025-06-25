from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.schemas.activity import Activity, ActivityCreate
from app.models.user import User
from app.services import activity_service
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Activity])
def get_activities(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    limit: int = 20
):
    """
    Get recent activities for the current user.
    """
    try:
        activities = activity_service.get_recent_activities(db, current_user, limit)
        return activities
    except Exception as e:
        logger.error(f"Error fetching activities: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch activities. Please try again.",
        )

@router.post("/log", response_model=Activity)
def log_new_activity(
    *,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
    activity_in: ActivityCreate
):
    """
    Log a new activity for the current user.
    """
    try:
        activity = activity_service.log_activity(db=db, user=current_user, activity_in=activity_in)
        return activity
    except Exception as e:
        logger.error(f"Error logging activity: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to log activity. Please try again."
        ) 