"""
主程序入口 - 优化版本
功能：获取基金持仓股票数据并计算技术指标
"""

import argparse
import json
import os
from typing import List, Dict, Any
from tqdm import tqdm
import pandas as pd

import sys
sys.path.append('.')  # 添加项目根目录到Python路径

from src.core.data_fetcher import AkFund
from src.data.reader import DataReader
from src.indicators.technical_indicators import TechnicalIndicators as TI
from src.analysis.signal_judgment import SignalJudger
from src.analysis.quarter_filter import filter_latest_quarter_data
from src.analysis.fund_weighted_analyzer import FundWeightedAnalyzer
from src.notify import notify, MessagePriority
from src.update_data import run_update_workflow
from src.utils.logger import logger
# 导入新的工作流模块
from src.workflow.technical import TechnicalIndicatorWorkflow
from src.workflow.analysis import FundAnalysisWorkflow


# 技术指标配置
TECHNICAL_INDICATORS_CONFIG = {
    'ma_period': [3, 5, 10, 14, 20, 30, 45],
    'sma_period': [3, 5, 10, 14, 20, 30, 45],
    'ema_period': [12, 26],
    'rsi_period': [6,12,24],
    'macd_period': ['12-26-9'],
    'boll_period': ['20-2'],
    'kdj_period': ['9-3-3'],
    'atr_period': [10],
    'cci_period': [20, 26],
    'williams_r_period': [10],
    'bias_period': [5, 10, 20, 30, 60, 120, 250],
    'psy_period': [10],
    'rsv_period': [10],
    'volume_period': [20]
}


def process_single_fund(
    fund_code: str,
    ak_fund: AkFund,
    rd: DataReader,
    start_date: str,
    data_dir: str
    ) -> Dict[str, Any]:
    """处理单个基金代码的持仓股票技术指标计算"""
    # 使用新的工作流（忽略传入的ak_fund和rd，工作流会自己创建）
    workflow = TechnicalIndicatorWorkflow(start_date=start_date, data_dir=data_dir)
    return workflow.process_fund(fund_code)


def show_main_menu() -> int:
    """显示主菜单并获取用户选择"""
    print("\n" + "=" * 60)
    print("基金持仓股票分析系统 v1.0")
    print("=" * 60)
    print("请选择要执行的操作：")
    print("1. 技术指标计算（为基金持仓股票计算技术指标）")
    print("2. 基金加权平均分析（基于持仓比例判断基金是否值得继续持有）")
    print("3. 更新数据（重新下载基金持仓和股票K线数据）")
    print("4. 退出程序")
    print("=" * 60)
    
    try:
        choice = input("请输入选项编号 (1-4): ")
        return int(choice)
    except (ValueError, EOFError, KeyboardInterrupt):
        return 0


def show_welcome_message():
    """显示欢迎提示和程序功能介绍"""
    logger.info("\n" + "=" * 60)
    logger.info("基金持仓股票分析系统 v1.0")
    logger.info("=" * 60)
    logger.info("功能1：技术指标计算（默认模式）")
    logger.info("   为基金持仓股票计算多种技术指标（MA、RSI、MACD等）")
    logger.info("")
    logger.info("功能2：基金加权平均分析")
    logger.info("  基于持仓股票的持有比例进行加权分析，判断基金是否值得继续持有")
    logger.info("")
    logger.info("功能3：更新数据")
    logger.info("  重新下载基金持仓和股票K线数据，更新到最新")
    logger.info("")
    logger.info("使用方式：")
    logger.info("  python main.py                        # 交互式菜单")
    logger.info("  python main.py --single-fund 005538   # 处理单个基金")
    logger.info("  python main.py --analyze --single-fund 005538   # 分析单个基金")
    logger.info("  python main.py --analyze --fund-codes 005538 015790  # 分析多个基金")
    logger.info("=" * 60 + "\n")


def ask_for_analysis(fund_codes: List[str]) -> bool:
    """询问用户是否要进行基金加权平均分析"""
    print("\n" + "=" * 60)
    print("技术指标计算已完成！")
    print("=" * 60)
    
    if len(fund_codes) == 1:
        print(f"您刚才处理的基金代码：{fund_codes[0]}")
    else:
        print(f"您刚才处理的基金代码：{fund_codes}")
    
    print("现在是否要进行基金加权平均分析？这将基于持仓比例判断基金是否值得继续持有。")
    
    try:
        answer = input("输入 'y' 继续分析，输入其他键退出: ")
        return answer.lower() == 'y'
    except (EOFError, KeyboardInterrupt):
        # 非交互式环境或用户中断，默认不进行分析
        print("非交互式环境，跳过加权平均分析。")
        return False


