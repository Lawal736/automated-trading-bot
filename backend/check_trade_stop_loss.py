#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import SessionLocal
from app.models.trading import Trade
from app.models.exchange import ExchangeConnection
from app.trading.exchanges.factory import ExchangeFactory
import asyncio

async def check_trade_stop_loss():
    db = SessionLocal()
    try:
        print("=== TRADE ID 29 STOP LOSS CHECK ===\n")
        
        # Find trade ID 29
        trade = db.query(Trade).filter(Trade.id == 29).first()
        if not trade:
            print("❌ Trade ID 29 not found")
            return
            
        print(f"Trade ID: {trade.id}")
        print(f"Symbol: {trade.symbol}")
        print(f"Side: {trade.side}")
        print(f"Executed Price: {trade.executed_price}")
        print(f"Quantity: {trade.quantity}")
        print(f"User's Stop Loss: {trade.stop_loss}")
        print(f"Exchange Order ID: {trade.exchange_order_id}")
        print(f"Status: {trade.status}")
        print()
        
        # Get exchange connection
        exchange_conn = db.query(ExchangeConnection).filter_by(id=trade.exchange_connection_id).first()
        if not exchange_conn:
            print("❌ Exchange connection not found")
            return
            
        print(f"Exchange: {exchange_conn.exchange_name}")
        print(f"Testnet: {exchange_conn.is_testnet}")
        print()
        
        # Create exchange instance and get precision
        exchange = ExchangeFactory.create_exchange(
            exchange_name=exchange_conn.exchange_name,
            api_key=exchange_conn.api_key,
            api_secret=exchange_conn.api_secret,
            is_testnet=exchange_conn.is_testnet
        )
        
        try:
            # Load markets and get precision/limits
            await exchange.client.load_markets()
            market = exchange.client.market(trade.symbol)
            price_precision = market['precision']['price']
            amount_precision = market['precision']['amount']
            
            print("=== PRECISION VALUES ===")
            print(f"Price Precision: {price_precision}")
            print(f"Amount Precision: {amount_precision}")
            print()
            
            # Calculate stop loss values
            if trade.stop_loss is not None:
                stop_loss_price = trade.stop_loss
                print(f"Using user's stored stop loss: {stop_loss_price}")
            else:
                # Fallback calculation
                if trade.side == 'buy':
                    stop_loss_price = trade.executed_price * 0.98
                else:
                    stop_loss_price = trade.executed_price * 1.02
                print(f"Using calculated stop loss: {stop_loss_price}")
            
            # Apply precision
            stop_price = round(float(stop_loss_price), price_precision)
            rounded_quantity = round(float(trade.quantity), amount_precision)
            
            # Calculate limit price
            side = 'sell' if trade.side == 'buy' else 'buy'
            if side == 'sell':
                limit_price = round(stop_price * 0.999, price_precision)
            else:
                limit_price = round(stop_price * 1.001, price_precision)
            
            print("=== CALCULATED VALUES ===")
            print(f"Original Stop Loss: {stop_loss_price}")
            print(f"Rounded Stop Price: {stop_price}")
            print(f"Original Quantity: {trade.quantity}")
            print(f"Rounded Quantity: {rounded_quantity}")
            print(f"Limit Price: {limit_price}")
            print(f"Stop Loss Side: {side}")
            print()
            
            print("=== ORDER PARAMETERS ===")
            print(f"Symbol: {trade.symbol}")
            print(f"Type: stop_loss_limit")
            print(f"Side: {side}")
            print(f"Amount: {rounded_quantity}")
            print(f"Price: {limit_price}")
            print(f"Stop Price: {stop_price}")
            print(f"Time In Force: GTC")
            
        finally:
            await exchange.close()
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_trade_stop_loss()) 