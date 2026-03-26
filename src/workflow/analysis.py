"""
基金加权平均分析工作流
基于基金持仓股票的持有比例进行加权平均，判断基金是否值得继续持有
"""

import os
from typing import Dict, List, Any, Optional
import pandas as pd

from .base import BaseWorkflow
from src.analysis.fund_weighted_analyzer import FundWeightedAnalyzer, FundAnalysisResult
from src.notify import notify, MessagePriority
from src.utils.logger import logger


class FundAnalysisWorkflow(BaseWorkflow):
    """基金加权平均分析工作流"""

    def __init__(self,
                 start_date: str = '2021-01-01',
                 data_dir: str = 'stock_data',
                 config: Optional[Dict[str, Any]] = None):
        super().__init__(start_date, data_dir, config)
        self.analyzer = FundWeightedAnalyzer(data_dir="data")

    def get_fund_holdings_for_analysis(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金持仓数据（用于分析，使用get_fund_portfolio_hold_em）

        Args:
            fund_code: 基金代码

        Returns:
            基金持仓DataFrame
        """
        logger.info(f"获取基金 {fund_code} 的持仓数据（用于分析）")
        fund_info = self.ak_fund.get_fund_portfolio_hold_em(fund_code=fund_code)
        if fund_info.empty:
            logger.error(f"基金 {fund_code} 的持仓数据为空")
        return fund_info

    def check_and_calculate_missing_indicators(self,
                                               stock_codes: List[str],
                                               data_dir: str = "data") -> None:
        """
        检查股票信号数据是否存在，如不存在则计算技术指标

        Args:
            stock_codes: 股票代码列表
            data_dir: 数据目录
        """
        # 统计需要计算技术指标的股票
        stocks_to_calculate = []
        for stock_code in stock_codes:
            signal_file = f"{data_dir}/{stock_code}_signals.csv"
            indicator_file = f"{data_dir}/{stock_code}_with_indicators.csv"

            if not os.path.exists(signal_file) or not os.path.exists(indicator_file):
                stocks_to_calculate.append(stock_code)

        if not stocks_to_calculate:
            logger.info("所有股票的信号数据已存在，跳过技术指标计算步骤")
            return

        logger.info(f"发现 {len(stocks_to_calculate)} 只股票需要计算技术指标")
        logger.info(f"需要计算的股票: {stocks_to_calculate[:10]}{'...' if len(stocks_to_calculate) > 10 else ''}")

        # 批量获取股票K线数据
        stock_data_map = self.get_stock_data(stocks_to_calculate)

        if not stock_data_map:
            logger.warning("没有成功获取任何股票数据，跳过技术指标计算")
            return

        logger.info(f"成功获取 {len(stock_data_map)} 只股票的K线数据")

        # 计算技术指标并生成信号
        logger.info("开始计算技术指标...")
        for stock_code, stock_kline in stock_data_map.items():
            try:
                # 计算技术指标
                indicators_df = self.calculate_technical_indicators(stock_kline, stock_code)

                # 保存技术指标结果
                self.save_indicators(indicators_df, stock_code)

                # 进行信号判断
                signal_result = self.calculate_signals(indicators_df, stock_code)

                if signal_result['status'] == 'success':
                    # 保存信号判断结果
                    self.save_signals(signal_result['summary_df'], stock_code)

                    logger.info(f"  股票 {stock_code} 信号判断完成: {signal_result['signal_level']} "
                               f"(得分: {signal_result['overall_score']:.3f})")

                else:
                    logger.warning(f"  股票 {stock_code} 信号判断失败: {signal_result.get('error', '未知错误')}")

            except Exception as e:
                logger.error(f"计算股票 {stock_code} 的技术指标时出错: {e}")
                continue

    def get_fund_name(self, fund_code: str) -> Optional[str]:
        """
        获取基金名称

        Args:
            fund_code: 基金代码

        Returns:
            基金名称，如果获取失败则返回None
        """
        fund_name = None
        fund_info_file = f"data/fund_info_{fund_code}.csv"
        if os.path.exists(fund_info_file):
            try:
                fund_info_df = pd.read_csv(fund_info_file)
                if not fund_info_df.empty and '基金简称' in fund_info_df.columns:
                    fund_name = fund_info_df.iloc[0]['基金简称']
            except:
                pass
        return fund_name

    def analyze_fund(self, fund_code: str) -> Dict[str, Any]:
        """
        执行基金加权平均分析（完整流程化：获取数据-计算指标-计算加权）

        Args:
            fund_code: 基金代码

        Returns:
            分析结果字典
        """
        logger.info(f"执行基金 {fund_code} 的完整加权平均分析流程...")

        try:
            # 步骤1: 获取基金持仓数据
            logger.info("【步骤1】获取基金持仓数据")
            fund_info = self.get_fund_holdings_for_analysis(fund_code)
            if fund_info.empty:
                logger.error(f"基金 {fund_code} 的持仓数据为空")
                return {'status': 'failed', 'reason': '持仓数据为空', 'fund_code': fund_code}

            # 步骤2: 过滤出最新季度的持仓
            logger.info("【步骤2】过滤最新季度数据")
            quarter_data = self.filter_latest_quarter(fund_info)

            if quarter_data.empty:
                logger.error(f"基金 {fund_code} 的季度数据为空")
                return {'status': 'failed', 'reason': '季度数据为空', 'fund_code': fund_code}

            stock_codes = quarter_data['股票代码'].unique().tolist()
            logger.info(f"最新季度持仓股票数量: {len(stock_codes)}")
            logger.info(f"股票代码列表: {stock_codes[:10]}{'...' if len(stock_codes) > 10 else ''}")

            # 步骤3: 检查股票信号数据是否存在，如不存在则计算技术指标
            logger.info("【步骤3】检查股票信号数据")
            self.check_and_calculate_missing_indicators(stock_codes, data_dir="data")

            # 步骤4: 进行基金加权平均分析
            logger.info("【步骤4】进行基金加权平均分析")

            # 获取基金名称（如果有）
            fund_name = self.get_fund_name(fund_code)

            # 执行分析
            analysis_result = self.analyzer.analyze_fund(
                fund_code=fund_code,
                holdings_df=quarter_data,
                fund_name=fund_name if fund_name else f"基金{fund_code}"
            )

            # 步骤5: 生成报告
            logger.info("【步骤5】生成分析报告")
            report_text = self.analyzer.generate_report(analysis_result)
            report_path = self.analyzer.save_report(analysis_result)

            # 打印分析结果
            logger.info("\n" + "=" * 60)
            logger.info(f"基金 {fund_code} 分析结果:")
            logger.info("-" * 60)
            logger.info(f"加权平均得分: {analysis_result.weighted_score:.3f}")
            logger.info(f"基金建议: {analysis_result.fund_recommendation.value}")
            logger.info(f"置信度: {analysis_result.confidence:.1%}")
            logger.info(f"总股票数: {analysis_result.total_stocks}")
            logger.info(f"已分析股票数: {analysis_result.analyzed_stocks}")
            logger.info(f"分析覆盖率: {(analysis_result.analyzed_stocks/analysis_result.total_stocks)*100:.1f}%")
            logger.info("-" * 60)

            # 根据建议显示不同的消息
            from src.analysis.fund_weighted_analyzer import FundRecommendation
            if analysis_result.fund_recommendation in [FundRecommendation.STRONG_BUY, FundRecommendation.BUY]:
                logger.info("✓ 基金建议: 可以继续持有或加仓")
            elif analysis_result.fund_recommendation == FundRecommendation.HOLD:
                logger.info("⦿ 基金建议: 建议持有观望")
            else:
                logger.info("✗ 基金建议: 考虑减仓或卖出")

            logger.info("=" * 60)

            # 发送基金建议通知
            notify.send_template("fund_recommendation",
                               fund_code=fund_code,
                               recommendation=analysis_result.fund_recommendation.value,
                               score=analysis_result.weighted_score,
                               confidence=analysis_result.confidence,
                               priority=MessagePriority.HIGH if analysis_result.weighted_score >= 0.6 else MessagePriority.DEFAULT)

            # 返回分析结果
            return {
                'status': 'success',
                'fund_code': fund_code,
                'fund_name': analysis_result.fund_name,
                'weighted_score': analysis_result.weighted_score,
                'recommendation': analysis_result.fund_recommendation.value,
                'confidence': analysis_result.confidence,
                'total_stocks': analysis_result.total_stocks,
                'analyzed_stocks': analysis_result.analyzed_stocks,
                'report_path': report_path,
                'details': {
                    'signal_distribution': analysis_result.details['signal_distribution'],
                    'holding_distribution': analysis_result.details['holding_distribution']
                }
            }

        except Exception as e:
            logger.error(f"基金 {fund_code} 分析失败: {e}", exc_info=True)
            return {'status': 'failed', 'reason': str(e), 'fund_code': fund_code}

    def run_batch(self, fund_codes: List[str]) -> List[Dict[str, Any]]:
        """
        批量处理多个基金的加权平均分析

        Args:
            fund_codes: 基金代码列表

        Returns:
            所有基金的分析结果列表
        """
        logger.info("开始进行基金加权平均分析")
        logger.info(f"基金代码列表: {fund_codes}")

        analysis_results = []

        for fund_code in fund_codes:
            logger.info(f"\n{'='*60}")
            logger.info(f"开始分析基金: {fund_code}")
            logger.info(f"{'='*60}")

            result = self.analyze_fund(fund_code)
            analysis_results.append(result)

            logger.info(f"基金 {fund_code} 分析完成")
            logger.info(f"{'='*60}\n")

        self.summarize_analysis_results(analysis_results, fund_codes)
        return analysis_results

    def summarize_analysis_results(self,
                                   analysis_results: List[Dict[str, Any]],
                                   fund_codes: List[str]) -> None:
        """
        输出基金加权平均分析汇总结果

        Args:
            analysis_results: 分析结果列表
            fund_codes: 基金代码列表
        """
        logger.info(f"\n{'='*60}")
        logger.info("基金加权平均分析汇总报告")
        logger.info(f"{'='*60}")

        total_funds = len(fund_codes)
        successful_analysis = sum(1 for r in analysis_results if r['status'] == 'success')
        failed_analysis = total_funds - successful_analysis

        logger.info(f"总基金数: {total_funds}")
        logger.info(f"分析成功: {successful_analysis}")
        logger.info(f"分析失败: {failed_analysis}")

        if successful_analysis > 0:
            logger.info("\n成功分析的基金结果:")
            logger.info("-" * 60)

            for result in analysis_results:
                if result['status'] == 'success':
                    logger.info(f"基金代码: {result['fund_code']}")
                    logger.info(f"基金名称: {result.get('fund_name', 'N/A')}")
                    logger.info(f"加权得分: {result.get('weighted_score', 0):.3f}")
                    logger.info(f"持有建议: {result.get('recommendation', 'N/A')}")
                    logger.info(f"置信度: {result.get('confidence', 0):.1%}")
                    logger.info(f"报告路径: {result.get('report_path', 'N/A')}")
                    logger.info("-" * 60)

            recommendations = {}
            for result in analysis_results:
                if result['status'] == 'success':
                    rec = result.get('recommendation', 'N/A')
                    recommendations[rec] = recommendations.get(rec, 0) + 1

            logger.info("\n持有建议分布:")
            for rec, count in recommendations.items():
                percentage = (count / successful_analysis) * 100
                logger.info(f"  {rec}: {count}只 ({percentage:.1f}%)")

        if failed_analysis > 0:
            logger.warning("\n分析失败的基金:")
            for result in analysis_results:
                if result['status'] == 'failed':
                    logger.warning(f"基金 {result['fund_code']}: {result.get('reason', '未知原因')}")

        logger.info(f"\n{'='*60}")
        logger.info("基金加权平均分析已完成!")
        logger.info(f"{'='*60}")