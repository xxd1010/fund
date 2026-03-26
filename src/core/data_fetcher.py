"""
股票与基金数据获取类（支持多数据源切换：akshare/baostock）

这是重构后的版本，使用新的多数据源架构
"""

import pandas as pd
import os
import sys
from typing import Dict, Any, Callable, Tuple, Optional
from datetime import datetime, timedelta

# 确保从任意位置运行时都能正确导入模块
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.utils import (
    load_config,
    retry_decorator,
    normalize_date_range,
    ensure_directory_exists,
    MemoryCache,
    logger,
)

# 导入新的多数据源架构
from .data_factory import MultiSourceDataFetcher


class AkFund:
    """
    股票与基金数据获取类（支持多数据源切换：akshare/baostock）
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
        
        # 初始化多数据源获取器
        self.data_fetcher = MultiSourceDataFetcher(config_path)
    
    def _get_cached_or_fetch(self, key: str, fetcher: Callable[[], Any], ttl_seconds: Optional[int] = None) -> Any:
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
    
    # 数据源切换方法
    def switch_stock_source(self, source_name: str) -> bool:
        """
        切换股票数据源
        
        Args:
            source_name: 数据源名称（akshare/baostock）
            
        Returns:
            是否切换成功
        """
        return self.data_fetcher.switch_stock_source(source_name)
    
    def switch_fund_source(self, source_name: str) -> bool:
        """
        切换基金数据源
        
        Args:
            source_name: 数据源名称（akshare/baostock）
            
        Returns:
            是否切换成功
        """
        return self.data_fetcher.switch_fund_source(source_name)
    
    def get_available_sources(self) -> Dict[str, list]:
        """
        获取可用的数据源
        
        Returns:
            可用数据源字典
        """
        return self.data_fetcher.get_available_sources()
    
    def get_current_sources(self) -> Dict[str, str]:
        """
        获取当前使用的数据源
        
        Returns:
            当前数据源字典
        """
        return {
            'stock': self.data_fetcher.stock_source,
            'fund': self.data_fetcher.fund_source
        }
    
    # 股票数据获取方法
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
                data = self.data_fetcher.get_stock_realtime(symbol)
                if data.empty:
                    logger.warning(f"股票 {symbol} 实时行情数据为空")
                return data
            except Exception as e:
                logger.error(f"获取股票实时行情失败: {e}")
                return pd.DataFrame()
        return inner()
    
    def get_stock_kline(self, symbol: str, period: str = 'daily', 
                        start_date: str = None, end_date: str = None) -> pd.DataFrame:
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
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
        def inner():
            logger.info(f"获取股票 {symbol} {period} K线数据")
            try:
                data = self.data_fetcher.get_stock_kline(symbol, period, start_date, end_date)
                if data.empty:
                    logger.warning(f"股票 {symbol} K线数据为空")
                return data
            except Exception as e:
                logger.error(f"获取股票K线数据失败: {e}")
                raise
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
            try:
                data = self.data_fetcher.get_stock_financial(symbol)
                if not data:
                    logger.warning(f"股票 {symbol} 财务数据为空")
                return data
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
                data = self.data_fetcher.get_fund_info(fund_code)
                if data.empty:
                    logger.warning(f"基金 {fund_code} 基本信息为空")
                return data
            except Exception as e:
                logger.error(f"获取基金基本信息失败: {e}")
                raise
        return inner()
    
    def get_fund_nav(self, fund_code: str, start_date: str = None, 
                     end_date: str = None) -> pd.DataFrame:
        """
        获取基金历史净值
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            基金历史净值数据
        """
        @retry_decorator(max_retries=self.retry_count, delay=self.retry_interval)
        def inner():
            logger.info(f"获取基金 {fund_code} 历史净值")
            try:
                data = self.data_fetcher.get_fund_nav(fund_code, start_date, end_date)
                if data.empty:
                    logger.warning(f"基金 {fund_code} 历史净值数据为空")
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
                data = self.data_fetcher.get_fund_portfolio(fund_code, date)
                if data.empty:
                    logger.warning(f"基金 {fund_code} 持仓数据为空")
                return data
            except Exception as e:
                logger.error(f"获取基金持仓失败: {e}")
                raise
        return inner()
    
    # 兼容性方法（保持与旧版本的兼容性）
    def get_fund_individual_detail_hold_xq(self, fund_code: str, date: str = None) -> pd.DataFrame:
        """
        获取基金 individual_detail_hold_xq（兼容性方法）
        
        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY-MM-DD，默认最新
            
        Returns:
            基金 individual_detail_hold_xq 数据
        """
        logger.warning("get_fund_individual_detail_hold_xq 方法已过时，建议使用 get_fund_portfolio")
        return self.get_fund_portfolio(fund_code, date)
    
    def get_fund_portfolio_hold_em(self, fund_code: str, date: str = None) -> pd.DataFrame:
        """
        获取基金持仓（兼容性方法）
        
        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY，默认最新
            
        Returns:
            基金持仓数据
        """
        logger.warning("get_fund_portfolio_hold_em 方法已过时，建议使用 get_fund_portfolio")
        return self.get_fund_portfolio(fund_code, date)
    
    def get_fund_ranking(self, date: str = None, rank_type: str = 'return_1y') -> pd.DataFrame:
        """
        获取基金业绩排名（兼容性方法）
        
        Args:
            date: 日期，格式：YYYY-MM-DD，默认最新
            rank_type: 排名类型，可选值：return_1y, return_2y, return_3y, return_5y
            
        Returns:
            基金业绩排名数据
        """
        logger.warning("get_fund_ranking 方法需要特定数据源支持，当前使用默认数据源")
        # 这里可以调用 akshare 的特定接口，但为了简化，返回空 DataFrame
        return pd.DataFrame()
    
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
                    'numeric_cols': ['最新价', '涨跌幅', '成交量', '成交额'],
                    'string_cols': ['代码', '名称'],
                },
                'stock_kline': {
                    'datetime_cols': ['日期'],
                    'numeric_cols': ['开盘', '最高', '最低', '收盘', '成交量', '成交额', '涨跌幅'],
                    'string_cols': [],
                },
                'fund_nav': {
                    'datetime_cols': ['净值日期'],
                    'numeric_cols': ['单位净值', '累计净值', '日增长率'],
                    'string_cols': [],
                },
                'fund_portfolio': {
                    'datetime_cols': ['季度'],
                    'numeric_cols': ['持仓市值', '占净值比例'],
                    'string_cols': ['股票代码', '股票名称'],
                }
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
    
    # 显示当前数据源
    print("当前数据源配置:")
    print(f"可用数据源: {ak_fund.get_available_sources()}")
    print(f"当前使用数据源: {ak_fund.get_current_sources()}")
    
    # 示例1：获取股票实时行情
    print("\n示例1：获取股票实时行情...")
    try:
        stock_realtime = ak_fund.get_stock_realtime('600519')
        if not stock_realtime.empty:
            processed_realtime = ak_fund.process_data(stock_realtime, 'stock_realtime')
            ak_fund.save_data(processed_realtime, 'stock_realtime_600519', 'csv')
            print(f"股票实时行情获取成功，数据形状: {stock_realtime.shape}")
            print(f"当前数据源: {ak_fund.get_current_sources()['stock']}")
        else:
            print("股票实时行情获取失败")
    except Exception as e:
        print(f"股票实时行情获取失败: {e}")
    
    # 示例2：切换数据源并获取股票K线数据
    print("\n示例2：切换数据源并获取股票K线数据...")
    try:
        # 尝试切换到 baostock
        if ak_fund.switch_stock_source('baostock'):
            print("已切换到 baostock 数据源")
            print(f"当前数据源: {ak_fund.get_current_sources()['stock']}")
            
            # 获取K线数据
            stock_kline = ak_fund.get_stock_kline('600519', period='daily', 
                                                 start_date='2024-01-01', end_date='2024-12-31')
            if not stock_kline.empty:
                processed_kline = ak_fund.process_data(stock_kline, 'stock_kline')
                ak_fund.save_data(processed_kline, 'stock_kline_600519_baostock', 'csv')
                print(f"股票K线数据获取成功，数据形状: {stock_kline.shape}")
            else:
                print("股票K线数据获取失败")
        else:
            print("无法切换到 baostock 数据源")
    except Exception as e:
        print(f"切换数据源失败: {e}")
    
    # 示例3：获取基金数据
    print("\n示例3：获取基金数据...")
    try:
        fund_info = ak_fund.get_fund_info('000001')
        if not fund_info.empty:
            processed_info = ak_fund.process_data(fund_info, 'fund_info')
            ak_fund.save_data(processed_info, 'fund_info_000001', 'csv')
            print(f"基金信息获取成功，数据形状: {fund_info.shape}")
            print(f"当前数据源: {ak_fund.get_current_sources()['fund']}")
        else:
            print("基金信息获取失败")
    except Exception as e:
        print(f"基金信息获取失败: {e}")
