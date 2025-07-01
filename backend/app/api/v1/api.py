from fastapi import APIRouter

from app.api.v1.endpoints import auth, exchanges, users, bots, activities, portfolio, reports, balance, backtest, admin, trades, cassava_data, stop_loss, automated_cassava, grid_trading

api_router = APIRouter()

# Health check endpoint for API
@api_router.get("/health")
def health_check():
    return {"status": "healthy"}

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(exchanges.router, prefix="/exchanges", tags=["exchanges"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(bots.router, prefix="/bots", tags=["bots"])
api_router.include_router(activities.router, prefix="/activities", tags=["activities"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(balance.router, prefix="/balance", tags=["balance"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(trades.router, prefix="/trades", tags=["trades"])
api_router.include_router(cassava_data.router, prefix="/cassava-data", tags=["cassava-data"])
api_router.include_router(stop_loss.router, prefix="/stop-loss", tags=["stop-loss"])
api_router.include_router(automated_cassava.router, prefix="/automated-cassava", tags=["automated-cassava"])
api_router.include_router(grid_trading.router, prefix="/grid-trading", tags=["grid-trading"])