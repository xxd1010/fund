"""
均线交叉策略 — 支持多组均线对投票
"""

from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
import numpy as np

from .base import BaseStrategy
from loguru import logger


class MACrossoverStrategy(BaseStrategy):
    """
    均线金叉/死叉策略

    支持配置多组均线对，当多数均线对产生金叉时买入，死叉时卖出。
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        super().__init__(params)
        self.ma_pairs: List[Tuple[int, int]] = params.get("ma_pairs", [(5, 20), (10, 60)]) if params else [(5, 20), (10, 60)]
        self.min_votes: int = params.get("min_votes", 1) if params else 1
        self.signal_persistence: int = params.get("signal_persistence", 3) if params else 3

    def _get_close_col(self, df: pd.DataFrame) -> Optional[pd.Series]:
        for col in ["close", "收盘"]:
            if col in df.columns:
                return df[col]
        return None

    def generate_signals(
        self, stock_code: str, df: pd.DataFrame, date_index: pd.DatetimeIndex
    ) -> pd.Series:
        signals = pd.Series(0, index=date_index, dtype=int)

        close = self._get_close_col(df)
        if close is None or close.empty:
            return signals

        # 将 close 对齐到统一日期索引
        if hasattr(close, 'index') and isinstance(close.index, pd.DatetimeIndex):
            close = close.reindex(date_index)
        else:
            return signals

        # 对每组均线对计算信号
        all_signals = pd.DataFrame(index=date_index)

        for i, (short, long) in enumerate(self.ma_pairs):
            ma_short = close.rolling(short).mean()
            ma_long = close.rolling(long).mean()
            diff = ma_short - ma_long

            pair_signal = pd.Series(0, index=date_index, dtype=int)
            # 金叉：diff 从负变正
            golden = (diff > 0) & (diff.shift(1) <= 0)
            death = (diff < 0) & (diff.shift(1) >= 0)

            pair_signal[golden] = 1
            pair_signal[death] = -1

            if self.signal_persistence > 1:
                for j in range(1, self.signal_persistence):
                    pair_signal[(pair_signal == 0) & (pair_signal.shift(j) == 1)] = 1
                    pair_signal[(pair_signal == 0) & (pair_signal.shift(j) == -1)] = -1

            all_signals[f"pair_{i}"] = pair_signal

        # 投票
        buy_votes = (all_signals == 1).sum(axis=1)
        sell_votes = (all_signals == -1).sum(axis=1)

        signals[(buy_votes >= self.min_votes) & (buy_votes > sell_votes)] = 1
        signals[(sell_votes >= self.min_votes) & (sell_votes > buy_votes)] = -1

        return signals
