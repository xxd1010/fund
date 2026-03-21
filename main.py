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


# 技术指标配置
TECHNICAL_INDICATORS_CONFIG = {
    'ma': [3, 5, 10, 14, 20, 30, 45],
    'sma': [3, 5, 10, 14, 20, 30, 45],
    'ema': [12, 26],
    'rsi': [6, 12, 24],
    'macd': ['12-26-9'],
    'boll': ['20-2'],
    'kdj': ['9-3-3'],
    'atr': [10],
    'cci': [20, 26],
    'williams_r': [10],
    'bias': [5, 10, 20, 30, 60, 120, 250],
    'psy': [10],
}


def process_single_fund(fund_code: str, ak_fund: AkFund, rd: DataReader, start_date: str, data_dir: str) -> Dict[str, Any]:
    """处理单个基金代码的持仓股票技术指标计算"""
    logger.info(f"开始处理基金 {fund_code} 的持仓股票技术指标计算")
    
    # 发送开始通知
    notify.send_template("analysis_start", fund_code=fund_code, priority=MessagePriority.DEFAULT)
    
    try:
        # 1. 获取基金持仓数据
        logger.info("步骤1: 获取基金持仓数据")
        fund_info = ak_fund.get_fund_portfolio_hold_em(fund_code=fund_code)
        if fund_info.empty:
            logger.error(f"基金 {fund_code} 的持仓数据为空")
            notify.send_template("error", fund_code=fund_code, error="持仓数据为空", priority=MessagePriority.HIGH)
            return {'status': 'failed', 'reason': '持仓数据为空', 'fund_code': fund_code}

        # 2. 过滤出最新季度的持仓
        logger.info("步骤2: 过滤最新季度数据")
        quarter_summary = filter_latest_quarter_data(fund_info)
        stock_codes = quarter_summary['股票代码'].unique().tolist()

        logger.info(f"最新季度持仓股票数量: {len(stock_codes)}")
        logger.info(f"股票代码列表: {stock_codes[:10]}{'...' if len(stock_codes) > 10 else ''}")

        # 3. 批量获取股票K线数据
        logger.info("步骤3: 批量处理股票数据")
        stock_data_map = {}

        # 使用tqdm显示进度
        for stock_code in tqdm(stock_codes, desc=f"处理基金 {fund_code} 的股票", unit="只"):
            try:
                # 检查是否已有数据文件
                stock_file = f"{data_dir}/{stock_code}_kline.csv"
                existing_files = rd.list_stock_files(data_dir)

                if stock_code in existing_files:
                    # 从本地读取
                    stock_kline = rd.read_stock_kline(
                        symbol=stock_code,
                        data_dir=data_dir
                    )
                else:
                    # 从网络下载
                    stock_kline = ak_fund.get_stock_kline(
                        symbol=stock_code,
                        period='daily',
                        start_date=start_date
                    )
                    # 保存到本地
                    if not stock_kline.empty:
                        ak_fund.save_data(
                            stock_kline,
                            file_name=f'{data_dir}/{stock_code}_kline',
                            file_type='csv'
                        )

                if not stock_kline.empty:
                    stock_data_map[stock_code] = stock_kline
                else:
                    logger.warning(f"股票 {stock_code} 数据为空，跳过")

            except Exception as e:
                logger.error(f"处理股票 {stock_code} 时出错: {e}")
                continue

        logger.info(f"成功获取 {len(stock_data_map)} 只股票的数据")

        if not stock_data_map:
            logger.error("没有成功获取任何股票数据，程序退出")
            return {'status': 'failed', 'reason': '无股票数据', 'fund_code': fund_code}

        # 4. 计算技术指标并保存结果
        logger.info("步骤4: 计算技术指标")
        results = {}

        for stock_code, stock_kline in tqdm(stock_data_map.items(), desc=f"计算基金 {fund_code} 的指标", unit="只"):
            try:
                ti = TI(stock_kline)

                # 配置要计算的指标
                indicators_to_calculate = list(TECHNICAL_INDICATORS_CONFIG.keys())

                # 计算所有指标
                indicators_df = ti.calculate_all(indicators=indicators_to_calculate)

                # 合并原始数据和技术指标
                result = pd.concat([stock_kline.reset_index(drop=True),
                                   indicators_df], axis=1)

                # 保存结果
                output_file = f"{stock_code}_with_indicators"
                ak_fund.save_data(
                    result,
                    file_name=output_file,
                    file_type='csv'
                )

                # 进行信号判断
                logger.info(f"  对股票 {stock_code} 进行信号判断")
                try:
                    judger = SignalJudger(result)
                    signal_result = judger.get_signals()

                    # 生成信号摘要DataFrame
                    summary_df = judger.get_signal_summary(signal_result)

                    # 保存信号判断结果
                    signal_file = f"{stock_code}_signals"
                    ak_fund.save_data(
                        summary_df,
                        file_name=signal_file,
                        file_type='csv'
                    )

                    # 在结果中添加信号判断信息
                    results[stock_code] = {
                        'status': 'success',
                        'rows': len(result),
                        'columns': len(result.columns),
                        'file': output_file,
                        'signal_file': signal_file,
                        'signal_level': signal_result.signal_level.value,
                        'overall_score': signal_result.overall_score,
                        'recommendation': signal_result.recommendation
                    }

                    logger.info(f"  股票 {stock_code} 信号判断完成: {signal_result.signal_level.value} (得分: {signal_result.overall_score:.3f})")

                except Exception as signal_e:
                    logger.warning(f"  信号判断失败: {signal_e}")
                    results[stock_code] = {
                        'status': 'success',
                        'rows': len(result),
                        'columns': len(result.columns),
                        'file': output_file,
                        'signal_error': str(signal_e)
                    }

            except Exception as e:
                logger.error(f"计算股票 {stock_code} 的技术指标时出错: {e}")
                results[stock_code] = {
                    'status': 'failed',
                    'error': str(e)
                }
                continue

        # 5. 生成汇总报告
        logger.info("步骤5: 生成汇总报告")
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
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
                if res['status'] == 'failed':
                    logger.warning(f"  {code}: {res.get('error', '未知错误')}")

        logger.info(f"基金 {fund_code} 的所有技术指标已保存为 CSV 文件")
        
        # 发送完成通知
        notify.send_template("analysis_complete", 
                           fund_code=fund_code, 
                           score=0.0,  # 技术指标计算没有得分，使用0.0
                           recommendation="技术指标计算完成",
                           priority=MessagePriority.DEFAULT)
        
        return {
            'status': 'success',
            'fund_code': fund_code,
            'total_stocks': len(stock_codes),
            'success_stocks': success_count,
            'failed_stocks': fail_count,
            'results': results
        }

    except Exception as e:
        logger.error(f"处理基金 {fund_code} 时失败: {e}", exc_info=True)
        return {'status': 'failed', 'reason': str(e), 'fund_code': fund_code}


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


