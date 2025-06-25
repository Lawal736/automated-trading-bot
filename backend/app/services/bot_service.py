from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.models.bot import Bot
from app.schemas.bot import BotCreate, BotUpdate
from app.core.logging import get_logger
from typing import Any, Dict, Optional, Union, List
from sqlalchemy.orm import Session

logger = get_logger(__name__)

async def create_bot(db: AsyncSession, *, user: User, bot_in: BotCreate) -> Bot:
    """
    Creates a new trading bot for a user.
    """
    
    bot_obj = Bot(
        user_id=user.id,
        exchange_connection_id=bot_in.exchange_connection_id,
        name=bot_in.name,
        strategy_name=bot_in.strategy_name,
        description=bot_in.description,
        trade_type=bot_in.trade_type,
        direction=bot_in.direction,
        leverage=bot_in.leverage,
        initial_balance=bot_in.initial_balance,
        current_balance=bot_in.initial_balance, # Starts same as initial
        stop_loss_percent=bot_in.stop_loss_percent,
        trading_pairs=bot_in.trading_pairs, # Store as comma-separated string
        is_active=False, # Bots are not active by default
        status="stopped",
        celery_task_id=None
    )
    
    db.add(bot_obj)
    await db.commit()
    await db.refresh(bot_obj)
    
    logger.info("Bot created", bot_id=bot_obj.id, user_id=user.id, name=bot_obj.name)
    
    return bot_obj

