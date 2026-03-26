"""
数据更新模块
重新下载基金持仓和股票K线数据
"""

import os
from typing import List, Dict, Any
from tqdm import tqdm
import pandas as pd

from src.core.data_fetcher import AkFund
from src.data.reader import DataReader
from src.analysis.quarter_filter import filter_latest_quarter_data
from src.notify import notify, MessagePriority
from src.utils.logger import logger


def update_data(fund_codes: List[str], start_date: str, data_dir: str) -> Dict[str, Any]:
    """更新数据：重新下载基金持仓和股票K线数据"""
    logger.info(f"开始更新数据，基金代码: {fund_codes}")
    
    # 发送开始通知
    notify.send("🔄 开始更新数据", priority=MessagePriority.DEFAULT)
    
    ak_fund = AkFund()
    rd = DataReader(base_path='data')
    
    total_results = {
        'status': 'success',
        'fund_codes': fund_codes,
        'fund_results': [],
        'stock_results': []
    }
    
    try:
        # 1. 更新基金持仓数据
        logger.info("步骤1: 更新基金持仓数据")
        fund_data_list = []  # 存储基金持仓数据到内存，避免文件读写问题
        for fund_code in tqdm(fund_codes, desc="更新基金持仓", unit="只"):
            try:
                # 获取最新基金持仓数据
                fund_info = ak_fund.get_fund_portfolio_hold_em(fund_code=fund_code)
                if fund_info.empty:
                    logger.warning(f"基金 {fund_code} 的持仓数据为空")
                    total_results['fund_results'].append({
                        'fund_code': fund_code,
                        'status': 'failed',
                        'reason': '持仓数据为空'
                    })
                    continue

                # 保存基金持仓数据到内存列表
                fund_data_list.append({
                    'fund_code': fund_code,
                    'data': fund_info
                })

                # 保存基金持仓数据到文件
                fund_file = f"fund_portfolio_{fund_code}"
                ak_fund.save_data(
                    fund_info,
                    file_name=fund_file,
                    file_type='csv'
                )
                
                # 获取基金基本信息（可选）
                try:
                    # 尝试获取基金基本信息，如果方法不存在则跳过
                    # 注意：get_fund_info_em 方法可能不存在，使用 try-except 处理
                    fund_basic_info = ak_fund.get_fund_info_em(fund_code=fund_code)
                    if not fund_basic_info.empty:
                        fund_info_file = f"fund_info_{fund_code}"
                        ak_fund.save_data(
                            fund_basic_info,
                            file_name=fund_info_file,
                            file_type='csv'
                        )
                except Exception as e:
                    # 忽略所有异常，因为这是可选功能
                    logger.debug(f"获取基金 {fund_code} 基本信息失败（可选功能）: {e}")
                
                total_results['fund_results'].append({
                    'fund_code': fund_code,
                    'status': 'success',
                    'rows': len(fund_info),
                    'file': fund_file
                })
                
                logger.info(f"基金 {fund_code} 持仓数据更新成功，共 {len(fund_info)} 条记录")
                
            except Exception as e:
                logger.error(f"更新基金 {fund_code} 持仓数据失败: {e}")
                total_results['fund_results'].append({
                    'fund_code': fund_code,
                    'status': 'failed',
                    'reason': str(e)
                })
        
        # 2. 获取所有基金的持仓股票（从内存中读取，避免文件读写问题）
        logger.info("步骤2: 获取所有基金的持仓股票")
        all_stock_codes = set()

        for fund_item in fund_data_list:
            fund_code = fund_item['fund_code']
            fund_df = fund_item['data']
            try:
                # 过滤最新季度数据
                quarter_data = filter_latest_quarter_data(fund_df)
                stock_codes = quarter_data['股票代码'].unique().tolist()
                all_stock_codes.update(stock_codes)
            except Exception as e:
                logger.warning(f"处理基金 {fund_code} 持仓数据失败: {e}")
        
        logger.info(f"需要更新的股票数量: {len(all_stock_codes)}")
        logger.info(f"股票代码列表: {list(all_stock_codes)[:10]}{'...' if len(all_stock_codes) > 10 else ''}")
        
        # 3. 更新股票K线数据
        logger.info("步骤3: 更新股票K线数据")
        for stock_code in tqdm(all_stock_codes, desc="更新股票K线", unit="只"):
            try:
                # 强制从网络下载最新数据（覆盖本地数据）
                stock_kline = ak_fund.get_stock_kline(
                    symbol=stock_code,
                    period='daily',
                    start_date=start_date
                )
                
                if not stock_kline.empty:
                    # 保存K线数据
                    ak_fund.save_data(
                        stock_kline,
                        file_name=f'{data_dir}/{stock_code}_kline',
                        file_type='csv'
                    )
                    
                    total_results['stock_results'].append({
                        'stock_code': stock_code,
                        'status': 'success',
                        'rows': len(stock_kline),
                        'start_date': stock_kline['日期'].min() if '日期' in stock_kline.columns else 'N/A',
                        'end_date': stock_kline['日期'].max() if '日期' in stock_kline.columns else 'N/A'
                    })
                    
                    logger.debug(f"股票 {stock_code} K线数据更新成功，共 {len(stock_kline)} 条记录")
                else:
                    logger.warning(f"股票 {stock_code} K线数据为空")
                    total_results['stock_results'].append({
                        'stock_code': stock_code,
                        'status': 'failed',
                        'reason': 'K线数据为空'
                    })
                    
            except Exception as e:
                logger.error(f"更新股票 {stock_code} K线数据失败: {e}")
                total_results['stock_results'].append({
                    'stock_code': stock_code,
                    'status': 'failed',
                    'reason': str(e)
                })
        
        # 4. 生成汇总报告
        logger.info("步骤4: 生成汇总报告")
        successful_funds = sum(1 for r in total_results['fund_results'] if r['status'] == 'success')
        failed_funds = len(total_results['fund_results']) - successful_funds
        
        successful_stocks = sum(1 for r in total_results['stock_results'] if r['status'] == 'success')
        failed_stocks = len(total_results['stock_results']) - successful_stocks
        
        logger.info("=" * 60)
        logger.info("数据更新完成!")
        logger.info("=" * 60)
        logger.info(f"基金数据: 成功 {successful_funds} / 失败 {failed_funds}")
        logger.info(f"股票数据: 成功 {successful_stocks} / 失败 {failed_stocks}")
        logger.info(f"总更新记录: {successful_funds + successful_stocks} 条")
        logger.info("=" * 60)
        
        # 发送完成通知
        notify.send(f"✅ 数据更新完成\n基金: {successful_funds}成功/{failed_funds}失败\n股票: {successful_stocks}成功/{failed_stocks}失败",
                   priority=MessagePriority.DEFAULT)
        
        return total_results
        
    except Exception as e:
        logger.error(f"数据更新过程中出错: {e}")
        notify.send(f"❌ 数据更新失败: {str(e)[:100]}", priority=MessagePriority.HIGH)
        return {
            'status': 'failed',
            'reason': str(e),
            'fund_codes': fund_codes
        }


def run_update_workflow(fund_codes: List[str], start_date: str, data_dir: str) -> Dict[str, Any]:
    """执行数据更新流程"""
    logger.info("开始数据更新流程")
    logger.info(f"基金代码列表: {fund_codes}")
    logger.info(f"开始日期: {start_date}")
    logger.info(f"数据目录: {data_dir}")
    
    result = update_data(fund_codes, start_date, data_dir)
    
    if result['status'] == 'success':
        logger.info("数据更新流程完成!")
    else:
        logger.error(f"数据更新流程失败: {result.get('reason', '未知原因')}")
    
    return result


if __name__ == "__main__":
    # 测试代码
    import sys
    sys.path.append('.')
    
    from src.utils.logger import setup_logger
    setup_logger(level="INFO")
    
    test_fund_codes = ['005538', '015790']
    test_start_date = '2021-01-01'
    test_data_dir = 'stock_data'
    
    print("测试数据更新模块...")
    result = run_update_workflow(test_fund_codes, test_start_date, test_data_dir)
    print(f"测试结果: {result['status']}")
