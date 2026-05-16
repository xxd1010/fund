"""
策略模块

提供策略抽象基类和内置策略实现
"""

from .base import BaseStrategy, StrategySignal, TradeAction

__all__ = ["BaseStrategy", "StrategySignal", "TradeAction"]
