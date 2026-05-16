"""
回测引擎 — 逐日循环模拟交易
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
from loguru import logger
from tqdm import tqdm

from ..config import BacktestConfig
from ..strategy.base import BaseStrategy, TradeAction
from .execution import ExecutionSimulator
from .position_sizer import PositionSizer
from .portfolio_manager import PortfolioManager


@dataclass
class BacktestResult:
    """完整回测结果"""
    config: BacktestConfig
    strategy_name: str = ""
    portfolio_snapshots: pd.DataFrame = field(default_factory=pd.DataFrame)
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)
    metrics: Any = None
    benchmark_metrics: Any = None
    per_stock_results: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_name": self.strategy_name,
            "metrics": self.metrics.to_dict() if self.metrics else {},
            "benchmark_metrics": self.benchmark_metrics.to_dict() if self.benchmark_metrics else {},
            "total_trades": len(self.trades),
        }


class BacktestEngine:
    """投资组合级别回测引擎"""

    def __init__(
        self,
        config: BacktestConfig,
        strategy: BaseStrategy,
        execution: Optional[ExecutionSimulator] = None,
        portfolio: Optional[PortfolioManager] = None,
        position_sizer: Optional[PositionSizer] = None,
    ):
        self.config = config
        self.strategy = strategy
        self.execution = execution or ExecutionSimulator(
            commission_rate=config.commission_rate,
            min_commission=config.min_commission,
            slippage=config.slippage,
        )
        self.portfolio = portfolio or PortfolioManager(config.initial_capital)
        self.sizer = position_sizer or PositionSizer(
            method=config.position_sizing,
            max_positions=config.max_positions,
        )

    def _validate_stock_data(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """验证并标准化股票数据"""
        validated = {}
        for code, df in stock_data.items():
            if df.empty:
                continue
            close_col = "收盘" if "收盘" in df.columns else "close"
            date_col = "日期" if "日期" in df.columns else "date"
            if close_col not in df.columns or date_col not in df.columns:
                logger.warning(f"股票 {code} 缺少必要列，跳过")
                continue
            df = df.copy()
            df[date_col] = pd.to_datetime(df[date_col])
            if date_col != "date":
                df["date"] = df[date_col]
            if close_col != "close":
                df["close"] = df[close_col]
            validated[code] = df
        return validated

    def _build_unified_date_index(
        self, stock_data: Dict[str, pd.DataFrame]
    ) -> pd.DatetimeIndex:
        """构建所有股票的统一交易日历"""
        all_dates = []
        for df in stock_data.values():
            dates = pd.to_datetime(df["date"] if "date" in df.columns else df["日期"])
            all_dates.append(dates)
        if not all_dates:
            return pd.DatetimeIndex([])
        unified = pd.DatetimeIndex(sorted(set().union(*[set(d) for d in all_dates])))
        start = pd.Timestamp(self.config.start_date) if self.config.start_date else None
        end = pd.Timestamp(self.config.end_date) if self.config.end_date else None
        if start:
            unified = unified[unified >= start]
        if end:
            unified = unified[unified <= end]
        return unified

    def _get_price_on_date(self, df: pd.DataFrame, date: pd.Timestamp, price_col: str = "close") -> Optional[float]:
        """获取某只股票在特定日期的收盘价"""
        date_col = "date" if "date" in df.columns else "日期"
        mask = df[date_col] == date
        if mask.any():
            val = df.loc[mask, price_col]
            if not val.empty and not pd.isna(val.iloc[0]):
                return float(val.iloc[0])
        return None

    def _get_next_trading_day(self, df: pd.DataFrame, date: pd.Timestamp) -> Optional[pd.Timestamp]:
        """获取下一个交易日"""
        date_col = "date" if "date" in df.columns else "日期"
        future = df[df[date_col] > date][date_col]
        return future.iloc[0] if not future.empty else None

    def run(
        self,
        stock_data: Dict[str, pd.DataFrame],
        benchmark_data: Optional[pd.DataFrame] = None,
    ) -> BacktestResult:
        """
        执行回测

        Args:
            stock_data: 股票代码 -> 含指标 DataFrame
            benchmark_data: 基准（如沪深300）K线数据
        """
        stock_data = self._validate_stock_data(stock_data)
        if not stock_data:
            logger.error("无有效股票数据")
            return BacktestResult(config=self.config, strategy_name=self.strategy.name)

        date_index = self._build_unified_date_index(stock_data)
        if len(date_index) < 2:
            logger.error("交易日不足")
            return BacktestResult(config=self.config, strategy_name=self.strategy.name)

        # 预计算信号
        signals_map: Dict[str, pd.Series] = {}
        for code, df in stock_data.items():
            sig = self.strategy.generate_signals(code, df, date_index)
            signals_map[code] = sig

        logger.info(f"回测开始: {len(stock_data)} 只股票, {len(date_index)} 个交易日")

        # 逐日循环
        for date in tqdm(date_index, desc="回测进度", unit="日"):
            current_prices: Dict[str, float] = {}
            for code, df in stock_data.items():
                price = self._get_price_on_date(df, date)
                if price is not None:
                    current_prices[code] = price

            # 1. 检查风控
            triggers = self.portfolio.check_risk_stops(
                date, current_prices,
                stop_loss_pct=self.config.stop_loss_pct,
                take_profit_pct=self.config.take_profit_pct,
                max_holding_days=self.config.max_holding_days,
            )
            for trigger in triggers:
                fill = self.execution.simulate_sell(
                    date, trigger["stock_code"], trigger["price"], trigger["shares"]
                )
                self.portfolio.apply_fill(fill)

            # 2. 处理信号
            for code in stock_data:
                if code not in signals_map:
                    continue
                sig_value = signals_map[code].get(date, 0)
                if pd.isna(sig_value):
                    sig_value = 0
                sig_value = int(sig_value)

                if sig_value == 1:  # 买入信号
                    if code in self.portfolio.positions:
                        continue
                    price = current_prices.get(code)
                    if price is None:
                        continue

                    # 延迟执行
                    exec_date = date
                    exec_price = price
                    next_day = self._get_next_trading_day(stock_data[code], date)
                    if self.config.buy_delay > 0 and next_day is not None:
                        delayed_price = self._get_price_on_date(stock_data[code], next_day)
                        if delayed_price is not None:
                            exec_date = next_day
                            exec_price = delayed_price

                    strength = self.strategy.get_signal_strength(code, stock_data[code], date)
                    position_pct = self.sizer.calculate_size(
                        self.portfolio.cash, self.portfolio.total_value,
                        signal_strength=strength, num_active=len(self.portfolio.positions),
                    )
                    fill = self.execution.simulate_buy(
                        exec_date, code, exec_price, self.portfolio.cash, position_pct
                    )
                    if fill.quantity > 0:
                        self.portfolio.apply_fill(fill)

                elif sig_value == -1:  # 卖出信号
                    if code not in self.portfolio.positions:
                        continue
                    price = current_prices.get(code)
                    if price is None:
                        continue

                    exec_date = date
                    exec_price = price
                    next_day = self._get_next_trading_day(stock_data[code], date)
                    if self.config.sell_delay > 0 and next_day is not None:
                        delayed_price = self._get_price_on_date(stock_data[code], next_day)
                        if delayed_price is not None:
                            exec_date = next_day
                            exec_price = delayed_price

                    pos = self.portfolio.positions[code]
                    fill = self.execution.simulate_sell(exec_date, code, exec_price, pos.shares)
                    if fill.quantity > 0:
                        self.portfolio.apply_fill(fill)

            # 3. 记录快照
            self.portfolio.snapshot(date, current_prices)

        logger.info(f"回测完成: {len(self.portfolio.trades)} 笔交易")

        # 计算绩效指标
        from ..metrics.performance import PerformanceMetrics
        from ..metrics.benchmark import BenchmarkComparison

        metrics = PerformanceMetrics.from_portfolio(
            self.portfolio.get_daily_values(), self.portfolio.get_trades_df()
        )

        benchmark_metrics = None
        if benchmark_data is not None and not benchmark_data.empty:
            try:
                bc = BenchmarkComparison(benchmark_data)
                benchmark_metrics = bc.compute_buy_hold_metrics()
            except Exception as e:
                logger.warning(f"基准计算失败: {e}")

        daily_vals = self.portfolio.get_daily_values()
        snapshots = pd.DataFrame({
            "date": daily_vals.index,
            "total_value": daily_vals.values,
        }) if not daily_vals.empty else pd.DataFrame()

        return BacktestResult(
            config=self.config,
            strategy_name=self.strategy.name,
            portfolio_snapshots=snapshots,
            trades=self.portfolio.get_trades_df(),
            metrics=metrics,
            benchmark_metrics=benchmark_metrics,
        )
