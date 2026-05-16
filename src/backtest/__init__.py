"""
回测与策略模块

提供策略回测框架，包括：
- 多种交易策略（信号策略、均线交叉策略、集成策略）
- 投资组合级别的回测引擎
- 绩效指标计算与基准对比
- 回测报告生成
"""

from .config import BacktestConfig
from .strategy.base import BaseStrategy, StrategySignal, TradeAction
from .strategy.signal_strategy import SignalBasedStrategy
from .strategy.ma_cross_strategy import MACrossoverStrategy
from .strategy.ensemble_strategy import MultiIndicatorEnsembleStrategy

__all__ = [
    "BacktestConfig",
    "BaseStrategy",
    "StrategySignal",
    "TradeAction",
    "SignalBasedStrategy",
    "MACrossoverStrategy",
    "MultiIndicatorEnsembleStrategy",
]
