import asyncio
import time
from datetime import datetime, timedelta
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from app.models.trading import Trade, OrderStatus
from app.schemas.activity import ActivityCreate
from app.services.activity_service import ActivityService

logger = logging.getLogger(__name__)

class StopLossTimeoutHandler:
    def __init__(self, exchange, session: Session):
        self.exchange = exchange
        self.session = session
        
    async def create_stop_loss_with_retry(self, trade_order, user_id, exchange_conn, user, activity_service: ActivityService, max_retries=3):
        """
        Create stop loss with proper timeout handling and retry logic
        """
        
        # Generate a unique client order ID for idempotency
        client_order_id = f"SL_{user_id}_{trade_order.symbol.replace('/', '')}_{int(time.time() * 1000)}"
        
        for attempt in range(max_retries):
            logger.info(f"Stop loss creation attempt {attempt + 1}/{max_retries}")
            
            try:
                # First, check if we already have this stop loss order
                existing_order = await self._check_existing_stop_loss(
                    trade_order.symbol, 
                    client_order_id,
                    trade_order.stop_loss,
                    trade_order.amount
                )
                
                if existing_order:
                    logger.info(f"Found existing stop loss order: {existing_order['id']}")
                    return await self._handle_existing_order(existing_order, trade_order, user_id, exchange_conn, user, activity_service)
                
                # If no existing order, create new one
                return await self._create_new_stop_loss(trade_order, user_id, exchange_conn, user, activity_service, client_order_id)
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                
                if attempt < max_retries - 1:
                    # Wait and check if order was created despite timeout
                    await asyncio.sleep(3)
                    
                    # Check if order was created during timeout
                    existing_order = await self._check_existing_stop_loss(
                        trade_order.symbol, 
                        client_order_id,
                        trade_order.stop_loss,
                        trade_order.amount
                    )
                    
                    if existing_order:
                        logger.info("Order was created despite timeout!")
                        return await self._handle_existing_order(existing_order, trade_order, user_id, exchange_conn, user, activity_service)
                    else:
                        logger.info("Order was not created, will retry")
                        continue
                else:
                    logger.error("Final timeout - stop loss creation failed")
                    raise
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"All attempts failed: {e}")
                    raise
        
        raise Exception("Stop loss creation failed after all retries")
    
    def _get_order_id(self, order):
        """
        Extract order ID from either dict or object response
        """
        if isinstance(order, dict):
            return order.get('id') or order.get('orderId')
        else:
            # Handle object response
            return getattr(order, 'id', None) or getattr(order, 'orderId', None)
    
    def _get_order_field(self, order, field):
        """
        Get field from either dict or object response
        """
        if isinstance(order, dict):
            return order.get(field)
        else:
            return getattr(order, field, None)
    
    async def _check_existing_stop_loss(self, symbol, client_order_id, stop_price, amount):
        """
        Check if stop loss order already exists by searching recent orders
        """
        try:
            # Method 1: Try to find by client order ID (if exchange supports it)
            try:
                open_orders = await self.exchange.client.fetch_open_orders(symbol)
                for order in open_orders:
                    client_id = self._get_order_field(order, 'clientOrderId')
                    order_type = self._get_order_field(order, 'type')
                    stop_price_field = self._get_order_field(order, 'stopPrice')
                    amount_field = self._get_order_field(order, 'amount')
                    
                    if (client_id == client_order_id or 
                        (order_type in ['stop_loss_limit', 'stop-limit', 'STOP_LOSS_LIMIT'] and
                         stop_price_field and abs(float(stop_price_field) - float(stop_price)) < 0.0001 and
                         amount_field and abs(float(amount_field) - float(amount)) < 0.0001)):
                        return order
            except:
                pass
                
            # Method 2: Check recent orders (last 5 minutes)
            try:
                since = int((datetime.now() - timedelta(minutes=5)).timestamp() * 1000)
                recent_orders = await self.exchange.client.fetch_orders(symbol, since=since, limit=50)
                
                for order in recent_orders:
                    client_id = self._get_order_field(order, 'clientOrderId')
                    order_type = self._get_order_field(order, 'type')
                    order_status = self._get_order_field(order, 'status')
                    stop_price_field = self._get_order_field(order, 'stopPrice')
                    amount_field = self._get_order_field(order, 'amount')
                    
                    if (client_id == client_order_id or
                        (order_type in ['stop_loss_limit', 'stop-limit', 'STOP_LOSS_LIMIT'] and
                         order_status in ['open', 'closed'] and
                         stop_price_field and abs(float(stop_price_field) - float(stop_price)) < 0.0001 and
                         amount_field and abs(float(amount_field) - float(amount)) < 0.0001)):
                        return order
            except:
                pass
                
            return None
            
        except Exception as e:
            logger.warning(f"Error checking existing orders: {e}")
            return None
    
    async def _create_new_stop_loss(self, trade_order, user_id, exchange_conn, user, activity_service: ActivityService, client_order_id):
        """
        Create new stop loss order with timeout protection
        """
        try:
            # Get market info and calculate prices
            await self.exchange.client.load_markets()
            market = self.exchange.client.market(trade_order.symbol)
            
            price_precision = market['precision']['price']
            amount_precision = market['precision']['amount']
            
            stop_side = "sell" if trade_order.side == "buy" else "buy"
            stop_price = round(float(trade_order.stop_loss), price_precision)
            rounded_quantity = round(float(trade_order.amount), amount_precision)
            
            if stop_side == "sell":
                limit_price = round(stop_price * 0.999, price_precision)
            else:
                limit_price = round(stop_price * 1.001, price_precision)
            
            # Create pending record
            pending_stop_loss = Trade(
                user_id=user_id,
                exchange_connection_id=exchange_conn.id,
                symbol=trade_order.symbol,
                trade_type="STOP_LOSS",
                order_type="stop-limit",
                side=stop_side,
                quantity=rounded_quantity,
                price=Decimal(str(limit_price)),
                status="pending",
                client_order_id=client_order_id  # Store for tracking
            )
            self.session.add(pending_stop_loss)
            self.session.commit()
            
            # Create order with timeout
            order_params = {
                "stopPrice": stop_price,
                "timeInForce": "GTC",
                "newClientOrderId": client_order_id  # Binance parameter for idempotency
            }
            
            logger.info(f"Creating stop loss order with client ID: {client_order_id}")
            
            # Try different order types for different exchanges/modes
            order_type_variants = [
                "STOP_LOSS_LIMIT",      # Binance Spot
                "stop_loss_limit",      # Some exchanges
                "STOP",                 # Alternative
                "stop-limit",           # CCXT standard
                "stopLimit"             # Some exchanges
            ]
            
            stop_loss_order = None
            last_error = None
            
            for order_type in order_type_variants:
                try:
                    logger.info(f"Trying order type: {order_type}")
                    
                    # Set timeout for the order creation
                    stop_loss_order = await asyncio.wait_for(
                        self.exchange.create_order(
                            symbol=trade_order.symbol,
                            order_type=order_type,
                            side=stop_side,
                            amount=rounded_quantity,
                            price=limit_price,
                            params=order_params
                        ),
                        timeout=10.0  # 10 second timeout
                    )
                    
                    logger.info(f"Success with order type: {order_type}")
                    break
                    
                except asyncio.TimeoutError:
                    # Timeout - don't try other variants, handle timeout logic
                    raise
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    if "order type" in error_msg or "invalid" in error_msg or "not a valid" in error_msg:
                        logger.warning(f"Order type {order_type} not supported: {e}")
                        continue
                    else:
                        # If it's not an order type error, don't try other variants
                        raise e
            
            if stop_loss_order is None:
                raise Exception(f"All order types failed. Last error: {last_error}")
            
            # Handle both dict and object responses
            order_id = self._get_order_id(stop_loss_order)
            
            # Update record with success
            pending_stop_loss.status = OrderStatus.OPEN.value
            pending_stop_loss.exchange_order_id = str(order_id)
            pending_stop_loss.executed_at = datetime.utcnow()
            self.session.commit()
            
            logger.info(f"Stop loss created successfully: {order_id}")
            
            # Log activity
            if user:
                activity_data = ActivityCreate(
                    type="STOP_LOSS_ORDER",
                    description=f"Stop loss order created for {trade_order.symbol} at {stop_price} (ID: {order_id})",
                    amount=rounded_quantity
                )
                activity_service.log_activity(self.session, user, activity_data)
            
            return stop_loss_order
            
        except asyncio.TimeoutError:
            logger.warning("Stop loss creation timed out")
            # Don't update status yet - we need to check if it was created
            raise
        except Exception as e:
            # Update record with failure
            if 'pending_stop_loss' in locals():
                pending_stop_loss.status = OrderStatus.REJECTED.value
                pending_stop_loss.error_message = str(e)[:500]
                self.session.commit()
            raise
    
    async def _handle_existing_order(self, existing_order, trade_order, user_id, exchange_conn, user, activity_service: ActivityService):
        """
        Handle case where order already exists
        """
        try:
            # Find or create the trade record
            pending_stop_loss = self.session.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.symbol == trade_order.symbol,
                Trade.trade_type == "STOP_LOSS",
                Trade.status == "pending"
            ).first()
            
            if not pending_stop_loss:
                # Create record for existing order
                stop_side = "sell" if trade_order.side == "buy" else "buy"
                pending_stop_loss = Trade(
                    user_id=user_id,
                    exchange_connection_id=exchange_conn.id,
                    symbol=trade_order.symbol,
                    trade_type="STOP_LOSS",
                    order_type="stop-limit",
                    side=stop_side,
                    quantity=float(self._get_order_field(existing_order, 'amount')),
                    price=Decimal(str(self._get_order_field(existing_order, 'price'))),
                    status="pending"
                )
                self.session.add(pending_stop_loss)
            
            # Update with existing order info
            order_id = self._get_order_id(existing_order)
            pending_stop_loss.status = OrderStatus.OPEN.value
            pending_stop_loss.exchange_order_id = str(order_id)
            pending_stop_loss.executed_at = datetime.utcnow()
            self.session.commit()
            
            logger.info(f"Linked existing stop loss order: {order_id}")
            
            return existing_order
            
        except Exception as e:
            logger.error(f"Error handling existing order: {e}")
            raise

async def create_stop_loss_safe(trade_order, user_id, exchange_conn, user, activity_service: ActivityService, exchange, session: Session):
    """
    Safe stop loss creation with timeout handling
    """
    if not trade_order.stop_loss:
        return None
    
    try:
        handler = StopLossTimeoutHandler(exchange, session)
        stop_loss_order = await handler.create_stop_loss_with_retry(
            trade_order, user_id, exchange_conn, user, activity_service
        )
        return stop_loss_order
        
    except Exception as e:
        logger.error(f"Stop loss creation failed completely: {e}")
        
        # Log failure activity
        if user:
            activity_data = ActivityCreate(
                type="STOP_LOSS_ORDER_FAILED",
                description=f"Failed to create stop loss for {trade_order.symbol}: {str(e)[:100]}",
                amount=trade_order.amount
            )
            activity_service.log_activity(session, user, activity_data)
        
        return None 