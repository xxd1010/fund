"""
策略抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional

import pandas as pd


class TradeAction(Enum):
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"


@dataclass
class StrategySignal:
    """单只股票单个交易日的策略信号"""

    date: Any
    stock_code: str
    action: TradeAction
    strength: float = 0.0
    price: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """策略抽象基类，所有策略必须实现 generate_signals 方法"""

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        self.params = params or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def generate_signals(
        self,
        stock_code: str,
        df: pd.DataFrame,
        date_index: pd.DatetimeIndex,
    ) -> pd.Series:
        """生成信号序列。返回与 date_index 对齐的 Series，值: +1 买入, -1 卖出, 0 持有"""
        ...

    def get_signal_strength(self, stock_code: str, df: pd.DataFrame, date: Any) -> float:
        """可选的信号强度计算，用于仓位分配"""
        return 1.0
