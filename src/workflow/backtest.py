"""
回测工作流 — 集成现有数据管线
"""

from typing import Dict, List, Any, Optional
import pandas as pd

from .base import BaseWorkflow
from src.backtest.config import BacktestConfig
from src.backtest.strategy.signal_strategy import SignalBasedStrategy
from src.backtest.strategy.ma_cross_strategy import MACrossoverStrategy
from src.backtest.strategy.ensemble_strategy import MultiIndicatorEnsembleStrategy
from src.backtest.engine.backtest_engine import BacktestEngine, BacktestResult
from src.backtest.reporter import BacktestReportGenerator
from src.utils.logger import logger


STRATEGY_MAP = {
    "signal": SignalBasedStrategy,
    "ma_cross": MACrossoverStrategy,
    "ensemble": MultiIndicatorEnsembleStrategy,
}


class BacktestWorkflow(BaseWorkflow):
    """回测工作流，继承 BaseWorkflow 复用数据获取方法"""

    def __init__(
        self,
        start_date: str = "2019-01-01",
        data_dir: str = "data",
        config: Optional[Dict[str, Any]] = None,
        max_workers: int = 8,
    ):
        super().__init__(start_date, data_dir, config, max_workers)
        backtest_cfg = (config or {}).get("backtest", {})
        self.backtest_config = BacktestConfig(
            start_date=start_date,
            **{k: v for k, v in backtest_cfg.items() if k in BacktestConfig.__dataclass_fields__},
        )

    def _get_strategy(self):
        """根据配置创建策略实例"""
        stype = self.backtest_config.strategy_type
        params = self.backtest_config.strategy_params or {}
        cls = STRATEGY_MAP.get(stype, SignalBasedStrategy)
        return cls(params)

    def run_backtest(self, fund_code: str) -> BacktestResult:
        """对单个基金的持仓股票执行回测"""
        logger.info(f"开始基金 {fund_code} 的回测...")

        # 1. 获取基金持仓
        fund_info = self.get_fund_holdings(fund_code)
        if fund_info.empty:
            logger.error(f"基金 {fund_code} 持仓为空")
            return BacktestResult(config=self.backtest_config, strategy_name="N/A")

        # 2. 过滤最新季度
        latest = self.filter_latest_quarter(fund_info)
        stock_codes = latest["股票代码"].unique().tolist() if "股票代码" in latest.columns else []
        logger.info(f"持仓股票: {len(stock_codes)} 只 — {stock_codes}")

        if not stock_codes:
            logger.error(f"基金 {fund_code} 无持仓股票")
            return BacktestResult(config=self.backtest_config, strategy_name="N/A")

        # 3. 加载股票数据
        stock_data = self.get_stock_data(stock_codes)
        if not stock_data:
            logger.error("无法获取股票数据")
            return BacktestResult(config=self.backtest_config, strategy_name="N/A")

        # 4. 确保所有股票都计算了技术指标
        indicators_data = {}
        for code in stock_codes:
            indicator_file = f"{code}_with_indicators"
            file_path = f"{self.data_dir}/{indicator_file}.csv"

            import os
            if os.path.exists(file_path):
                df = pd.read_csv(file_path, encoding="utf-8-sig")
                indicators_data[code] = df
            elif code in stock_data:
                try:
                    df = self.calculate_technical_indicators(stock_data[code], code)
                    self.save_indicators(df, code)
                    indicators_data[code] = df
                except Exception as e:
                    logger.warning(f"计算 {code} 技术指标失败: {e}")

        if not indicators_data:
            logger.error("无有效的技术指标数据")
            return BacktestResult(config=self.backtest_config, strategy_name="N/A")

        # 5. 可选：获取基准数据
        try:
            benchmark = self.ak_fund.get_stock_kline(
                symbol=self.backtest_config.benchmark_code,
                period="daily",
                start_date=self.start_date,
            )
            if benchmark.empty:
                benchmark = None
        except Exception:
            benchmark = None

        # 6. 创建策略和引擎
        strategy = self._get_strategy()
        engine = BacktestEngine(
            config=self.backtest_config,
            strategy=strategy,
        )

        # 7. 运行回测
        result = engine.run(indicators_data, benchmark)

        # 8. 生成报告
        reporter = BacktestReportGenerator()
        reporter.save_report(result, fund_code)

        # 打印摘要
        if result.metrics:
            logger.info(f"\n{reporter.generate_summary(result, fund_code)}")

        return result

    def run_batch(self, fund_codes: List[str]) -> Dict[str, BacktestResult]:
        """批量回测多个基金"""
        results = {}
        for code in fund_codes:
            try:
                results[code] = self.run_backtest(code)
            except Exception as e:
                logger.error(f"基金 {code} 回测失败: {e}")
                results[code] = BacktestResult(config=self.backtest_config, strategy_name="failed")
        return results
