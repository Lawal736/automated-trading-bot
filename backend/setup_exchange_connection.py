#!/usr/bin/env python3
"""
Script to set up exchange connection in trading service
"""

from app.core.database import get_db
from app.models.exchange import ExchangeConnection
from app.trading.trading_service import trading_service
import asyncio

def setup_exchange_connection():
    """Set up exchange connection in trading service"""
    db = next(get_db())
    
    try:
        # Get the first exchange connection
        connection = db.query(ExchangeConnection).first()
        if not connection:
            print("No exchange connection found in database")
            return
        
        print(f"Found exchange connection: {connection.exchange_name} (ID: {connection.id})")
        
        # Set up asyncio loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Add exchange connection to trading service
            success = loop.run_until_complete(trading_service.add_exchange_connection(connection))
            if success:
                print(f"Successfully added exchange connection {connection.exchange_name} to trading service")
                
                # Test the connection
                status = loop.run_until_complete(trading_service.get_connection_status())
                print(f"Connection status: {status}")
            else:
                print(f"Failed to add exchange connection {connection.exchange_name}")
                
        finally:
            loop.close()
            
    except Exception as e:
        print(f"Error setting up exchange connection: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_exchange_connection() 