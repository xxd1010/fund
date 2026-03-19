"""
主程序入口 - 优化版本
功能：获取基金持仓股票数据并计算技术指标
"""

import logging
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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


def main():
    """主函数"""
    # 初始化
    ak_fund = AkFund()
    rd = DataReader(base_path='data')

    # 配置参数
    FUND_CODE = '005538'
    START_DATE = '2021-01-01'
    DATA_DIR = 'stock_data'

    logger.info(f"开始处理基金 {FUND_CODE} 的持仓股票技术指标计算")

    try:
        # 1. 获取基金持仓数据
        logger.info("步骤1: 获取基金持仓数据")
        fund_info = ak_fund.get_fund_portfolio_hold_em(fund_code=FUND_CODE)
        if fund_info.empty:
            logger.error(f"基金 {FUND_CODE} 的持仓数据为空")
            return

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
        for stock_code in tqdm(stock_codes, desc="处理股票", unit="只"):
            try:
                # 检查是否已有数据文件
                stock_file = f"{DATA_DIR}/{stock_code}_kline.csv"
                existing_files = rd.list_stock_files(DATA_DIR)

                if stock_code in existing_files:
                    # 从本地读取
                    stock_kline = rd.read_stock_kline(
                        symbol=stock_code,
                        data_dir=DATA_DIR
                    )
                else:
                    # 从网络下载
                    stock_kline = ak_fund.get_stock_kline(
                        symbol=stock_code,
                        period='d',
                        start_date=START_DATE
                    )
                    # 保存到本地
                    if not stock_kline.empty:
                        ak_fund.save_data(
                            stock_kline,
                            file_name=f'{DATA_DIR}/{stock_code}_kline',
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
            return

        # 4. 计算技术指标并保存结果
        logger.info("步骤4: 计算技术指标")
        results = {}

        for stock_code, stock_kline in tqdm(stock_data_map.items(), desc="计算指标", unit="只"):
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
        logger.info("处理完成!")
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

        logger.info("所有技术指标已保存为 CSV 文件")

    except Exception as e:
        logger.error(f"程序执行失败: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()