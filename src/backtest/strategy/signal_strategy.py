"""
基于综合信号的策略 — 复用 SignalJudger 的历史评分
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .base import BaseStrategy
from src.analysis.signal_judgment import SignalJudger
from src.constants import TECHNICAL_INDICATORS_CONFIG
from loguru import logger


class SignalBasedStrategy(BaseStrategy):
    """
    基于综合技术指标的策略

    使用 SignalJudger.get_historical_signals() 计算每行的 overall_score，
    超过买入阈值产生买入信号，低于卖出阈值产生卖出信号。
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.buy_threshold = params.get("buy_threshold", 0.2) if params else 0.2
        self.sell_threshold = params.get("sell_threshold", -0.2) if params else -0.2
        self.tech_config = params.get("tech_config", TECHNICAL_INDICATORS_CONFIG) if params else TECHNICAL_INDICATORS_CONFIG
        self.min_data_points = params.get("min_data_points", 100) if params else 100
        self.signal_persistence = params.get("signal_persistence", 3) if params else 3

    def generate_signals(
        self, stock_code: str, df: pd.DataFrame, date_index: pd.DatetimeIndex
    ) -> pd.Series:
        """
        生成信号序列

        返回与 date_index 对齐的 Series，值为 +1(买入)/-1(卖出)/0(持有)
        """
        signals = pd.Series(0, index=date_index, dtype=int)

        if df.empty or len(df) < self.min_data_points:
            return signals

        try:
            judger = SignalJudger(data=df, tech_period=self.tech_config)
            hist = judger.get_historical_signals(min_data_points=self.min_data_points)

            if hist.empty:
                return signals

            hist["date"] = pd.to_datetime(hist["date"])
            hist = hist.set_index("date")

            # 将 overall_score 对齐到统一日期索引
            aligned = hist["overall_score"].reindex(date_index).fillna(0)

            # 产生信号：超过阈值买入，低于卖出
            buy_signal = aligned >= self.buy_threshold
            sell_signal = aligned <= self.sell_threshold

            signals[buy_signal] = 1
            signals[sell_signal] = -1

            # 信号持续性：信号出现后的N天内保持
            if self.signal_persistence > 1:
                for i in range(1, self.signal_persistence):
                    shifted_buy = buy_signal.shift(i).fillna(False)
                    shifted_sell = sell_signal.shift(i).fillna(False)
                    mask = (signals == 0) & shifted_buy
                    signals[mask] = 1
                    mask = (signals == 0) & shifted_sell
                    signals[mask] = -1

        except Exception as e:
            logger.warning(f"股票 {stock_code} 生成信号失败: {e}")

        return signals

    def get_signal_strength(self, stock_code: str, df: pd.DataFrame, date: Any) -> float:
        """返回最新日期的信号强度（用于仓位分配）"""
        try:
            judger = SignalJudger(data=df, tech_period=self.tech_config)
            result = judger.get_signals()
            return abs(result.overall_score)
        except Exception:
            return 0.5
