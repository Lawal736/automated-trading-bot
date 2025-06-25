from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from collections import defaultdict

from .. import models
from ..schemas.report import Report, DailyPnl, StrategyPerformance
from ..services import activity_service

def get_full_report(db: Session, *, user_id: int) -> Report:
    """
    Generates a full performance report for a given user.
    """
    activities = activity_service.get_all_activities_by_user_id(db=db, user_id=user_id)
    
    # --- General Stats ---
    trades_with_pnl = [a for a in activities if a.pnl is not None]
    total_trades = len(trades_with_pnl)
    winning_trades = [a for a in trades_with_pnl if a.pnl > 0]
    losing_trades = [a for a in trades_with_pnl if a.pnl < 0]
    
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    
    win_loss_ratio = win_count / total_trades if total_trades > 0 else 0
    total_pnl = sum(a.pnl for a in trades_with_pnl)
    
    avg_profit = sum(a.pnl for a in winning_trades) / win_count if win_count > 0 else 0
    avg_loss = sum(a.pnl for a in losing_trades) / loss_count if loss_count > 0 else 0

    # --- Daily PnL ---
    daily_pnl_map = defaultdict(float)
    for activity in trades_with_pnl:
        day = activity.timestamp.date()
        daily_pnl_map[day] += activity.pnl
        
    daily_pnl_data = [DailyPnl(day=day, pnl=pnl) for day, pnl in sorted(daily_pnl_map.items())]

    # --- Strategy Performance ---
    strategy_map = defaultdict(lambda: {'pnl': 0.0, 'trades': 0, 'wins': 0})
    
    # We need bot information to get strategy name
    bot_ids = {a.bot_id for a in activities if a.bot_id}
    bots = db.query(models.Bot).filter(models.Bot.id.in_(bot_ids)).all()
    bot_strategy_map = {bot.id: bot.strategy_name for bot in bots}

    for activity in trades_with_pnl:
        if activity.bot_id in bot_strategy_map:
            strategy_name = bot_strategy_map[activity.bot_id]
            strategy_map[strategy_name]['pnl'] += activity.pnl
            strategy_map[strategy_name]['trades'] += 1
            if activity.pnl > 0:
                strategy_map[strategy_name]['wins'] += 1

    strategy_performance = []
    for name, data in strategy_map.items():
        s_trades = data['trades']
        s_wins = data['wins']
        s_ratio = s_wins / s_trades if s_trades > 0 else 0
        strategy_performance.append(
            StrategyPerformance(
                strategy_name=name,
                total_pnl=data['pnl'],
                total_trades=s_trades,
                win_loss_ratio=s_ratio,
            )
        )
        
    return Report(
        daily_pnl_data=daily_pnl_data,
        total_pnl=total_pnl,
        win_loss_ratio=win_loss_ratio,
        avg_profit=avg_profit,
        avg_loss=avg_loss,
        total_trades=total_trades,
        strategy_performance=strategy_performance,
    ) 