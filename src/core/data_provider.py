"""
数据源提供者基类和接口定义

支持多数据源切换：akshare, baostock
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import pandas as pd


class DataProviderBase(ABC):
    """数据源提供者基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化数据源提供者
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.name = "base"
    
    @abstractmethod
    def get_stock_realtime(self, symbol: str) -> pd.DataFrame:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码（6位数字）
            
        Returns:
            实时行情数据，包含以下标准列：
            - 代码: 股票代码
            - 名称: 股票名称
            - 最新价: 当前价格
            - 涨跌幅: 涨跌幅度(%)
            - 成交量: 成交量
            - 成交额: 成交额
        """
        pass
    
    @abstractmethod
    def get_stock_kline(self, symbol: str, period: str = 'daily', 
                        start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票历史K线数据
        
        Args:
            symbol: 股票代码（6位数字）
            period: 周期，可选值：daily, weekly, monthly
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            K线数据，包含以下标准列：
            - 日期: 交易日期
            - 开盘: 开盘价
            - 收盘: 收盘价
            - 最高: 最高价
            - 最低: 最低价
            - 成交量: 成交量
            - 成交额: 成交额
        """
        pass
    
    @abstractmethod
    def get_stock_financial(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取股票财务指标
        
        Args:
            symbol: 股票代码
            
        Returns:
            财务指标字典，包含：
            - basic: 基本财务指标
            - income: 利润表
            - balance: 资产负债表
            - cash_flow: 现金流量表
        """
        pass
    
    @abstractmethod
    def get_fund_info(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金基本信息
        """
        pass
    
    @abstractmethod
    def get_fund_nav(self, fund_code: str, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取基金历史净值
        
        Args:
            fund_code: 基金代码
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            基金历史净值数据
        """
        pass
    
    @abstractmethod
    def get_fund_portfolio(self, fund_code: str, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取基金持仓
        
        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY-MM-DD，默认最新
            
        Returns:
            基金持仓数据
        """
        pass
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        标准化股票代码为6位数字
        
        Args:
            symbol: 股票代码
            
        Returns:
            6位数字的股票代码
        """
        return str(symbol).zfill(6)
    
    def get_exchange_prefix(self, symbol: str) -> str:
        """
        根据股票代码获取交易所前缀
        
        Args:
            symbol: 股票代码（6位数字）
            
        Returns:
            带交易所前缀的股票代码，如 sh600519, sz000001
        """
        symbol = self.normalize_symbol(symbol)
        
        # 沪市股票代码以6开头，深市以0、3开头，北交所以8开头
        if symbol.startswith('6'):
            return f"sh{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz{symbol}"
        elif symbol.startswith('8') or symbol.startswith('4'):
            return f"bj{symbol}"
        else:
            return symbol
    
    def get_baostock_code(self, symbol: str) -> str:
        """
        根据股票代码获取 baostock 格式的代码
        
        Args:
            symbol: 股票代码（6位数字）
            
        Returns:
            baostock 格式的股票代码，如 sh.600519, sz.000001
        """
        symbol = self.normalize_symbol(symbol)
        
        if symbol.startswith('6'):
            return f"sh.{symbol}"
        elif symbol.startswith('0') or symbol.startswith('3'):
            return f"sz.{symbol}"
        elif symbol.startswith('8') or symbol.startswith('4'):
            return f"bj.{symbol}"
        else:
            return f"sz.{symbol}"  # 默认深市
    
    def standardize_kline_columns(self, df: pd.DataFrame, column_mapping: Dict[str, str]) -> pd.DataFrame:
        """
        标准化K线数据列名
        
        Args:
            df: 原始数据
            column_mapping: 列名映射，{原始列名: 标准列名}
            
        Returns:
            标准化后的数据
        """
        if df.empty:
            return df
        
        # 只重命名存在的列
        rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
        if rename_dict:
            df = df.rename(columns=rename_dict)
        
        return df
