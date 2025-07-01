from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime

from .... import models, schemas
from ....api import deps
from ....services import portfolio_service
from app.schemas.position import Position
from app.models.trading import Position as PositionModel
from app.services.position_service import PositionService
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=schemas.portfolio.Portfolio)
def read_portfolio(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve portfolio data for the current user (basic version).
    """
    portfolio = portfolio_service.get_portfolio_data(db=db, user_id=current_user.id)
    return portfolio


@router.get("/realtime", response_model=schemas.portfolio.Portfolio)
async def read_portfolio_realtime(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve real-time portfolio data with live position updates.
    This endpoint updates position prices from exchanges before returning data.
    """
    try:
        portfolio = await portfolio_service.get_portfolio_data_realtime(db=db, user_id=current_user.id)
        return portfolio
    except Exception as e:
        logger.error(f"Error getting real-time portfolio for user {current_user.id}: {e}")
        # Fallback to basic portfolio
        portfolio = portfolio_service.get_portfolio_data(db=db, user_id=current_user.id)
        return portfolio


@router.get("/positions/", response_model=List[Position])
def get_open_positions(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get all open positions for the current user.
    """
    positions = db.query(PositionModel).filter_by(user_id=current_user.id, is_open=True).all()
    return positions


@router.get("/positions/detailed")
async def get_detailed_positions(
    include_closed: bool = False,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get detailed position information with P&L breakdown, duration, and risk metrics.
    """
    try:
        position_service = PositionService()
        detailed_positions = position_service.get_detailed_positions(
            db, current_user.id, include_closed
        )
        
        return {
            "positions": detailed_positions,
            "total_positions": len(detailed_positions),
            "open_positions": len([p for p in detailed_positions if p['is_open']]),
            "closed_positions": len([p for p in detailed_positions if not p['is_open']]),
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Error getting detailed positions for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve detailed positions")


@router.post("/positions/{position_id}/update-price")
async def update_position_price(
    position_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Update the current price for a specific position.
    """
    try:
        # Verify position belongs to user
        position = db.query(PositionModel).filter(
            PositionModel.id == position_id,
            PositionModel.user_id == current_user.id
        ).first()
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        position_service = PositionService()
        update_result = await position_service.update_position_prices(db, current_user.id)
        
        # Find the specific position in the update results
        position_update = next(
            (p for p in update_result.get('position_updates', []) if p['position_id'] == position_id),
            None
        )
        
        if position_update:
            return {
                "success": True,
                "position_update": position_update,
                "message": f"Position {position_id} price updated successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Position {position_id} was not updated"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating position {position_id} for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update position price")


@router.get("/positions/{position_id}/risk")
async def get_position_risk_metrics(
    position_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get risk metrics for a specific position.
    """
    try:
        # Verify position belongs to user
        position = db.query(PositionModel).filter(
            PositionModel.id == position_id,
            PositionModel.user_id == current_user.id
        ).first()
        
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        
        position_service = PositionService()
        risk_metrics = position_service.get_position_risk_metrics(db, position_id)
        
        if 'error' in risk_metrics:
            raise HTTPException(status_code=400, detail=risk_metrics['error'])
        
        return risk_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting risk metrics for position {position_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve risk metrics")


@router.get("/pnl/summary")
async def get_pnl_summary(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Get comprehensive P&L summary for the user's portfolio.
    """
    try:
        position_service = PositionService()
        pnl_summary = position_service.get_portfolio_pnl_summary(db, current_user.id)
        
        return {
            "pnl_summary": pnl_summary,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"Error getting P&L summary for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve P&L summary")


@router.post("/positions/update-all-prices")
async def update_all_position_prices(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Dict[str, Any]:
    """
    Update current prices for all open positions of the user.
    """
    try:
        position_service = PositionService()
        update_result = await position_service.update_position_prices(db, current_user.id)
        
        return {
            "success": True,
            "updated_positions": update_result.get('updated_positions', 0),
            "total_unrealized_pnl": update_result.get('total_unrealized_pnl', 0.0),
            "position_updates": update_result.get('position_updates', []),
            "timestamp": update_result.get('timestamp'),
            "message": f"Updated {update_result.get('updated_positions', 0)} positions"
        }
        
    except Exception as e:
        logger.error(f"Error updating all positions for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update position prices") 