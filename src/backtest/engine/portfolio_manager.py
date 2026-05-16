"""
投资组合管理器 — 资金、持仓、净值管理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import pandas as pd

from .execution import Fill
from ..strategy.base import TradeAction
from loguru import logger


@dataclass
class Position:
    """单只股票持仓"""
    stock_code: str
    shares: int
    avg_cost: float
    entry_date: Any
    entry_price: float = 0.0
    highest_value: float = 0.0  # 持仓期间最高市值（用于回撤计算）


@dataclass
class PortfolioSnapshot:
    """每日投资组合快照"""
    date: Any
    cash: float
    positions_value: float
    total_value: float
    daily_return: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)  # stock_code -> market_value


class PortfolioManager:
    """投资组合管理器"""

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.snapshots: List[PortfolioSnapshot] = []
        self.trades: List[Fill] = []
        self._prev_total = initial_capital

    @property
    def total_value(self) -> float:
        """当前总资产（需要先 snapshot 才能获取最新）"""
        if self.snapshots:
            return self.snapshots[-1].total_value
        return self.cash

    def apply_fill(self, fill: Fill, current_prices: Optional[Dict[str, float]] = None) -> bool:
        """应用成交记录"""
        if fill.quantity <= 0:
            return False

        if fill.action == TradeAction.BUY:
            cost = fill.trade_value + fill.commission
            if self.cash < cost:
                return False
            self.cash -= cost
            if fill.stock_code in self.positions:
                pos = self.positions[fill.stock_code]
                total_cost = pos.shares * pos.avg_cost + cost
                pos.shares += fill.quantity
                pos.avg_cost = total_cost / pos.shares if pos.shares > 0 else 0
            else:
                self.positions[fill.stock_code] = Position(
                    stock_code=fill.stock_code,
                    shares=fill.quantity,
                    avg_cost=fill.fill_price,
                    entry_date=fill.date,
                    entry_price=fill.fill_price,
                    highest_value=fill.trade_value,
                )
        else:
            if fill.stock_code not in self.positions:
                return False
            pos = self.positions[fill.stock_code]
            if pos.shares < fill.quantity:
                return False
            proceeds = fill.trade_value - fill.commission
            self.cash += proceeds
            pos.shares -= fill.quantity
            if pos.shares <= 0:
                del self.positions[fill.stock_code]

        self.trades.append(fill)
        return True

    def snapshot(self, date: Any, current_prices: Dict[str, float]) -> PortfolioSnapshot:
        """记录当日净值快照"""
        positions_value = 0.0
        pos_dict = {}

        for code, pos in self.positions.items():
            price = current_prices.get(code, pos.avg_cost)
            mv = pos.shares * price
            positions_value += mv
            pos_dict[code] = mv
            if mv > pos.highest_value:
                pos.highest_value = mv

        total = self.cash + positions_value
        daily_return = (total / self._prev_total - 1) if self._prev_total > 0 else 0.0
        self._prev_total = total

        snap = PortfolioSnapshot(
            date=date,
            cash=self.cash,
            positions_value=positions_value,
            total_value=total,
            daily_return=daily_return,
            positions=pos_dict,
        )
        self.snapshots.append(snap)
        return snap

    def check_risk_stops(
        self,
        date: Any,
        current_prices: Dict[str, float],
        stop_loss_pct: float = -0.08,
        take_profit_pct: float = 0.20,
        max_holding_days: int = 60,
    ) -> List[Dict[str, Any]]:
        """检查止损/止盈/持仓时间触发"""
        triggers = []

        for code, pos in list(self.positions.items()):
            price = current_prices.get(code, pos.avg_cost)
            profit_pct = (price - pos.avg_cost) / pos.avg_cost if pos.avg_cost > 0 else 0

            holding_days = 0
            if hasattr(date, 'date'):
                holding_days = (date.date() - pd.Timestamp(pos.entry_date).date()).days
            elif isinstance(date, str):
                holding_days = (pd.Timestamp(date) - pd.Timestamp(pos.entry_date)).days

            reason = None
            if profit_pct <= stop_loss_pct:
                reason = f"止损 ({profit_pct:.1%})"
            elif profit_pct >= take_profit_pct:
                reason = f"止盈 ({profit_pct:.1%})"
            elif holding_days >= max_holding_days:
                reason = f"持仓到期 ({holding_days}天)"

            if reason:
                triggers.append({
                    "stock_code": code,
                    "reason": reason,
                    "price": price,
                    "shares": pos.shares,
                    "profit_pct": profit_pct,
                })

        return triggers

    def get_daily_values(self) -> pd.Series:
        """返回每日净值序列"""
        if not self.snapshots:
            return pd.Series()
        dates = [s.date for s in self.snapshots]
        values = [s.total_value for s in self.snapshots]
        return pd.Series(values, index=pd.to_datetime(dates))

    def get_trades_df(self) -> pd.DataFrame:
        """返回交易记录 DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        records = []
        for t in self.trades:
            records.append({
                "日期": t.date,
                "股票代码": t.stock_code,
                "操作": t.action.value,
                "委托价": t.order_price,
                "成交价": t.fill_price,
                "数量": t.quantity,
                "成交额": t.trade_value,
                "佣金": t.commission,
                "滑点成本": t.slippage_cost,
            })
        return pd.DataFrame(records)
