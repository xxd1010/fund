"""
基础工作流类
包含共享的数据获取和处理方法
"""

import os
from typing import Dict, List, Any, Optional
import pandas as pd
from tqdm import tqdm

from src.core.data_fetcher import AkFund
from src.data.reader import DataReader
from src.analysis.quarter_filter import filter_latest_quarter_data
from src.indicators.technical_indicators import TechnicalIndicators as TI
from src.analysis.signal_judgment import SignalJudger
from src.utils.logger import logger
from src.utils.concurrency import ConcurrentProcessor


# 技术指标默认配置
DEFAULT_TECHNICAL_INDICATORS_CONFIG = {
    "ma_period": [3, 5, 10, 14, 20, 30, 45],
    "sma_period": [3, 5, 10, 14, 20, 30, 45],
    "ema_period": [12, 26],
    "rsi_period": [6, 12, 24],
    "macd_period": ["12-26-9"],
    "boll_period": ["20-2"],
    "kdj_period": ["9-3-3"],
    "atr_period": [10],
    "cci_period": [20, 26],
    "williams_r_period": [10],
    "bias_period": [5, 10, 20, 30, 60, 120, 250],
    "psy_period": [10],
    "rsv_period": [10],
    "volume_period": [20],
}


class BaseWorkflow:
    """基础工作流类，提供共享的数据处理方法"""

    def __init__(
        self,
        start_date: str = "2021-01-01",
        data_dir: str = "stock_data",
        config: Optional[Dict[str, Any]] = None,
        max_workers: int = 8,
    ):
        """
        初始化基础工作流

        Args:
            start_date: 开始日期
            data_dir: 数据目录
            config: 配置字典，包含技术指标配置等
            max_workers: 最大并发工作线程数
        """
        self.start_date = start_date
        self.data_dir = data_dir
        self.config = config or {}
        self.max_workers = max_workers

        # 技术指标配置，优先使用传入的配置，否则使用默认配置
        self.tech_config = self.config.get(
            "technical_indicators", DEFAULT_TECHNICAL_INDICATORS_CONFIG
        )

        # 初始化数据获取对象
        self.ak_fund = AkFund()
        self.rd = DataReader(base_path="data")

        # 初始化并发处理器
        self.processor = ConcurrentProcessor(max_workers=max_workers, use_threads=True)

    def get_fund_holdings(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金持仓数据

        Args:
            fund_code: 基金代码

        Returns:
            基金持仓DataFrame
        """
        logger.info(f"获取基金 {fund_code} 的持仓数据")
        fund_info = self.ak_fund.get_fund_portfolio(fund_code=fund_code)
        if fund_info.empty:
            logger.error(f"基金 {fund_code} 的持仓数据为空")
        return fund_info

    def filter_latest_quarter(self, fund_info: pd.DataFrame) -> pd.DataFrame:
        """
        过滤出最新季度的持仓数据

        Args:
            fund_info: 基金持仓DataFrame

        Returns:
            最新季度持仓DataFrame
        """
        logger.info("过滤最新季度数据")
        quarter_summary = filter_latest_quarter_data(fund_info)
        return quarter_summary

    def get_stock_data(self, stock_codes: List[str]) -> Dict[str, pd.DataFrame]:
        """
        批量获取股票K线数据（支持并发）

        Args:
            stock_codes: 股票代码列表

        Returns:
            股票代码到K线数据的映射字典
        """
        logger.info(f"批量处理 {len(stock_codes)} 只股票的数据")

        def fetch_single_stock(stock_code: str) -> Optional[pd.DataFrame]:
            """获取单只股票数据"""
            try:
                # 检查是否已有数据文件
                existing_files = self.rd.list_stock_files(self.data_dir)

                if stock_code in existing_files:
                    # 从本地读取
                    stock_kline = self.rd.read_stock_kline(
                        symbol=stock_code, data_dir=self.data_dir
                    )
                else:
                    # 从网络下载
                    stock_kline = self.ak_fund.get_stock_kline(
                        symbol=stock_code, period="daily", start_date=self.start_date
                    )
                    # 保存到本地
                    if not stock_kline.empty:
                        self.ak_fund.save_data(
                            stock_kline,
                            file_name=f"{self.data_dir}/{stock_code}_kline",
                            file_type="csv",
                        )

                if not stock_kline.empty:
                    return stock_kline
                else:
                    logger.warning(f"股票 {stock_code} 数据为空，跳过")
                    return None

            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时出错: {e}")
                return None

        # 使用并发处理获取股票数据
        if len(stock_codes) > 1 and self.max_workers > 1:
            results = self.processor.process_batch(
                items=stock_codes,
                processor=fetch_single_stock,
                desc="获取股票数据",
                show_progress=True,
            )
            stock_data_map = {
                code: data for code, data in results.items() if data is not None
            }
        else:
            # 单线程处理
            stock_data_map = {}
            for stock_code in tqdm(stock_codes, desc="获取股票数据", unit="只"):
                logger.info(f"处理股票 {stock_code}...")
                data = fetch_single_stock(stock_code)
                if data is not None:
                    stock_data_map[stock_code] = data

        logger.info(f"成功获取 {len(stock_data_map)} 只股票的数据")
        return stock_data_map

    def calculate_technical_indicators(
        self, stock_kline: pd.DataFrame, stock_code: str = ""
    ) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            stock_kline: 股票K线数据
            stock_code: 股票代码（用于日志）

        Returns:
            包含技术指标的DataFrame
        """
        if stock_code:
            logger.info(f"计算股票 {stock_code} 的技术指标")

        try:
            ti = TI(stock_kline)

            # 配置要计算的指标
            indicators_to_calculate = list(self.tech_config.keys())

            # 计算所有指标
            indicators_df = ti.calculate_all(indicators=indicators_to_calculate)

            # 合并原始数据和技术指标
            result = pd.concat(
                [stock_kline.reset_index(drop=True), indicators_df], axis=1
            )

            return result

        except Exception as e:
            logger.error(f"计算技术指标时出错: {e}")
            raise

    def calculate_signals(
        self, indicators_df: pd.DataFrame, stock_code: str = ""
    ) -> Dict[str, Any]:
        """
        进行信号判断

        Args:
            indicators_df: 包含技术指标的DataFrame
            stock_code: 股票代码（用于日志）

        Returns:
            信号判断结果字典
        """
        if stock_code:
            logger.info(f"对股票 {stock_code} 进行信号判断")

        try:
            judger = SignalJudger(data=indicators_df, tech_period=self.tech_config)
            signal_result = judger.get_signals()

            # 生成信号摘要DataFrame
            summary_df = judger.get_signal_summary(signal_result)

            return {
                "status": "success",
                "signal_result": signal_result,
                "summary_df": summary_df,
                "signal_level": signal_result.signal_level.value,
                "overall_score": signal_result.overall_score,
                "recommendation": signal_result.recommendation,
            }

        except Exception as e:
            logger.warning(f"信号判断失败: {e}")
            return {"status": "failed", "error": str(e)}

    def save_indicators(self, indicators_df: pd.DataFrame, stock_code: str) -> str:
        """
        保存技术指标结果

        Args:
            indicators_df: 包含技术指标的DataFrame
            stock_code: 股票代码

        Returns:
            保存的文件名（不含扩展名）
        """
        output_file = f"{stock_code}_with_indicators"
        self.ak_fund.save_data(indicators_df, file_name=output_file, file_type="csv")
        return output_file

    def save_signals(self, summary_df: pd.DataFrame, stock_code: str) -> str:
        """
        保存信号判断结果

        Args:
            summary_df: 信号摘要DataFrame
            stock_code: 股票代码

        Returns:
            保存的文件名（不含扩展名）
        """
        signal_file = f"{stock_code}_signals"
        self.ak_fund.save_data(summary_df, file_name=signal_file, file_type="csv")
        return signal_file
