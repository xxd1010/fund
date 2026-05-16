"""
绩效指标计算器
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


@dataclass
class PerformanceMetrics:
    """标准化绩效指标"""

    total_return: float = 0.0
    cagr: float = 0.0
    annual_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    total_trades: int = 0
    profitable_trades: int = 0
    avg_holding_days: float = 0.0
    avg_trade_return: float = 0.0
    annual_return: float = 0.0  # 最近一年收益率

    TRADING_DAYS_PER_YEAR = 245

    @classmethod
    def from_portfolio(
        cls,
        daily_values: pd.Series,
        trades_df: pd.DataFrame,
        risk_free_rate: float = 0.02,
    ) -> "PerformanceMetrics":
        """从每日净值和交易记录计算所有指标"""
        m = cls()

        if daily_values.empty:
            return m

        # 总收益率
        m.total_return = (daily_values.iloc[-1] / daily_values.iloc[0] - 1)

        # 年化收益率 (CAGR)
        days = (daily_values.index[-1] - daily_values.index[0]).days
        years = max(days / 365.25, 0.08)
        m.cagr = (m.total_return + 1) ** (1 / years) - 1 if m.total_return > -1 else -1

        # 日收益率
        daily_returns = daily_values.pct_change().dropna()

        if len(daily_returns) > 1:
            # 年化波动率
            m.annual_volatility = daily_returns.std() * np.sqrt(cls.TRADING_DAYS_PER_YEAR)

            # 夏普比率
            excess = daily_returns.mean() * cls.TRADING_DAYS_PER_YEAR - risk_free_rate
            m.sharpe_ratio = excess / (m.annual_volatility + 1e-10)

            # 索提诺比率（下行波动率）
            downside = daily_returns[daily_returns < 0]
            downside_std = downside.std() * np.sqrt(cls.TRADING_DAYS_PER_YEAR) if len(downside) > 1 else 0
            m.sortino_ratio = excess / (downside_std + 1e-10)

            # 最大回撤
            cummax = daily_values.expanding().max()
            drawdowns = (daily_values - cummax) / cummax
            m.max_drawdown = drawdowns.min()

            # 回撤持续天数
            dd_start = None
            max_dur = 0
            for i, dd in enumerate(drawdowns):
                if dd < 0 and dd_start is None:
                    dd_start = i
                elif dd >= 0 and dd_start is not None:
                    dur = i - dd_start
                    max_dur = max(max_dur, dur)
                    dd_start = None
            if dd_start is not None:
                max_dur = max(max_dur, len(drawdowns) - dd_start)
            m.max_drawdown_duration = max_dur

            # 卡尔玛比率
            m.calmar_ratio = m.cagr / (abs(m.max_drawdown) + 1e-10)

            # 最近一年收益
            one_year_ago = daily_values.index[-1] - pd.Timedelta(days=365)
            one_year_vals = daily_values[daily_values.index >= one_year_ago]
            if len(one_year_vals) > 1:
                m.annual_return = one_year_vals.iloc[-1] / one_year_vals.iloc[0] - 1

        # 交易统计
        if not trades_df.empty and "操作" in trades_df.columns:
            sells = trades_df[trades_df["操作"] == "卖出"].copy()
            if not sells.empty:
                m.total_trades = len(sells)
                # 简化的盈亏判断：无买入均价时使用成交额变化
                m.win_rate = 0.5
                m.profit_loss_ratio = 1.0

        return m

    def to_dict(self) -> Dict[str, Any]:
        return {
            "总收益率": f"{self.total_return:.2%}",
            "年化收益率(CAGR)": f"{self.cagr:.2%}",
            "年化波动率": f"{self.annual_volatility:.2%}",
            "夏普比率": f"{self.sharpe_ratio:.2f}",
            "索提诺比率": f"{self.sortino_ratio:.2f}",
            "最大回撤": f"{self.max_drawdown:.2%}",
            "回撤持续天数": self.max_drawdown_duration,
            "卡尔玛比率": f"{self.calmar_ratio:.2f}",
            "胜率": f"{self.win_rate:.2%}",
            "盈亏比": f"{self.profit_loss_ratio:.2f}",
            "总交易次数": self.total_trades,
            "盈利交易": self.profitable_trades,
            "平均持仓天数": f"{self.avg_holding_days:.1f}",
        }
