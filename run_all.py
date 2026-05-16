"""
自动化执行脚本 - 按顺序执行：更新数据 → 技术指标计算 → 基金加权平均分析
"""

import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import (
    load_config,
    run_update_workflow,
    run_technical_workflow,
    run_analysis_workflow,
    logger,
)
from src.utils.logger import setup_logger
from src.notify import notify


def build_consolidated_message(
    technical_results: List[Dict[str, Any]],
    analysis_results: List[Dict[str, Any]],
    backtest_results: Dict[str, Any]
) -> str:
    """
    将所有执行结果合并到一条消息中

    Args:
        technical_results: 技术指标计算结果
        analysis_results: 基金分析结果
        backtest_results: 回测结果

    Returns:
        合并后的消息字符串
    """
    lines = []

    # 1. 技术指标计算结果汇总
    tech_success = sum(1 for r in technical_results if r.get("status") == "success")
    lines.append(f"📊 技术指标计算: 成功 {tech_success}/{len(technical_results)} 个基金")

    # 2. 基金加权平均分析结果
    successful_funds = [r for r in analysis_results if r.get("status") == "success"]
    if successful_funds:
        fund_lines = []
        for result in successful_funds:
            rec_emoji = "📈" if "买入" in result.get("recommendation", "") else "📉"
            fund_lines.append(
                f"{rec_emoji} {result['fund_code']}: {result.get('recommendation', 'N/A')} "
                f"(得分: {result.get('weighted_score', 0):.3f})"
            )
        lines.append(f"📈 基金分析: 成功 {len(successful_funds)}/{len(analysis_results)} 只基金")
        lines.append("\n".join(fund_lines))
    else:
        lines.append("📈 基金分析: 无成功分析的基金")

    # 3. 股票信号汇总（来自技术指标结果）
    total_stocks = 0
    buy_signals = 0
    stock_lines = []
    for result in technical_results:
        if result.get("status") == "success" and "results" in result:
            for stock_code, stock_result in result["results"].items():
                if stock_result.get("status") == "success":
                    total_stocks += 1
                    signal_level = stock_result.get("signal_level", "")
                    score = stock_result.get("overall_score", 0)
                    if signal_level in ["强烈买入", "买入"]:
                        buy_signals += 1
                        stock_lines.append(f"📈 {stock_code}: {signal_level} (得分: {score:.3f})")

    if stock_lines:
        lines.append(f"📈 股票信号: 共 {total_stocks} 只，其中买入信号 {buy_signals} 只")
        lines.append("\n".join(stock_lines))
    else:
        lines.append(f"📈 股票信号: 共分析 {total_stocks} 只，无强烈买入信号")

    # 4. 回测结果汇总
    if backtest_results:
        successful_backtests = sum(
            1 for r in backtest_results.values()
            if getattr(r, 'metrics', None) is not None
        )
        lines.append(f"📉 回测评估: 成功 {successful_backtests}/{len(backtest_results)} 个基金")
        for fund_code, result in backtest_results.items():
            if getattr(result, 'metrics', None) is not None:
                total_return = result.metrics.get('total_return', 0)
                sharpe = result.metrics.get('sharpe_ratio', 0)
                lines.append(f"  {fund_code}: 收益率 {total_return:.2%}, 夏普比率 {sharpe:.2f}")
    else:
        lines.append("📉 回测评估: 无回测结果")

    return "\n\n".join(lines)


