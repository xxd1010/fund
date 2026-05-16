"""
多指标集成策略 — 加权组合多个子策略
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

from .base import BaseStrategy
from .signal_strategy import SignalBasedStrategy
from .ma_cross_strategy import MACrossoverStrategy
from loguru import logger


class MultiIndicatorEnsembleStrategy(BaseStrategy):
    """
    集成策略，加权组合 SignalBasedStrategy 和 MACrossoverStrategy

    通过多数投票或加权平均产生最终信号。
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.weights = params.get("weights", {"signal": 0.5, "ma_cross": 0.5}) if params else {"signal": 0.5, "ma_cross": 0.5}
        self.vote_threshold = params.get("vote_threshold", 0.3) if params else 0.3

        signal_params = params.get("signal_params", {}) if params else {}
        ma_params = params.get("ma_params", {}) if params else {}
        self.signal_strategy = SignalBasedStrategy(signal_params)
        self.ma_strategy = MACrossoverStrategy(ma_params)
        self.name = "MultiIndicatorEnsemble"

    def generate_signals(
        self, stock_code: str, df: pd.DataFrame, date_index: pd.DatetimeIndex
    ) -> pd.Series:
        signals = pd.Series(0, index=date_index, dtype=int)

        try:
            sig1 = self.signal_strategy.generate_signals(stock_code, df, date_index)
            sig2 = self.ma_strategy.generate_signals(stock_code, df, date_index)

            w1 = self.weights.get("signal", 0.5)
            w2 = self.weights.get("ma_cross", 0.5)
            total_w = w1 + w2

            if total_w > 0:
                combined = (sig1 * w1 + sig2 * w2) / total_w
            else:
                combined = sig1 * 0.5 + sig2 * 0.5

            signals[combined >= self.vote_threshold] = 1
            signals[combined <= -self.vote_threshold] = -1

        except Exception as e:
            logger.warning(f"集成策略生成信号失败 ({stock_code}): {e}")

        return signals
