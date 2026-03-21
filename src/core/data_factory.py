"""
数据源工厂类

负责创建和管理不同的数据源提供者
"""

import pandas as pd
from typing import Dict, Any, Optional

from src.utils import logger

from .data_provider import DataProviderBase
from .akshare_provider import AkshareProvider
from .baostock_provider import BaostockProvider


class DataProviderFactory:
    """数据源工厂类"""
    
    _providers = {
        'akshare': AkshareProvider,
        'baostock': BaostockProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_name: str, config: Dict[str, Any] = None) -> DataProviderBase:
        """
        创建数据源提供者
        
        Args:
            provider_name: 提供者名称，可选值：akshare, baostock
            config: 配置字典
            
        Returns:
            数据源提供者实例
        """
        if provider_name not in cls._providers:
            raise ValueError(f"不支持的数据源: {provider_name}，可选值: {list(cls._providers.keys())}")
        
        try:
            provider_class = cls._providers[provider_name]
            provider = provider_class(config)
            logger.info(f"创建数据源提供者: {provider_name}")
            return provider
        except Exception as e:
            logger.error(f"创建数据源提供者 {provider_name} 失败: {e}")
            raise
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取可用的数据源提供者列表
        
        Returns:
            提供者名称列表
        """
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, name: str, provider_class):
        """
        注册新的数据源提供者
        
        Args:
            name: 提供者名称
            provider_class: 提供者类
        """
        if not issubclass(provider_class, DataProviderBase):
            raise TypeError(f"提供者类必须继承自 DataProviderBase")
        
        cls._providers[name] = provider_class
        logger.info(f"注册数据源提供者: {name}")


class MultiSourceDataFetcher:
    """
    多数据源数据获取器
    
    支持根据配置自动切换数据源
    """
    
    def __init__(self, config_path: str = 'config.json'):
        """
        初始化多数据源数据获取器
        
        Args:
            config_path: 配置文件路径
        """
        from src.utils import load_config
        
        default_config = {
            'retry_count': 3,
            'retry_interval': 2,
            'storage_path': './data',
            'update_frequency': 60,
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
        
        # 初始化数据源提供者
        self.providers = {}
        self._init_providers()
        
        # 当前使用的数据源
        self.stock_source = self.config.get('data_sources', {}).get('stock', 'akshare')
        self.fund_source = self.config.get('data_sources', {}).get('fund', 'akshare')
        
        logger.info(f"多数据源数据获取器初始化完成")
        logger.info(f"股票数据源: {self.stock_source}")
        logger.info(f"基金数据源: {self.fund_source}")
    
    def _init_providers(self):
        """初始化所有数据源提供者"""
        for provider_name in DataProviderFactory.get_available_providers():
            try:
                provider = DataProviderFactory.create_provider(provider_name, self.config)
                self.providers[provider_name] = provider
                logger.info(f"初始化数据源提供者: {provider_name}")
            except Exception as e:
                logger.warning(f"初始化数据源提供者 {provider_name} 失败: {e}")
    
    def get_stock_provider(self) -> DataProviderBase:
        """
        获取股票数据源提供者
        
        Returns:
            股票数据源提供者
        """
        if self.stock_source not in self.providers:
            logger.warning(f"股票数据源 {self.stock_source} 不可用，使用默认数据源")
            # 尝试使用其他可用的数据源
            for source in self.providers:
                if source != 'akshare':  # 优先使用非akshare的数据源
                    self.stock_source = source
                    break
            else:
                self.stock_source = 'akshare'  # 默认使用akshare
        
        return self.providers.get(self.stock_source)
    
    def get_fund_provider(self) -> DataProviderBase:
        """
        获取基金数据源提供者
        
        Returns:
            基金数据源提供者
        """
        if self.fund_source not in self.providers:
            logger.warning(f"基金数据源 {self.fund_source} 不可用，使用默认数据源")
            # 基金数据主要依赖 akshare，所以优先使用 akshare
            if 'akshare' in self.providers:
                self.fund_source = 'akshare'
            else:
                # 如果没有 akshare，使用第一个可用的数据源
                for source in self.providers:
                    self.fund_source = source
                    break
        
        return self.providers.get(self.fund_source)
    
    def switch_stock_source(self, source_name: str) -> bool:
        """
        切换股票数据源
        
        Args:
            source_name: 数据源名称
            
        Returns:
            是否切换成功
        """
        if source_name not in self.providers:
            logger.error(f"无法切换到数据源 {source_name}，该数据源不可用")
            return False
        
        self.stock_source = source_name
        logger.info(f"股票数据源已切换到: {source_name}")
        return True
    
    def switch_fund_source(self, source_name: str) -> bool:
        """
        切换基金数据源
        
        Args:
            source_name: 数据源名称
            
        Returns:
            是否切换成功
        """
        if source_name not in self.providers:
            logger.error(f"无法切换到数据源 {source_name}，该数据源不可用")
            return False
        
        self.fund_source = source_name
        logger.info(f"基金数据源已切换到: {source_name}")
        return True
    
    def get_available_sources(self) -> Dict[str, list]:
        """
        获取可用的数据源
        
        Returns:
            可用数据源字典
        """
        return {
            'stock': list(self.providers.keys()),
            'fund': list(self.providers.keys())
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
        provider = self.get_stock_provider()
        return provider.get_stock_realtime(symbol)
    
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
        provider = self.get_stock_provider()
        return provider.get_stock_kline(symbol, period, start_date, end_date)
    
    def get_stock_financial(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取股票财务指标
        
        Args:
            symbol: 股票代码
            
        Returns:
            财务指标字典
        """
        provider = self.get_stock_provider()
        return provider.get_stock_financial(symbol)
    
    # 基金数据获取方法
    def get_fund_info(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金基本信息
        """
        provider = self.get_fund_provider()
        return provider.get_fund_info(fund_code)
    
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
        provider = self.get_fund_provider()
        return provider.get_fund_nav(fund_code, start_date, end_date)
    
    def get_fund_portfolio(self, fund_code: str, date: str = None) -> pd.DataFrame:
        """
        获取基金持仓
        
        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY-MM-DD，默认最新
            
        Returns:
            基金持仓数据
        """
        provider = self.get_fund_provider()
        return provider.get_fund_portfolio(fund_code, date)


if __name__ == "__main__":
    # 测试多数据源数据获取器
    import pandas as pd
    
    print("测试多数据源数据获取器...")
    
    # 创建数据获取器
    fetcher = MultiSourceDataFetcher()
    
    # 显示可用数据源
    print(f"可用数据源: {fetcher.get_available_sources()}")
    print(f"当前股票数据源: {fetcher.stock_source}")
    print(f"当前基金数据源: {fetcher.fund_source}")
    
    # 测试获取股票数据
    print("\n测试获取股票实时行情...")
    realtime = fetcher.get_stock_realtime('600519')
    if not realtime.empty:
        print(f"实时行情获取成功，数据形状: {realtime.shape}")
        print(realtime.head())
    else:
        print("实时行情获取失败")
    
    # 测试切换数据源
    print("\n测试切换股票数据源...")
    if 'baostock' in fetcher.providers:
        success = fetcher.switch_stock_source('baostock')
        if success:
            print(f"已切换到 baostock 数据源")
            
            # 再次测试获取数据
            realtime2 = fetcher.get_stock_realtime('600519')
            if not realtime2.empty:
                print(f"baostock 实时行情获取成功，数据形状: {realtime2.shape}")
                print(realtime2.head())
            else:
                print("baostock 实时行情获取失败")
    else:
        print("baostock 数据源不可用")
    
    # 测试获取基金数据
    print("\n测试获取基金信息...")
    try:
        fund_info = fetcher.get_fund_info('000001')
        if not fund_info.empty:
            print(f"基金信息获取成功，数据形状: {fund_info.shape}")
            print(fund_info.head())
        else:
            print("基金信息获取失败")
    except Exception as e:
        print(f"基金信息获取失败: {e}")