def load_config(config_path: str = 'config.json') -> Dict[str, Any]:
    """加载配置文件"""
    default_config = {
        'fund_codes': ['005538', '015790'],
        'start_date': '2021-01-01',
        'data_dir': 'stock_data'
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 合并默认配置和用户配置
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
            return config
        except Exception as e:
            logger.warning(f"加载配置文件失败: {e}，使用默认配置")
            return default_config
    else:
        logger.info(f"配置文件 {config_path} 不存在，使用默认配置")
        return default_config


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='基金持仓股票技术指标计算程序')
    parser.add_argument('--fund-codes', type=str, nargs='+', 
                       help='基金代码列表，例如：--fund-codes 005538 015790 000001')
    parser.add_argument('--config', type=str, default='config.json',
                       help='配置文件路径，默认：config.json')
    parser.add_argument('--start-date', type=str,
                       help='开始日期，格式：YYYY-MM-DD')
    parser.add_argument('--data-dir', type=str,
                       help='数据存储目录')
    parser.add_argument('--single-fund', type=str,
                       help='处理单个基金代码，例如：--single-fund 005538')
    parser.add_argument('--analyze', action='store_true',
                       help='进行基金加权平均分析，判断基金是否还能继续持有')
    
    return parser.parse_args()


def perform_fund_analysis(fund_code: str, ak_fund: AkFund, rd: DataReader,
                         start_date: str, data_dir: str) -> Dict[str, Any]:
    """执行基金加权平均分析（完整流程化：获取数据-计算指标-计算加权）"""
    # 使用新的工作流（忽略传入的ak_fund和rd，工作流会自己创建）
    workflow = FundAnalysisWorkflow(start_date=start_date, data_dir=data_dir)
    return workflow.analyze_fund(fund_code)


def summarize_analysis_results(analysis_results: List[Dict[str, Any]], fund_codes: List[str]) -> None:
    """输出基金加权平均分析汇总结果"""
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


def run_analysis_workflow(fund_codes: List[str], start_date: str, data_dir: str) -> List[Dict[str, Any]]:
    """执行基金加权平均分析流程"""
    # 使用新的工作流
    workflow = FundAnalysisWorkflow(start_date=start_date, data_dir=data_dir)
    analysis_results = workflow.run_batch(fund_codes)
    return analysis_results


def run_technical_workflow(
    fund_codes: List[str],
    start_date: str,
    data_dir: str,
    prompt_for_analysis: bool = False
) -> List[Dict[str, Any]]:
    """执行技术指标计算流程"""
    # 使用新的工作流
    workflow = TechnicalIndicatorWorkflow(start_date=start_date, data_dir=data_dir)
    all_results = workflow.run_batch(fund_codes, prompt_for_analysis)

    if prompt_for_analysis:
        try:
            if ask_for_analysis(fund_codes):
                successful_fund_codes = [
                    result['fund_code']
                    for result in all_results
                    if result['status'] == 'success'
                ]

                if not successful_fund_codes:
                    logger.warning("没有成功处理的基金，无法进行分析")
                    return all_results

                logger.info(f"将对以下基金进行加权平均分析: {successful_fund_codes}")
                run_analysis_workflow(successful_fund_codes, start_date, data_dir)
            else:
                logger.info("用户选择退出，程序结束。")
        except Exception as e:
            logger.error(f"交互式分析过程中出错: {e}")
            logger.info("程序正常结束。")

    return all_results


def should_use_interactive_menu(args: argparse.Namespace) -> bool:
    """判断是否进入交互式菜单"""
    has_cli_action = any([
        args.analyze,
        args.single_fund,
        args.fund_codes,
        args.start_date,
        args.data_dir,
        args.config != 'config.json',
    ])
    return not has_cli_action and sys.stdin.isatty()


def main():
    """主函数"""
    args = parse_arguments()
    config = load_config(args.config)

    if args.single_fund:
        fund_codes = [args.single_fund]
        logger.info(f"处理单个基金: {args.single_fund}")
    elif args.fund_codes:
        fund_codes = args.fund_codes
        logger.info(f"使用命令行参数指定的基金代码: {fund_codes}")
    else:
        fund_codes = config.get('fund_codes', ['005538', '015790'])
        logger.info(f"使用配置文件中的基金代码: {fund_codes}")

    start_date = args.start_date if args.start_date else config.get('start_date', '2021-01-01')
    data_dir = args.data_dir if args.data_dir else config.get('data_dir', 'stock_data')

    if should_use_interactive_menu(args):
        # show_welcome_message()
        choice = show_main_menu()

        if choice == 1:
            run_technical_workflow(fund_codes, start_date, data_dir, prompt_for_analysis=True)
        elif choice == 2:
            run_analysis_workflow(fund_codes, start_date, data_dir)
        elif choice == 3:
            run_update_workflow(fund_codes, start_date, data_dir)
        elif choice == 4:
            logger.info("用户选择退出，程序结束。")
        else:
            logger.warning("无效选项，程序结束。")
        return

    if args.analyze:
        run_analysis_workflow(fund_codes, start_date, data_dir)
        return

if __name__ == '__main__':
    main()
