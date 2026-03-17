import akshare as ak
import pandas as pd
import numpy as np
import json
import time
import os
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
from loguru import logger

# 配置日志
logger.add("ak_fund.log", rotation="10 MB", retention="30 days", level="INFO")

class AkFund:
    """
    基于akshare库的股票与基金数据获取类
    """
    
    def __init__(self, config_path: str = 'config.json'):
        """
        初始化AkFund类
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_interval = self.config.get('retry_interval', 2)
        self.storage_path = self.config.get('storage_path', './data')
        
        # 创建存储目录
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _load_config(self, config_path: str) -> Dict:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置字典
        """
        default_config = {
            'retry_count': 3,
            'retry_interval': 2,
            'storage_path': './data',
            'update_frequency': 60,  # 秒
            'data_sources': {
                'stock': 'akshare',
                'fund': 'akshare'
            }
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
                logger.error(f"加载配置文件失败: {e}")
                return default_config
        else:
            logger.warning(f"配置文件 {config_path} 不存在，使用默认配置")
            return default_config
    
    def _retry_decorator(self, func):
        """
        重试装饰器
        
        Args:
            func: 被装饰的函数
            
        Returns:
            装饰后的函数
        """
        def wrapper(*args, **kwargs):
            for i in range(self.retry_count):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"尝试 {i+1}/{self.retry_count} 失败: {e}")
                    if i < self.retry_count - 1:
                        time.sleep(self.retry_interval)
                    else:
                        logger.error(f"所有尝试都失败: {e}")
                        raise
        return wrapper
    
    # 重新定义装饰器的使用方式
    def get_stock_realtime(self, symbol: str) -> pd.DataFrame:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码
            
        Returns:
            实时行情数据
        """
        @self._retry_decorator
        def inner():
            logger.info(f"获取股票 {symbol} 实时行情")
            try:
                # 尝试多种方法获取实时行情
                try:
                    data = ak.stock_zh_a_spot_em()
                    data = data[data['代码'] == symbol]
                except Exception:
                    try:
                        data = ak.stock_zh_a_spot()
                        data = data[data['symbol'] == symbol]
                    except Exception as e:
                        logger.error(f"获取实时行情失败: {e}")
                        raise
                
                if data.empty:
                    logger.warning(f"未找到股票 {symbol} 的实时行情数据")
                
                return data
            except Exception as e:
                logger.error(f"获取股票实时行情失败: {e}")
                raise
        return inner()
    
    def _get_exchange_prefix(self, symbol: str) -> str:
        """
        根据股票代码获取交易所前缀
        
        Args:
            symbol: 股票代码
            
        Returns:
            带交易所前缀的股票代码
        """
        # 沪市股票代码以6开头，深市以0、3开头
        if symbol.startswith('6'):
            return f"sh{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz{symbol}"
        else:
            return symbol
    
    def get_stock_kline(self, symbol: str, period: str = 'daily', start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票历史K线数据
        
        Args:
            symbol: 股票代码
            period: 周期，可选值：daily, weekly, monthly
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            K线数据
        """
        # 默认时间范围
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            # 默认获取1年数据
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 格式化日期为YYYYMMDD格式
        start_date_fmt = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')
        
        @self._retry_decorator
        def inner():
            logger.info(f"获取股票 {symbol} {period} K线数据")
            
            # 尝试多个数据源
            errors = []
            
            # 尝试1：使用东方财富数据源（原始接口）
            try:
                logger.info(f"尝试使用东方财富数据源获取 {symbol} K线数据")
                if period == 'daily':
                    data = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
                elif period == 'weekly':
                    data = ak.stock_zh_a_hist(symbol=symbol, period="weekly", start_date=start_date, end_date=end_date, adjust="qfq")
                elif period == 'monthly':
                    data = ak.stock_zh_a_hist(symbol=symbol, period="monthly", start_date=start_date, end_date=end_date, adjust="qfq")
                else:
                    raise ValueError(f"不支持的周期: {period}")
                
                if not data.empty:
                    logger.info(f"东方财富数据源成功获取 {len(data)} 条数据")
                    return data
            except Exception as e:
                errors.append(f"东方财富数据源: {e}")
                logger.warning(f"东方财富数据源失败: {e}")
            
            # 尝试2：使用腾讯数据源
            try:
                logger.info(f"尝试使用腾讯数据源获取 {symbol} K线数据")
                symbol_with_prefix = self._get_exchange_prefix(symbol)
                data = ak.stock_zh_a_hist_tx(symbol=symbol_with_prefix, start_date=start_date_fmt, end_date=end_date_fmt)
                
                if not data.empty:
                    # 重命名列以统一格式
                    data = data.rename(columns={
                        'date': '日期',
                        'open': '开盘',
                        'close': '收盘',
                        'high': '最高',
                        'low': '最低',
                        'amount': '成交量'
                    })
                    logger.info(f"腾讯数据源成功获取 {len(data)} 条数据")
                    return data
            except Exception as e:
                errors.append(f"腾讯数据源: {e}")
                logger.warning(f"腾讯数据源失败: {e}")
            
            # 尝试3：使用新浪数据源
            try:
                logger.info(f"尝试使用新浪数据源获取 {symbol} K线数据")
                symbol_with_prefix = self._get_exchange_prefix(symbol)
                data = ak.stock_zh_a_daily(symbol=symbol_with_prefix, start_date=start_date, end_date=end_date, adjust='qfq')
                
                if not data.empty:
                    logger.info(f"新浪数据源成功获取 {len(data)} 条数据")
                    return data
            except Exception as e:
                errors.append(f"新浪数据源: {e}")
                logger.warning(f"新浪数据源失败: {e}")
            
            # 所有数据源都失败
            error_msg = "; ".join(errors)
            logger.error(f"所有数据源都失败: {error_msg}")
            raise Exception(f"无法获取K线数据，所有数据源都失败: {error_msg}")
            
        return inner()
    
    def get_stock_financial(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取股票财务指标
        
        Args:
            symbol: 股票代码
            
        Returns:
            财务指标字典
        """
        @self._retry_decorator
        def inner():
            logger.info(f"获取股票 {symbol} 财务指标")
            
            financial_data = {}
            
            try:
                # 基本财务指标
                try:
                    financial_data['basic'] = ak.stock_financial_indicator(symbol=symbol)
                except Exception as e:
                    logger.warning(f"获取基本财务指标失败: {e}")
                
                # 利润表
                try:
                    financial_data['income'] = ak.stock_profit_statement(symbol=symbol)
                except Exception as e:
                    logger.warning(f"获取利润表失败: {e}")
                
                # 资产负债表
                try:
                    financial_data['balance'] = ak.stock_balance_sheet(symbol=symbol)
                except Exception as e:
                    logger.warning(f"获取资产负债表失败: {e}")
                
                # 现金流量表
                try:
                    financial_data['cash_flow'] = ak.stock_cash_flow(symbol=symbol)
                except Exception as e:
                    logger.warning(f"获取现金流量表失败: {e}")
                
                return financial_data
            except Exception as e:
                logger.error(f"获取股票财务指标失败: {e}")
                raise
        return inner()
    
    # 基金数据获取方法
    def get_fund_info(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金基本信息
        """
        @self._retry_decorator
        def inner():
            logger.info(f"获取基金 {fund_code} 基本信息")
            
            try:
                # 使用更通用的方法获取基金信息
                # 尝试获取基金列表，然后筛选
                fund_list = ak.fund_name_em()
                fund_info = fund_list[fund_list['基金代码'] == fund_code]
                return fund_info
            except Exception as e:
                logger.error(f"获取基金基本信息失败: {e}")
                raise
        return inner()
    
    def get_fund_nav(self, fund_code: str, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取基金历史净值
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            基金历史净值数据
        """
        # 默认时间范围
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            # 默认获取1年数据
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        
        @self._retry_decorator
        def inner():
            logger.info(f"获取基金 {fund_code} 历史净值")
            
            try:
                data = ak.fund_etf_hist_em(symbol=fund_code, start_date=start_date, end_date=end_date)
                return data
            except Exception as e:
                logger.error(f"获取基金历史净值失败: {e}")
                raise
        return inner()
    
    def get_fund_portfolio(self, fund_code: str, date: str = None) -> pd.DataFrame:
        """
        获取基金持仓
        
        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY-MM-DD，默认最新
            
        Returns:
            基金持仓数据
        """
        @self._retry_decorator
        def inner():
            logger.info(f"获取基金 {fund_code} 持仓")
            
            try:
                data = ak.fund_portfolio_holdings_em(symbol=fund_code, date=date)
                return data
            except Exception as e:
                logger.error(f"获取基金持仓失败: {e}")
                raise
        return inner()

    def get_fund_individual_detail_hold_xq(self, fund_code: str, date: str = None) -> pd.DataFrame:
        """
        获取基金 individual_detail_hold_xq

        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY-MM-DD，默认最新

        Returns:
            基金 individual_detail_hold_xq 数据
        """
        @self._retry_decorator
        def inner():
            logger.info(f"获取基金 {fund_code} individual_detail_hold_xq")
            try:
                data = ak.fund_individual_detail_hold_xq(symbol=fund_code, date=date)
                return data
            except Exception as e:
                logger.error(f"获取基金 individual_detail_hold_xq 失败: {e}")
                raise
        return inner()

    def get_fund_portfolio_hold_em(self, fund_code: str, date: str = None) -> pd.DataFrame:
        """
        获取基金持仓

        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY，默认最新

        Returns:
            基金持仓数据
        """
        @self._retry_decorator
        def inner():
            logger.info(f"获取基金 {fund_code} 持仓")

            try:
                data = ak.fund_portfolio_hold_em(symbol=fund_code, date=date)
                return data
            except Exception as e:
                logger.error(f"获取基金持仓失败: {e}")
                raise
        return inner()

    def get_fund_ranking(self, date: str = None, rank_type: str = 'return_1y') -> pd.DataFrame:
        """
        获取基金业绩排名
        
        Args:
            date: 日期，格式：YYYY-MM-DD，默认最新
            rank_type: 排名类型，可选值：return_1y, return_2y, return_3y, return_5y
            
        Returns:
            基金业绩排名数据
        """
        @self._retry_decorator
        def inner():
            logger.info(f"获取基金业绩排名，类型：{rank_type}")
            
            try:
                # 获取基金排名数据
                data = ak.fund_rank_em(date=date)
                
                # 根据排名类型筛选
                if rank_type == 'return_1y':
                    data = data.sort_values('近1年', ascending=False)
                elif rank_type == 'return_2y':
                    data = data.sort_values('近2年', ascending=False)
                elif rank_type == 'return_3y':
                    data = data.sort_values('近3年', ascending=False)
                elif rank_type == 'return_5y':
                    data = data.sort_values('近5年', ascending=False)
                else:
                    raise ValueError(f"不支持的排名类型: {rank_type}")
                
                return data
            except Exception as e:
                logger.error(f"获取基金业绩排名失败: {e}")
                raise
        return inner()
    

    
    # 数据处理功能
    def process_data(self, data: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """
        处理数据
        
        Args:
            data: 原始数据
            data_type: 数据类型，如：stock_realtime, stock_kline, fund_nav等
            
        Returns:
            处理后的数据
        """
        logger.info(f"处理 {data_type} 数据")
        
        if data.empty:
            logger.warning("输入数据为空")
            return data
        
        try:
            # 复制数据以避免修改原始数据
            processed_data = data.copy()
            
            # 通用处理：去除空值
            processed_data = processed_data.dropna()
            
            # 数据类型特定处理
            if data_type == 'stock_realtime':
                # 处理股票实时行情数据
                if '代码' in processed_data.columns:
                    processed_data['代码'] = processed_data['代码'].astype(str)
                if '最新价' in processed_data.columns:
                    processed_data['最新价'] = pd.to_numeric(processed_data['最新价'], errors='coerce')
            
            elif data_type == 'stock_kline':
                # 处理K线数据
                if '日期' in processed_data.columns:
                    processed_data['日期'] = pd.to_datetime(processed_data['日期'])
                for col in ['开盘', '最高', '最低', '收盘', '成交量', '成交额']:
                    if col in processed_data.columns:
                        processed_data[col] = pd.to_numeric(processed_data[col], errors='coerce')
            
            elif data_type == 'fund_nav':
                # 处理基金净值数据
                if '净值日期' in processed_data.columns:
                    processed_data['净值日期'] = pd.to_datetime(processed_data['净值日期'])
                for col in ['单位净值', '累计净值', '日增长率']:
                    if col in processed_data.columns:
                        processed_data[col] = pd.to_numeric(processed_data[col], errors='coerce')
            
            # 去除重复行
            processed_data = processed_data.drop_duplicates()
            
            return processed_data
        except Exception as e:
            logger.error(f"处理数据失败: {e}")
            raise
    
    # 数据存储功能
    def save_data(self, data: pd.DataFrame, file_name: str, file_type: str = 'csv') -> bool:
        """
        保存数据到文件
        
        Args:
            data: 数据
            file_name: 文件名
            file_type: 文件类型，可选值：csv, excel
            
        Returns:
            是否保存成功
        """
        logger.info(f"保存数据到 {file_type} 文件: {file_name}")
        
        try:
            file_path = os.path.join(self.storage_path, f"{file_name}.{file_type}")
            
            if file_type == 'csv':
                data.to_csv(file_path, index=False, encoding='utf-8-sig')
            elif file_type == 'excel':
                data.to_excel(file_path, index=False)
            else:
                raise ValueError(f"不支持的文件类型: {file_type}")
            
            logger.info(f"数据保存成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False

if __name__ == "__main__":
    # 示例用法
    ak_fund = AkFund()
    
    # 示例1：获取股票实时行情
    try:
        stock_realtime = ak_fund.get_stock_realtime('600519')
        processed_realtime = ak_fund.process_data(stock_realtime, 'stock_realtime')
        ak_fund.save_data(processed_realtime, 'stock_realtime_600519', 'csv')
        print("股票实时行情获取成功")
    except Exception as e:
        print(f"股票实时行情获取失败: {e}")
    
    # 示例2：获取股票K线数据
    try:
        stock_kline = ak_fund.get_stock_kline('600519', period='daily', start_date='2023-01-01', end_date='2023-12-31')
        processed_kline = ak_fund.process_data(stock_kline, 'stock_kline')
        ak_fund.save_data(processed_kline, 'stock_kline_600519', 'csv')
        print("股票K线数据获取成功")
    except Exception as e:
        print(f"股票K线数据获取失败: {e}")
    
    # 示例3：获取基金基本信息
    try:
        fund_info = ak_fund.get_fund_info('000001')
        ak_fund.save_data(fund_info, 'fund_info_000001', 'csv')
        print("基金基本信息获取成功")
    except Exception as e:
        print(f"基金基本信息获取失败: {e}")
    
    # 示例4：获取基金历史净值
    try:
        fund_nav = ak_fund.get_fund_nav('000001', start_date='2023-01-01', end_date='2023-12-31')
        processed_nav = ak_fund.process_data(fund_nav, 'fund_nav')
        ak_fund.save_data(processed_nav, 'fund_nav_000001', 'csv')
        print("基金历史净值获取成功")
    except Exception as e:
        print(f"基金历史净值获取失败: {e}")
