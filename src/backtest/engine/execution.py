"""
订单执行模拟器 — 佣金、滑点、最小交易单位
"""

from dataclasses import dataclass
from typing import Any
import math

from ..strategy.base import TradeAction


@dataclass
class Fill:
    """成交记录"""
    date: Any
    stock_code: str
    action: TradeAction
    order_price: float
    fill_price: float
    quantity: int
    commission: float
    slippage_cost: float

    @property
    def trade_value(self) -> float:
        return self.fill_price * self.quantity

    @property
    def total_cost(self) -> float:
        """买入为正（支出），卖出为负（收入），含佣金"""
        if self.action == TradeAction.BUY:
            return self.trade_value + self.commission
        else:
            return -(self.trade_value - self.commission)

    @property
    def net_proceeds(self) -> float:
        """卖出净收入（正），买入净支出（负）"""
        return -self.total_cost


class ExecutionSimulator:
    """订单执行模拟器"""

    LOT_SIZE = 100  # A股最小交易单位

    def __init__(
        self,
        commission_rate: float = 0.0003,
        min_commission: float = 5.0,
        slippage: float = 0.001,
    ):
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.slippage = slippage

    def simulate_buy(
        self,
        date: Any,
        stock_code: str,
        price: float,
        cash_available: float,
        position_pct: float,
    ) -> Fill:
        """模拟买入成交"""
        fill_price = price * (1 + self.slippage)
        fill_price = math.ceil(fill_price * 100) / 100

        max_shares = int(cash_available * position_pct / (fill_price * (1 + self.commission_rate)))
        quantity = (max_shares // self.LOT_SIZE) * self.LOT_SIZE

        if quantity <= 0:
            quantity = 0

        trade_value = fill_price * quantity
        commission = max(trade_value * self.commission_rate, self.min_commission) if quantity > 0 else 0

        if cash_available < trade_value + commission:
            quantity = int((cash_available / (fill_price * (1 + self.commission_rate) + self.min_commission / self.LOT_SIZE)) // self.LOT_SIZE) * self.LOT_SIZE
            if quantity < 0:
                quantity = 0
            trade_value = fill_price * quantity
            commission = max(trade_value * self.commission_rate, self.min_commission) if quantity > 0 else 0

        slippage_cost = (fill_price - price) * quantity

        return Fill(
            date=date,
            stock_code=stock_code,
            action=TradeAction.BUY,
            order_price=price,
            fill_price=fill_price,
            quantity=quantity,
            commission=commission,
            slippage_cost=slippage_cost,
        )

    def simulate_sell(
        self,
        date: Any,
        stock_code: str,
        price: float,
        shares_held: int,
    ) -> Fill:
        """模拟卖出成交"""
        fill_price = price * (1 - self.slippage)
        fill_price = math.floor(fill_price * 100) / 100

        quantity = min(shares_held, (shares_held // self.LOT_SIZE) * self.LOT_SIZE)
        if quantity <= 0:
            quantity = 0

        trade_value = fill_price * quantity
        commission = max(trade_value * self.commission_rate, self.min_commission) if quantity > 0 else 0
        slippage_cost = (price - fill_price) * quantity

        return Fill(
            date=date,
            stock_code=stock_code,
            action=TradeAction.SELL,
            order_price=price,
            fill_price=fill_price,
            quantity=quantity,
            commission=commission,
            slippage_cost=slippage_cost,
        )
