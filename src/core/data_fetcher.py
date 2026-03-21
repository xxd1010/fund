import akshare as ak
import pandas as pd
import json
import time
import os
import sys
from typing import Dict, Any, Callable, Tuple
from datetime import datetime, timedelta
from functools import wraps
from loguru import logger

# 确保从任意位置运行时都能正确导入模块
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.utils import (
    load_config,
    deep_merge_dict,
    retry_decorator,
    normalize_date_range,
    ensure_directory_exists,
    MemoryCache,
)

# 配置日志
_LOGGER_SINK = os.path.abspath("ak_fund.log")
if not globals().get("_AK_FUND_LOGGER_CONFIGURED", False):
    logger.add(_LOGGER_SINK, rotation="10 MB", retention="30 days", level="INFO")
    _AK_FUND_LOGGER_CONFIGURED = True

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
        default_config = {
            'retry_count': 3,
            'retry_interval': 2,
            'storage_path': './data',
            'update_frequency': 60,  # 秒
            'cache_ttl': 60,
            'max_cache_size': 128,
            'data_sources': {
                'stock': 'akshare',
                'fund': 'akshare'
            }
        }
        
        self.config = load_config(config_path, default_config)
        self.retry_count = self.config.get('retry_count', 3)
        self.retry_interval = self.config.get('retry_interval', 2)
        self.storage_path = self.config.get('storage_path', './data')
        self.cache_ttl = int(self.config.get('cache_ttl', 60))
        self.max_cache_size = int(self.config.get('max_cache_size', 128))
        self.cache = MemoryCache(ttl=self.cache_ttl, max_size=self.max_cache_size)
        
        # 创建存储目录
        os.makedirs(self.storage_path, exist_ok=True)
    
    def _get_cached_or_fetch(self, key: str, fetcher: Callable[[], Any], ttl_seconds: int = None) -> Any:
        """
        从缓存获取数据，如果不存在则调用fetcher
        
        Args:
            key: 缓存键
            fetcher: 数据获取函数
            ttl_seconds: 缓存生存时间（秒）
            
        Returns:
            数据
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.cache_ttl
        
        # 尝试从缓存获取
        cached_value = self.cache.get(key)
        if cached_value is not None:
            return cached_value
        
        # 调用fetcher获取数据
        value = fetcher()
        
        # 存入缓存
        self.cache.set(key, value)
        
        return value

    def _normalize_date_range(self, start_date: str = None, end_date: str = None) -> Tuple[str, str]:
        """
        标准化日期范围
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            (标准化开始日期, 标准化结束日期)
        """
        return normalize_date_range(start_date, end_date)

    
    # 重新定义装饰器的使用方式
    def get_stock_realtime(self, symbol: str) -> pd.DataFrame:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码
            
        Returns:
            实时行情数据
        """
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
        def inner():
            logger.info(f"获取股票 {symbol} 实时行情")
            try:
                # 全市场快照请求成本较高，优先使用短时缓存。
                try:
                    snapshot = self._get_cached_or_fetch(
                        key='stock_zh_a_spot_em_snapshot',
                        fetcher=ak.stock_zh_a_spot_em,
                        ttl_seconds=10
                    )
                    data = snapshot[snapshot['代码'] == symbol]
                except Exception:
                    snapshot = self._get_cached_or_fetch(
                        key='stock_zh_a_spot_snapshot',
                        fetcher=ak.stock_zh_a_spot,
                        ttl_seconds=10
                    )
                    data = snapshot[snapshot['symbol'] == symbol]
                
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
        # 确保股票代码是字符串类型
        symbol = str(symbol).zfill(6)  # 转换为字符串并补齐6位
        
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
        # 确保股票代码是字符串类型并补齐6位
        symbol = str(symbol).zfill(6)
        
        start_date, end_date = self._normalize_date_range(start_date, end_date)
        
        # 格式化日期为YYYYMMDD格式
        start_date_fmt = start_date.replace('-', '')
        end_date_fmt = end_date.replace('-', '')

        if period not in {'daily', 'weekly', 'monthly'}:
            raise ValueError(f"不支持的周期: {period}")
        
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
        def inner():
            logger.info(f"获取股票 {symbol} {period} K线数据")
            
            # 尝试多个数据源
            errors = []
            
            # 尝试1：使用东方财富数据源（原始接口）
            try:
                logger.info(f"尝试使用东方财富数据源获取 {symbol} K线数据")
                data = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                )
                
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
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
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
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
        def inner():
            logger.info(f"获取基金 {fund_code} 基本信息")
            
            try:
                # 基金列表变化频率较低，缓存后可减少重复请求。
                fund_list = self._get_cached_or_fetch(
                    key='fund_name_em_list',
                    fetcher=ak.fund_name_em,
                    ttl_seconds=300
                )
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
        start_date, end_date = self._normalize_date_range(start_date, end_date)
        
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
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
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
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
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
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
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
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
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
        def inner():
            logger.info(f"获取基金业绩排名，类型：{rank_type}")
            
            try:
                # 获取基金排名数据
                data = ak.fund_rank_em(date=date)
                
                rank_column_map = {
                    'return_1y': '近1年',
                    'return_2y': '近2年',
                    'return_3y': '近3年',
                    'return_5y': '近5年',
                }
                rank_column = rank_column_map.get(rank_type)
                if not rank_column:
                    raise ValueError(f"不支持的排名类型: {rank_type}")
                data = data.sort_values(rank_column, ascending=False)
                
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
            
            # 仅剔除整行空值，避免过早丢弃有用数据。
            processed_data = processed_data.dropna(how='all')
            
            convert_rules = {
                'stock_realtime': {
                    'datetime_cols': [],
                    'numeric_cols': ['最新价'],
                    'string_cols': ['代码'],
                },
                'stock_kline': {
                    'datetime_cols': ['日期'],
                    'numeric_cols': ['开盘', '最高', '最低', '收盘', '成交量', '成交额'],
                    'string_cols': [],
                },
                'fund_nav': {
                    'datetime_cols': ['净值日期'],
                    'numeric_cols': ['单位净值', '累计净值', '日增长率'],
                    'string_cols': [],
                },
            }
            rule = convert_rules.get(data_type, {'datetime_cols': [], 'numeric_cols': [], 'string_cols': []})

            for col in rule['string_cols']:
                if col in processed_data.columns:
                    processed_data[col] = processed_data[col].astype(str)
            for col in rule['datetime_cols']:
                if col in processed_data.columns:
                    processed_data[col] = pd.to_datetime(processed_data[col], errors='coerce')
            for col in rule['numeric_cols']:
                if col in processed_data.columns:
                    processed_data[col] = pd.to_numeric(processed_data[col], errors='coerce')

            # 类型转换后再剔除全空行。
            processed_data = processed_data.dropna(how='all')
            
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
            file_name: 文件名，支持子目录（如 'stock_data/600519'）
            file_type: 文件类型，可选值：csv, excel
            
        Returns:
            是否保存成功
        """
        logger.info(f"保存数据到 {file_type} 文件: {file_name}")
        
        try:
            # 处理file_name中的子目录路径
            full_path = os.path.join(self.storage_path, file_name)
            directory = os.path.dirname(full_path)
            
            # 创建子目录（如果不存在）
            if directory:
                ensure_directory_exists(directory)
            
            file_path = f"{full_path}.{file_type}"
            
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
