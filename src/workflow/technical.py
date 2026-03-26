"""
技术指标计算工作流
为基金持仓股票计算技术指标
"""

from typing import Dict, List, Any, Optional
import pandas as pd
from tqdm import tqdm

from .base import BaseWorkflow
from src.utils.logger import logger
from src.notify import notify, MessagePriority


class TechnicalIndicatorWorkflow(BaseWorkflow):
    """技术指标计算工作流"""

    def _process_single_stock(
        self, stock_code: str, stock_kline: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        处理单只股票的技术指标计算

        Args:
            stock_code: 股票代码
            stock_kline: 股票K线数据

        Returns:
            处理结果字典
        """
        try:
            # 计算技术指标
            indicators_df = self.calculate_technical_indicators(stock_kline, stock_code)

            # 保存技术指标结果
            output_file = self.save_indicators(indicators_df, stock_code)

            # 进行信号判断
            signal_result = self.calculate_signals(indicators_df, stock_code)

            if signal_result["status"] == "success":
                # 保存信号判断结果
                signal_file = self.save_signals(signal_result["summary_df"], stock_code)

                logger.info(
                    f"  股票 {stock_code} 信号判断完成: {signal_result['signal_level']} "
                    f"(得分: {signal_result['overall_score']:.3f})"
                )

                # 发送股票信号通知（仅对买入/强烈买入信号）
                if signal_result["signal_level"] in ["强烈买入", "买入"]:
                    notify.send_template(
                        "stock_recommendation",
                        stock_code=stock_code,
                        signal_level=signal_result["signal_level"],
                        score=signal_result["overall_score"],
                        recommendation=signal_result["recommendation"],
                        priority=MessagePriority.HIGH
                        if signal_result["signal_level"] == "强烈买入"
                        else MessagePriority.DEFAULT,
                    )

                return {
                    "status": "success",
                    "rows": len(indicators_df),
                    "columns": len(indicators_df.columns),
                    "file": output_file,
                    "signal_file": signal_file,
                    "signal_level": signal_result["signal_level"],
                    "overall_score": signal_result["overall_score"],
                    "recommendation": signal_result["recommendation"],
                }
            else:
                logger.warning(
                    f"  股票 {stock_code} 信号判断失败: {signal_result.get('error', '未知错误')}"
                )
                return {
                    "status": "success",
                    "rows": len(indicators_df),
                    "columns": len(indicators_df.columns),
                    "file": output_file,
                    "signal_error": signal_result.get("error", "未知错误"),
                }

        except Exception as e:
            logger.error(f"计算股票 {stock_code} 的技术指标时出错: {e}")
            return {"status": "failed", "error": str(e)}

    def process_fund(self, fund_code: str) -> Dict[str, Any]:
        """
        处理单个基金的技术指标计算

        Args:
            fund_code: 基金代码

        Returns:
            处理结果字典
        """
        logger.info(f"开始处理基金 {fund_code} 的持仓股票技术指标计算")

        try:
            # 1. 获取基金持仓数据
            fund_info = self.get_fund_holdings(fund_code)
            if fund_info.empty:
                logger.error(f"基金 {fund_code} 的持仓数据为空")
                return {
                    "status": "failed",
                    "reason": "持仓数据为空",
                    "fund_code": fund_code,
                }

            # 2. 过滤出最新季度的持仓
            quarter_summary = self.filter_latest_quarter(fund_info)
            stock_codes = quarter_summary["股票代码"].unique().tolist()

            logger.info(f"最新季度持仓股票数量: {len(stock_codes)}")
            logger.info(
                f"股票代码列表: {stock_codes[:10]}{'...' if len(stock_codes) > 10 else ''}"
            )

            # 3. 批量获取股票K线数据
            stock_data_map = self.get_stock_data(stock_codes)

            if not stock_data_map:
                logger.error("没有成功获取任何股票数据，程序退出")
                return {
                    "status": "failed",
                    "reason": "无股票数据",
                    "fund_code": fund_code,
                }

            # 4. 计算技术指标并保存结果
            logger.info("开始计算技术指标和信号判断")
            results = {}

            # 使用并发处理计算技术指标
            if len(stock_data_map) > 1 and self.max_workers > 1:
                stock_items = list(stock_data_map.items())

                def process_item(item):
                    code, kline = item
                    return code, self._process_single_stock(code, kline)

                batch_results = self.processor.process_batch(
                    items=stock_items,
                    processor=process_item,
                    desc=f"计算基金 {fund_code} 持仓股票的指标",
                    show_progress=True,
                )

                for item, result in batch_results.items():
                    if result is not None:
                        code, stock_result = result
                        results[code] = stock_result
            else:
                # 单线程处理
                for stock_code, stock_kline in tqdm(
                    stock_data_map.items(),
                    desc=f"计算基金 {fund_code} 持仓股票的指标",
                    unit="只",
                ):
                    results[stock_code] = self._process_single_stock(
                        stock_code, stock_kline
                    )

            # 5. 生成汇总报告
            success_count = sum(1 for r in results.values() if r["status"] == "success")
            fail_count = len(results) - success_count

            logger.info("=" * 60)
            logger.info(f"基金 {fund_code} 处理完成!")
            logger.info(f"总股票数: {len(stock_codes)}")
            logger.info(f"成功: {success_count}")
            logger.info(f"失败: {fail_count}")
            logger.info("=" * 60)

            # 打印失败的股票
            if fail_count > 0:
                logger.warning("失败的股票:")
                for code, res in results.items():
                    if res["status"] == "failed":
                        logger.warning(f"  {code}: {res.get('error', '未知错误')}")

            logger.info(f"基金 {fund_code} 的所有技术指标已保存为 CSV 文件")

            return {
                "status": "success",
                "fund_code": fund_code,
                "total_stocks": len(stock_codes),
                "success_stocks": success_count,
                "failed_stocks": fail_count,
                "results": results,
            }

        except Exception as e:
            logger.error(f"处理基金 {fund_code} 时失败: {e}", exc_info=True)
            return {"status": "failed", "reason": str(e), "fund_code": fund_code}

    def run_batch(
        self, fund_codes: List[str], prompt_for_analysis: bool = False
    ) -> List[Dict[str, Any]]:
        """
        批量处理多个基金的技术指标计算

        Args:
            fund_codes: 基金代码列表
            prompt_for_analysis: 是否提示进行基金加权平均分析

        Returns:
            所有基金的处理结果列表
        """
        logger.info(f"开始批量处理 {len(fund_codes)} 个基金的技术指标计算")
        logger.info(f"基金代码列表: {fund_codes}")

        all_results = []

        # 批量处理每个基金
        for fund_code in fund_codes:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"开始处理基金: {fund_code}")

            # 处理单个基金的技术指标计算
            result = self.process_fund(fund_code)
            all_results.append(result)

            logger.info(f"基金 {fund_code} 处理完成")
            logger.info(f"{'=' * 60}\n")

        logger.info(f"\n{'=' * 60}")
        logger.info("批量处理完成!")
        logger.info(f"{'=' * 60}")

        # 输出批量处理结果
        total_funds = len(fund_codes)
        successful_funds = sum(1 for r in all_results if r["status"] == "success")
        failed_funds = total_funds - successful_funds

        logger.info(f"总基金数: {total_funds}")
        logger.info(f"成功处理: {successful_funds}")
        logger.info(f"处理失败: {failed_funds}")

        total_stocks_all = sum(
            r.get("total_stocks", 0) for r in all_results if r["status"] == "success"
        )
        success_stocks_all = sum(
            r.get("success_stocks", 0) for r in all_results if r["status"] == "success"
        )
        failed_stocks_all = sum(
            r.get("failed_stocks", 0) for r in all_results if r["status"] == "success"
        )

        logger.info(f"总股票数（所有基金）: {total_stocks_all}")
        logger.info(f"成功股票数: {success_stocks_all}")
        logger.info(f"失败股票数: {failed_stocks_all}")

        if failed_funds > 0:
            logger.warning("处理失败的基金:")
            for result in all_results:
                if result["status"] == "failed":
                    logger.warning(
                        f"基金 {result['fund_code']}: {result.get('reason', '未知原因')}"
                    )

        logger.info(f"{'=' * 60}")
        logger.info("所有基金的技术指标计算已完成!")
        logger.info(f"{'=' * 60}")

        return all_results
