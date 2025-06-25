from sqlalchemy.orm import Session
from app.models.activity import Activity
from app.models.user import User
from app.schemas.activity import ActivityCreate
from app.core.logging import get_logger
from app.services.base import ServiceBase
from sqlalchemy import func
from datetime import datetime, time
from typing import List, Dict, Any

logger = get_logger(__name__)

class ActivityService(ServiceBase[Activity, ActivityCreate, ActivityCreate]):
    def get_daily_trade_stats(self, db: Session, bot_id: int) -> Dict[str, Any]:
        """
        Calculates the number of trades and profit/loss for a bot for the current day.
        """
        today_start = datetime.combine(datetime.utcnow().date(), time.min)
        
        try:
            # Count trades
            trade_count = db.query(func.count(Activity.id))\
                .filter(
                    Activity.bot_id == bot_id,
                    Activity.type == 'trade',
                    Activity.timestamp >= today_start
                ).scalar() or 0

            # Sum PnL
            daily_pnl = db.query(func.sum(Activity.pnl))\
                .filter(
                    Activity.bot_id == bot_id,
                    Activity.type == 'trade',
                    Activity.timestamp >= today_start
                ).scalar() or 0.0

            return {"trade_count": trade_count, "daily_pnl": daily_pnl}
        except Exception as e:
            logger.error(f"Error calculating daily stats for bot {bot_id}: {e}")
            return {"trade_count": 0, "daily_pnl": 0.0}

    def log_activity(self, db: Session, user: User, activity_in: ActivityCreate) -> Activity:
        try:
            activity = Activity(
                user_id=user.id,
                type=activity_in.type,
                description=activity_in.description,
                amount=activity_in.amount
            )
            db.add(activity)
            db.commit()
            db.refresh(activity)
            
            logger.info(f"Activity logged", user_id=user.id, activity_type=activity_in.type)
            return activity
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
            db.rollback()
            raise

    def get_all_activities_by_user_id(self, db: Session, user_id: int) -> List[Activity]:
        try:
            activities = db.query(Activity).filter(Activity.user_id == user_id).all()
            logger.info(f"Retrieved {len(activities)} activities for user {user_id}")
            return activities
        except Exception as e:
            logger.error(f"Error fetching all activities for user {user_id}: {str(e)}")
            raise

    def get_recent_activities(self, db: Session, user: User, limit: int = 20) -> List[Activity]:
        try:
            activities = db.query(Activity)\
                .filter(Activity.user_id == user.id)\
                .order_by(Activity.timestamp.desc())\
                .limit(limit)\
                .all()
            
            logger.info(f"Retrieved {len(activities)} activities", user_id=user.id)
            return activities
        except Exception as e:
            logger.error(f"Error fetching activities: {str(e)}")
            raise

# Create service instance
activity_service = ActivityService(Activity) 