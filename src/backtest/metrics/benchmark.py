"""
基准对比 — 沪深300 买入持有
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np

from .performance import PerformanceMetrics
from loguru import logger


class BenchmarkComparison:
    """与基准收益对比"""

    def __init__(self, benchmark_data: pd.DataFrame):
        close_col = "收盘" if "收盘" in benchmark_data.columns else "close"
        date_col = "日期" if "日期" in benchmark_data.columns else "date"

        if close_col not in benchmark_data.columns or date_col not in benchmark_data.columns:
            raise ValueError("基准数据缺少必要列")

        self.benchmark_data = benchmark_data.copy()
        self.benchmark_data[date_col] = pd.to_datetime(self.benchmark_data[date_col])
        self.benchmark_data = self.benchmark_data.sort_values(date_col)
        self.benchmark_data.set_index(date_col, inplace=True)
        self.close = self.benchmark_data[close_col]

    def compute_buy_hold_metrics(self) -> PerformanceMetrics:
        """计算基准买入持有策略的绩效指标"""
        daily_values = self.close.dropna()
        if daily_values.empty:
            return PerformanceMetrics()

        trades = pd.DataFrame({
            "日期": [daily_values.index[0], daily_values.index[-1]],
            "股票代码": ["基准", "基准"],
            "操作": ["买入", "卖出"],
            "成交价": [daily_values.iloc[0], daily_values.iloc[-1]],
            "数量": [1, 1],
            "成交额": [daily_values.iloc[0], daily_values.iloc[-1]],
            "佣金": [0, 0],
            "滑点成本": [0, 0],
        })

        return PerformanceMetrics.from_portfolio(daily_values, trades)

    def compare(
        self, backtest_values: pd.Series, backtest_metrics: PerformanceMetrics
    ) -> Dict[str, Any]:
        """对比回测结果与基准"""
        try:
            bench_metrics = self.compute_buy_hold_metrics()

            # 对齐数据
            aligned = pd.DataFrame({
                "strategy": backtest_values,
                "benchmark": self.close,
            }).dropna()

            if aligned.empty:
                return {"error": "数据无法对齐"}

            # Alpha
            strategy_return = aligned["strategy"].pct_change().mean() * 245
            benchmark_return = aligned["benchmark"].pct_change().mean() * 245
            alpha = strategy_return - benchmark_return

            # 超额收益
            excess_return = backtest_metrics.total_return - bench_metrics.total_return

            return {
                "策略收益率": f"{backtest_metrics.total_return:.2%}",
                "基准收益率": f"{bench_metrics.total_return:.2%}",
                "超额收益": f"{excess_return:.2%}",
                "年化Alpha": f"{alpha:.2%}",
                "策略夏普": f"{backtest_metrics.sharpe_ratio:.2f}",
                "基准夏普": f"{bench_metrics.sharpe_ratio:.2f}",
            }
        except Exception as e:
            logger.warning(f"基准对比计算失败: {e}")
            return {"error": str(e)}