def show_welcome_message(fund_codes: List[str]):
    """显示欢迎提示和程序功能介绍"""
    logger.info("\n" + "=" * 60)
    logger.info("基金持仓股票分析系统 v1.0")
    logger.info("=" * 60)
    logger.info("功能1：技术指标计算（默认模式）")
    logger.info("  为基金持仓股票计算多种技术指标（MA、RSI、MACD等）")
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
    logger.info(f"执行基金 {fund_code} 的完整加权平均分析流程...")
    
    try:
        # 步骤1: 获取基金持仓数据
        logger.info("【步骤1】获取基金持仓数据")
        fund_info = ak_fund.get_fund_portfolio_hold_em(fund_code=fund_code)
        if fund_info.empty:
            logger.error(f"基金 {fund_code} 的持仓数据为空")
            return {'status': 'failed', 'reason': '持仓数据为空', 'fund_code': fund_code}
        
        # 步骤2: 过滤出最新季度的持仓
        logger.info("【步骤2】过滤最新季度数据")
        quarter_data = filter_latest_quarter_data(fund_info)
        
        if quarter_data.empty:
            logger.error(f"基金 {fund_code} 的季度数据为空")
            return {'status': 'failed', 'reason': '季度数据为空', 'fund_code': fund_code}
        
        stock_codes = quarter_data['股票代码'].unique().tolist()
        logger.info(f"最新季度持仓股票数量: {len(stock_codes)}")
        logger.info(f"股票代码列表: {stock_codes[:10]}{'...' if len(stock_codes) > 10 else ''}")
        
        # 步骤3: 检查股票信号数据是否存在，如不存在则计算技术指标
        logger.info("【步骤3】检查股票信号数据")
        
        # 统计需要计算技术指标的股票
        stocks_to_calculate = []
        for stock_code in stock_codes:
            signal_file = f"data/{stock_code}_signals.csv"
            indicator_file = f"data/{stock_code}_with_indicators.csv"
            
            if not os.path.exists(signal_file) or not os.path.exists(indicator_file):
                stocks_to_calculate.append(stock_code)
        
        if stocks_to_calculate:
            logger.info(f"发现 {len(stocks_to_calculate)} 只股票需要计算技术指标")
            logger.info(f"需要计算的股票: {stocks_to_calculate[:10]}{'...' if len(stocks_to_calculate) > 10 else ''}")
            
            # 批量获取股票K线数据
            logger.info("开始批量获取股票K线数据...")
            stock_data_map = {}
            
            for stock_code in stocks_to_calculate:
                try:
                    # 检查是否已有K线数据文件
                    stock_file = f"{data_dir}/{stock_code}_kline.csv"
                    existing_files = rd.list_stock_files(data_dir)
                    
                    if stock_code in existing_files:
                        # 从本地读取
                        stock_kline = rd.read_stock_kline(
                            symbol=stock_code,
                            data_dir=data_dir
                        )
                    else:
                        # 从网络下载
                        stock_kline = ak_fund.get_stock_kline(
                            symbol=stock_code,
                            period='daily',
                            start_date=start_date
                        )
                        # 保存到本地
                        if not stock_kline.empty:
                            ak_fund.save_data(
                                stock_kline,
                                file_name=f'{data_dir}/{stock_code}_kline',
                                file_type='csv'
                            )
                    
                    if not stock_kline.empty:
                        stock_data_map[stock_code] = stock_kline
                    else:
                        logger.warning(f"股票 {stock_code} 数据为空，跳过")
                        
                except Exception as e:
                    logger.error(f"获取股票 {stock_code} 数据时出错: {e}")
                    continue
            
            logger.info(f"成功获取 {len(stock_data_map)} 只股票的K线数据")
            
            # 计算技术指标并生成信号
            logger.info("开始计算技术指标...")
            for stock_code, stock_kline in stock_data_map.items():
                try:
                    ti = TI(stock_kline)
                    
                    # 配置要计算的指标
                    indicators_to_calculate = list(TECHNICAL_INDICATORS_CONFIG.keys())
                    
                    # 计算所有指标
                    indicators_df = ti.calculate_all(indicators=indicators_to_calculate)
                    
                    # 合并原始数据和技术指标
                    result = pd.concat([stock_kline.reset_index(drop=True),
                                       indicators_df], axis=1)
                    
                    # 保存技术指标结果
                    output_file = f"{stock_code}_with_indicators"
                    ak_fund.save_data(
                        result,
                        file_name=output_file,
                        file_type='csv'
                    )
                    
                    # 进行信号判断
                    logger.info(f"  对股票 {stock_code} 进行信号判断")
                    try:
                        judger = SignalJudger(result)
                        signal_result = judger.get_signals()
                        
                        # 生成信号摘要DataFrame
                        summary_df = judger.get_signal_summary(signal_result)
                        
                        # 保存信号判断结果
                        signal_file = f"{stock_code}_signals"
                        ak_fund.save_data(
                            summary_df,
                            file_name=signal_file,
                            file_type='csv'
                        )
                        
                        logger.info(f"  股票 {stock_code} 信号判断完成: {signal_result.signal_level.value} (得分: {signal_result.overall_score:.3f})")
                        
                    except Exception as signal_e:
                        logger.warning(f"  信号判断失败: {signal_e}")
                        
                except Exception as e:
                    logger.error(f"计算股票 {stock_code} 的技术指标时出错: {e}")
                    continue
        else:
            logger.info("所有股票的信号数据已存在，跳过技术指标计算步骤")
        
        # 步骤4: 进行基金加权平均分析
        logger.info("【步骤4】进行基金加权平均分析")
        analyzer = FundWeightedAnalyzer(data_dir="data")
        
        # 获取基金名称（如果有）
        fund_name = None
        fund_info_file = f"data/fund_info_{fund_code}.csv"
        if os.path.exists(fund_info_file):
            try:
                fund_info_df = pd.read_csv(fund_info_file)
                if not fund_info_df.empty and '基金简称' in fund_info_df.columns:
                    fund_name = fund_info_df.iloc[0]['基金简称']
            except:
                pass
        
        # 执行分析
        analysis_result = analyzer.analyze_fund(
            fund_code=fund_code,
            holdings_df=quarter_data,
            fund_name=fund_name if fund_name else f"基金{fund_code}"
        )
        
        # 步骤5: 生成报告
        logger.info("【步骤5】生成分析报告")
        report_text = analyzer.generate_report(analysis_result)
        report_path = analyzer.save_report(analysis_result)
        
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
                logger.warning(f"  基金 {result['fund_code']}: {result.get('reason', '未知原因')}")

    logger.info(f"\n{'='*60}")
    logger.info("基金加权平均分析已完成!")
    logger.info(f"{'='*60}")


