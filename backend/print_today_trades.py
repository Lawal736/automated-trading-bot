from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.trading import Trade
from datetime import datetime, timedelta

def main():
    db: Session = SessionLocal()
    try:
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        trades = db.query(Trade).filter(
            Trade.created_at >= today,
            Trade.created_at < tomorrow
        ).all()
        print(f"Trades for {today} (UTC):")
        for trade in trades:
            print(f"ID: {trade.id}, Symbol: {trade.symbol}, Price: {trade.executed_price}, Status: {trade.status}, OrderID: {trade.exchange_order_id}, Created: {trade.created_at}")
    finally:
        db.close()

if __name__ == "__main__":
    main() 