def main():
    """按顺序执行三个操作"""
    setup_logger()

    logger.info("=" * 60)
    logger.info("开始自动化执行流程（按 3→1→2 顺序）")
    logger.info("=" * 60)

    # 加载配置
    config = load_config()
    fund_codes = config.get("fund_codes", ["005538", "015790"])
    start_date = config.get("start_date", "2021-01-01")
    data_dir = config.get("data_dir", "stock_data")

    logger.info(f"配置信息:")
    logger.info(f"  基金代码: {fund_codes}")
    logger.info(f"  开始日期: {start_date}")
    logger.info(f"  数据目录: {data_dir}")
    logger.info("")

    # 步骤1: 更新数据 (操作3)
    logger.info("=" * 60)
    logger.info("[步骤 1/3] 正在执行：更新数据")
    logger.info("=" * 60)
    try:
        update_result = run_update_workflow(fund_codes, start_date, data_dir)
        logger.info(f"✅ 数据更新完成！处理了 {len(update_result)} 个基金")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ 数据更新失败: {e}")
        logger.warning("尝试继续执行后续步骤...")
        logger.info("")

    # 步骤2: 技术指标计算 (操作1)
    logger.info("=" * 60)
    logger.info("[步骤 2/3] 正在执行：技术指标计算")
    logger.info("=" * 60)
    technical_results = []
    try:
        technical_results = run_technical_workflow(
            fund_codes=fund_codes,
            start_date=start_date,
            data_dir=data_dir,
            prompt_for_analysis=False,  # 不提示进行分析，因为下一步会自动执行
        )
        success_count = sum(1 for r in technical_results if r["status"] == "success")
        logger.info(
            f"✅ 技术指标计算完成！成功处理 {success_count}/{len(technical_results)} 个基金"
        )
        logger.info("")
    except Exception as e:
        logger.error(f"❌ 技术指标计算失败: {e}")
        logger.warning("尝试继续执行后续步骤...")
        logger.info("")

    # 步骤3: 基金加权平均分析 (操作2)
    logger.info("=" * 60)
    logger.info("[步骤 3/4] 正在执行：基金加权平均分析")
    logger.info("=" * 60)
    analysis_results = []
    try:
        analysis_results = run_analysis_workflow(fund_codes, start_date, data_dir)

        # 输出汇总报告
        total_funds = len(fund_codes)
        successful_analysis = sum(
            1 for r in analysis_results if r["status"] == "success"
        )
        failed_analysis = total_funds - successful_analysis

        logger.info(f"✅ 基金加权平均分析完成！")
        logger.info(f"   总基金数: {total_funds}")
        logger.info(f"   分析成功: {successful_analysis}")
        logger.info(f"   分析失败: {failed_analysis}")

        if successful_analysis > 0:
            logger.info("\n成功分析的基金结果:")
            logger.info("-" * 60)
            for result in analysis_results:
                if result["status"] == "success":
                    logger.info(f"基金代码: {result['fund_code']}")
                    logger.info(f"基金名称: {result.get('fund_name', 'N/A')}")
                    logger.info(f"加权得分: {result.get('weighted_score', 0):.3f}")
                    logger.info(f"持有建议: {result.get('recommendation', 'N/A')}")
                    logger.info(f"置信度: {result.get('confidence', 0):.1%}")
                    logger.info(f"报告路径: {result.get('report_path', 'N/A')}")
                    logger.info("-" * 60)

        logger.info("")
    except Exception as e:
        logger.error(f"❌ 基金加权平均分析失败: {e}")
        logger.info("")

    # 步骤4: 回测策略评估
    logger.info("=" * 60)
    logger.info("[步骤 4/4] 正在执行：回测策略评估")
    logger.info("=" * 60)
    backtest_results = {}
    try:
        from src.workflow.backtest import BacktestWorkflow
        backtest_workflow = BacktestWorkflow(
            start_date=start_date, data_dir=data_dir, config=config
        )
        backtest_results = backtest_workflow.run_batch(fund_codes)
        successful_backtests = sum(
            1 for r in backtest_results.values()
            if getattr(r, 'metrics', None) is not None
        )
        logger.info(f"✅ 回测策略评估完成！成功评估 {successful_backtests}/{len(backtest_results)} 个基金")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ 回测策略评估失败: {e}")
        logger.info("")

    # 发送综合通知 - 将所有结果合并到一条消息
    try:
        consolidated_message = build_consolidated_message(
            technical_results, analysis_results, backtest_results
        )
        send_notification(title="自动化执行完成", message=consolidated_message)
    except Exception as e:
        logger.error(f"发送综合通知失败: {e}")

    # 完成总结
    logger.info("=" * 60)
    logger.info("自动化执行流程全部完成！")
    logger.info(f"完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


def send_notification(title: str, message: str) -> bool:
    """
    发送通知消息

    Args:
        title: 通知标题
        message: 通知内容

    Returns:
        是否发送成功
    """
    try:
        result = notify.send(message=message, title=title)
        if result:
            logger.info("✅ 通知发送成功！")
        else:
            logger.warning("❌ 通知发送失败！")
        return result
    except Exception as e:
        logger.error(f"❌ 发送通知失败: {e}")
        return False


if __name__ == "__main__":
    main()