def run_analysis_workflow(fund_codes: List[str], start_date: str, data_dir: str) -> List[Dict[str, Any]]:
    """执行基金加权平均分析流程"""
    logger.info("开始进行基金加权平均分析")
    logger.info(f"基金代码列表: {fund_codes}")

    ak_fund = AkFund()
    rd = DataReader(base_path='data')
    analysis_results = []

    for fund_code in fund_codes:
        logger.info(f"\n{'='*60}")
        logger.info(f"开始分析基金: {fund_code}")
        logger.info(f"{'='*60}")

        result = perform_fund_analysis(fund_code, ak_fund, rd, start_date, data_dir)
        analysis_results.append(result)

        logger.info(f"基金 {fund_code} 分析完成")
        logger.info(f"{'='*60}\n")

    summarize_analysis_results(analysis_results, fund_codes)
    return analysis_results


def run_technical_workflow(
    fund_codes: List[str],
    start_date: str,
    data_dir: str,
    prompt_for_analysis: bool = False
) -> List[Dict[str, Any]]:
    """执行技术指标计算流程"""
    ak_fund = AkFund()
    rd = DataReader(base_path='data')

    logger.info(f"开始批量处理 {len(fund_codes)} 个基金的技术指标计算")
    logger.info(f"基金代码列表: {fund_codes}")
    logger.info(f"开始日期: {start_date}")
    logger.info(f"数据目录: {data_dir}")

    all_results = []

    for fund_code in fund_codes:
        logger.info(f"\n{'='*60}")
        logger.info(f"开始处理基金: {fund_code}")
        logger.info(f"{'='*60}")

        result = process_single_fund(fund_code, ak_fund, rd, start_date, data_dir)
        all_results.append(result)

        logger.info(f"基金 {fund_code} 处理完成")
        logger.info(f"{'='*60}\n")

    logger.info(f"\n{'='*60}")
    logger.info("批量处理完成!")
    logger.info(f"{'='*60}")

    total_funds = len(fund_codes)
    successful_funds = sum(1 for r in all_results if r['status'] == 'success')
    failed_funds = total_funds - successful_funds

    logger.info(f"总基金数: {total_funds}")
    logger.info(f"成功处理: {successful_funds}")
    logger.info(f"处理失败: {failed_funds}")

    total_stocks_all = sum(r.get('total_stocks', 0) for r in all_results if r['status'] == 'success')
    success_stocks_all = sum(r.get('success_stocks', 0) for r in all_results if r['status'] == 'success')
    failed_stocks_all = sum(r.get('failed_stocks', 0) for r in all_results if r['status'] == 'success')

    logger.info(f"总股票数（所有基金）: {total_stocks_all}")
    logger.info(f"成功股票数: {success_stocks_all}")
    logger.info(f"失败股票数: {failed_stocks_all}")

    if failed_funds > 0:
        logger.warning("处理失败的基金:")
        for result in all_results:
            if result['status'] == 'failed':
                logger.warning(f"  基金 {result['fund_code']}: {result.get('reason', '未知原因')}")

    logger.info(f"{'='*60}")
    logger.info("所有基金的技术指标计算已完成!")
    logger.info(f"{'='*60}")

    logger.info("\n" + "=" * 60)
    logger.info("提示: 您可以使用 --analyze 参数进行基金加权平均分析")
    logger.info(f"示例: python main.py --single-fund {fund_codes[0]} --analyze")
    logger.info("这将基于基金持仓股票的持有比例进行加权平均，判断基金是否还能继续持有")
    logger.info("=" * 60)

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
        show_welcome_message(fund_codes)
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

    show_welcome_message(fund_codes)
    run_technical_workflow(fund_codes, start_date, data_dir, prompt_for_analysis=True)


if __name__ == '__main__':
    main()
