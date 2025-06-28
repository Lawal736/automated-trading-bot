from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.cassava_data_service import CassavaDataService
from app.schemas.cassava_trend import CassavaTrendDataResponse, CassavaTrendDataFilter
from app.tasks.cassava_data_tasks import backfill_cassava_trend_data
import logging
import traceback
from urllib.parse import unquote

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/cassava-trend-data", response_model=CassavaTrendDataResponse)
async def get_cassava_trend_data(
    symbol: Optional[str] = Query(None, description="Filter by trading pair"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    trading_condition: Optional[str] = Query(None, description="Filter by trading condition (BUY/SHORT/HOLD)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get Cassava trend data with filtering and pagination"""
    
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # URL-decode the symbol if provided
        if symbol:
            symbol = unquote(symbol)
        
        # Convert date strings to datetime objects
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
        
        cassava_service = CassavaDataService(db)
        
        result = cassava_service.get_cassava_data(
            symbol=symbol,
            start_date=start_datetime,
            end_date=end_datetime,
            trading_condition=trading_condition,
            page=page,
            size=size
        )
        
        return CassavaTrendDataResponse(**result)
        
    except Exception as e:
        logger.error(f"Error getting Cassava trend data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/cassava-trend-data/symbols")
async def get_trading_symbols(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of trading symbols for Cassava strategy"""
    
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        cassava_service = CassavaDataService(db)
        symbols = cassava_service.get_trading_pairs()
        
        return {"symbols": symbols}
        
    except Exception as e:
        logger.error(f"Error getting trading symbols: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/cassava-trend-data/backfill")
async def trigger_backfill(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger backfill of Cassava trend data"""
    
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        # Trigger the backfill task
        task = backfill_cassava_trend_data.delay(start_date, end_date)
        
        return {
            "message": "Backfill task started",
            "task_id": task.id,
            "start_date": start_date,
            "end_date": end_date
        }
        
    except Exception as e:
        logger.error(f"Error triggering backfill: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cassava-trend-data/export")
async def export_cassava_data(
    symbol: Optional[str] = Query(None, description="Filter by trading pair"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    trading_condition: Optional[str] = Query(None, description="Filter by trading condition"),
    format: str = Query("csv", description="Export format (csv/excel)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export Cassava trend data to CSV or Excel"""
    
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        cassava_service = CassavaDataService(db)
        
        # Get all data (no pagination for export)
        result = cassava_service.get_cassava_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            trading_condition=trading_condition,
            page=1,
            size=10000  # Large size to get all data
        )
        
        # Convert to export format
        if format.lower() == "csv":
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                "Date", "Symbol", "EMA_10", "EMA_8", "EMA_20", "EMA_15", 
                "EMA_25", "EMA_5", "DI_Plus", "Top_Fractal", "Trading_Condition"
            ])
            
            # Write data
            for item in result["data"]:
                writer.writerow([
                    item.date.strftime("%Y-%m-%d"),
                    item.symbol,
                    item.ema_10,
                    item.ema_8,
                    item.ema_20,
                    item.ema_15,
                    item.ema_25,
                    item.ema_5,
                    item.di_plus,
                    item.top_fractal or "",
                    item.trading_condition
                ])
            
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=cassava_trend_data.csv"}
            )
            
        elif format.lower() == "excel":
            import pandas as pd
            import io
            
            # Convert to DataFrame
            data = []
            for item in result["data"]:
                data.append({
                    "Date": item.date.strftime("%Y-%m-%d"),
                    "Symbol": item.symbol,
                    "EMA_10": item.ema_10,
                    "EMA_8": item.ema_8,
                    "EMA_20": item.ema_20,
                    "EMA_15": item.ema_15,
                    "EMA_25": item.ema_25,
                    "EMA_5": item.ema_5,
                    "DI_Plus": item.di_plus,
                    "Top_Fractal": item.top_fractal,
                    "Trading_Condition": item.trading_condition
                })
            
            df = pd.DataFrame(data)
            
            # Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Cassava Trend Data', index=False)
            
            output.seek(0)
            
            from fastapi.responses import Response
            return Response(
                content=output.getvalue(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=cassava_trend_data.xlsx"}
            )
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported format. Use 'csv' or 'excel'")
        
    except Exception as e:
        logger.error(f"Error exporting Cassava data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") 