async def get_bots_by_user(
    db: AsyncSession, 
    *, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> list[Bot]:
    """
    Retrieve bots for a specific user with pagination.
    """
    query = select(Bot).where(Bot.user_id == user_id).offset(skip).limit(limit)
    result = await db.execute(query)
    bots = result.scalars().all()
    
    logger.info("Bots retrieved", user_id=user_id, count=len(bots))
    
    return bots

async def get_bot_by_id(db: AsyncSession, *, bot_id: int, user_id: int) -> Bot | None:
    """
    Retrieve a single bot by its ID, ensuring it belongs to the user.
    """
    query = select(Bot).where(Bot.id == bot_id, Bot.user_id == user_id)
    result = await db.execute(query)
    bot = result.scalars().first()
    
    if bot:
        logger.info("Bot retrieved", bot_id=bot_id, user_id=user_id)
    else:
        logger.warning("Bot not found or access denied", bot_id=bot_id, user_id=user_id)
        
    return bot 

class CRUDBot:
    def create_with_owner(
        self, db: Session, *, obj_in: BotCreate, owner_id: int
    ) -> Bot:
        """Create a new bot for a specific user, including advanced settings."""
        try:
            # Create the Bot object with all fields from the schema
            bot_obj = Bot(
                user_id=owner_id,
                name=obj_in.name,
                strategy_name=obj_in.strategy_name,
                description=obj_in.description,
                exchange_connection_id=obj_in.exchange_connection_id,
                
                # Trading Configuration
                trading_pairs=obj_in.trading_pairs,
                trade_type=obj_in.trade_type,
                direction=obj_in.direction,
                leverage=obj_in.leverage,
                initial_balance=obj_in.initial_balance,
                current_balance=obj_in.initial_balance,

                # Risk Management & Limits
                max_trades_per_day=obj_in.max_trades_per_day,
                min_balance_threshold=obj_in.min_balance_threshold,
                max_daily_loss=obj_in.max_daily_loss,
                max_position_size_percent=obj_in.max_position_size_percent,
                trade_interval_seconds=obj_in.trade_interval_seconds,

                # Advanced Stop Loss Configuration
                stop_loss_type=obj_in.stop_loss_type,
                stop_loss_percentage=obj_in.stop_loss_percentage,
                stop_loss_timeframe=obj_in.stop_loss_timeframe,
                stop_loss_ema_period=obj_in.stop_loss_ema_period,
                stop_loss_atr_period=obj_in.stop_loss_atr_period,
                stop_loss_atr_multiplier=obj_in.stop_loss_atr_multiplier,
                stop_loss_support_lookback=obj_in.stop_loss_support_lookback,
                
                # Default status
                is_active=False,
                celery_task_id=None
            )
            
            db.add(bot_obj)
            db.commit()
            db.refresh(bot_obj)
            
            logger.info("Bot created with advanced settings", bot_id=bot_obj.id, user_id=owner_id)
            return bot_obj
        except Exception as e:
            logger.error(f"Error creating bot with advanced settings: {str(e)}")
            db.rollback()
            raise

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ) -> List[Bot]:
        """Get all bots for a specific user"""
        try:
            bots = db.query(Bot).filter(Bot.user_id == owner_id).order_by(Bot.id).offset(skip).limit(limit).all()
            logger.info(f"Retrieved {len(bots)} bots", user_id=owner_id)
            return bots
        except Exception as e:
            logger.error(f"Error fetching bots: {str(e)}")
            raise

    def get_by_owner(
        self, db: Session, *, id: int, owner_id: int
    ) -> Optional[Bot]:
        """Get a specific bot by ID for a user"""
        try:
            bot = db.query(Bot).filter(Bot.id == id, Bot.user_id == owner_id).first()
            if bot:
                logger.info("Bot retrieved", bot_id=id, user_id=owner_id)
            else:
                logger.warning("Bot not found or access denied", bot_id=id, user_id=owner_id)
            return bot
        except Exception as e:
            logger.error(f"Error fetching bot: {str(e)}")
            raise

    def update(
        self, db: Session, *, db_obj: Bot, obj_in: Union[BotUpdate, Dict[str, Any]]
    ) -> Bot:
        """
        Update a bot with specific fields.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logger.info(f"Bot {db_obj.id} updated successfully.")
        return db_obj

    def remove(self, *, db: Session, id: int) -> Bot:
        """Delete a bot"""
        try:
            obj = db.query(Bot).get(id)
            db.delete(obj)
            db.commit()
            return obj
        except Exception as e:
            logger.error(f"Error deleting bot: {str(e)}")
            db.rollback()
            raise

    def start_bot(self, db: Session, bot: Bot) -> Dict[str, Any]:
        """
        Start a trading bot by scheduling it with Celery.
        This method abstracts the Celery operations from the API layer.
        """
        try:
            # Import here to avoid circular imports and make the service optional
            from app.core.celery import celery_app
            from app.tasks.trading_tasks import run_trading_bot_strategy
            
            if bot.is_active:
                logger.warning(f"Attempted to start already running bot {bot.id}")
                return { "success": False, "message": "Bot is already running" }

            # Update bot status first
            bot.is_active = True
            db.commit()
            
            # Call the task directly (this will execute immediately)
            task_result = run_trading_bot_strategy.delay(bot.id)
            bot.celery_task_id = task_result.id
            db.commit()
            
            logger.info(f"Bot {bot.id} started successfully", task_id=task_result.id)
            
            return {
                "success": True,
                "message": "Bot started successfully",
                "task_id": bot.celery_task_id
            }
        except ImportError:
            logger.warning("Celery not available, bot scheduling disabled")
            bot.is_active = False # Rollback status
            db.commit()
            return { "success": False, "message": "Bot scheduling service unavailable" }
        except Exception as e:
            logger.error(f"Failed to start bot {bot.id}: {str(e)}")
            # Rollback the bot status if task scheduling failed
            bot.is_active = False
            bot.celery_task_id = None
            db.commit()
            return { "success": False, "message": f"Failed to start bot: {str(e)}" }

    def stop_bot(self, db: Session, bot: Bot) -> Dict[str, Any]:
        """
        Stop a trading bot by revoking its Celery task.
        This is made more robust to ensure the bot can be stopped in the DB
        even if Celery is unreachable.
        """
        if not bot.is_active:
            logger.warning(f"Attempted to stop already stopped bot {bot.id}")
            return {"success": False, "message": "Bot is not running"}

        task_id = bot.celery_task_id
        if task_id:
            try:
                from app.core.celery import celery_app
                celery_app.control.revoke(task_id, terminate=True)
                logger.info(f"Successfully sent revoke command for Celery task {task_id} for bot {bot.id}")
            except Exception as e:
                logger.error(f"Failed to revoke Celery task {task_id} for bot {bot.id}: {e}. The bot will be marked as stopped regardless.")

        # Always update the bot's status in the database to reflect the user's intent.
        bot.is_active = False
        bot.celery_task_id = None
        db.commit()
        db.refresh(bot)
        
        logger.info(f"Bot {bot.id} marked as stopped in the database.")
        
        return {
            "success": True,
            "message": "Bot stop command issued successfully."
        }

# Create a singleton instance
bot_service = CRUDBot() 