"""
回测配置数据类
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class BacktestConfig:
    """回测全局配置"""

    initial_capital: float = 100000.0
    position_sizing: str = "equal_weight"
    max_positions: int = 10

    commission_rate: float = 0.0003
    min_commission: float = 5.0
    slippage: float = 0.001
    buy_delay: int = 1
    sell_delay: int = 1

    stop_loss_pct: float = -0.08
    take_profit_pct: float = 0.20
    max_holding_days: int = 60

    start_date: str = ""
    end_date: str = ""

    strategy_type: str = "signal"
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    benchmark_code: str = "000300"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_capital": self.initial_capital,
            "position_sizing": self.position_sizing,
            "max_positions": self.max_positions,
            "commission_rate": self.commission_rate,
            "min_commission": self.min_commission,
            "slippage": self.slippage,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "max_holding_days": self.max_holding_days,
            "strategy_type": self.strategy_type,
            "strategy_params": self.strategy_params,
        }
