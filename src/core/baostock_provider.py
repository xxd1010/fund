"""
baostock 数据提供者实现

基于 baostock 库的数据获取，提供更稳定的数据源
"""

import baostock as bs
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time

from src.utils import logger
from .data_provider import DataProviderBase


class BaostockProvider(DataProviderBase):
    """baostock 数据提供者"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化 baostock 数据提供者
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.name = "baostock"
        self.connected = False
        self.login()
    
    def login(self) -> bool:
        """
        登录 baostock 系统
        
        Returns:
            是否登录成功
        """
        try:
            lg = bs.login()
            if lg.error_code == '0':
                logger.info("baostock 登录成功")
                self.connected = True
                return True
            else:
                logger.error(f"baostock 登录失败: {lg.error_msg}")
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"baostock 登录异常: {e}")
            self.connected = False
            return False
    
    def logout(self):
        """登出 baostock 系统"""
        if self.connected:
            bs.logout()
            self.connected = False
            logger.info("baostock 已登出")
    
    def ensure_connected(self) -> bool:
        """
        确保 baostock 连接正常
        
        Returns:
            是否连接正常
        """
        if not self.connected:
            return self.login()
        return True
    
    def get_stock_realtime(self, symbol: str) -> pd.DataFrame:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码（6位数字）
            
        Returns:
            实时行情数据
        """
        if not self.ensure_connected():
            logger.error("baostock 连接失败，无法获取实时行情")
            return pd.DataFrame()
        
        try:
            symbol = self.normalize_symbol(symbol)
            bs_code = self.get_baostock_code(symbol)
            
            # 获取实时行情数据
            rs = bs.query_stock_basic(code=bs_code)
            if rs.error_code != '0':
                logger.error(f"获取股票基本信息失败: {rs.error_msg}")
                return pd.DataFrame()
            
            # 获取实时行情
            rs = bs.query_stock_quote(code=bs_code)
            if rs.error_code != '0':
                logger.error(f"获取股票实时行情失败: {rs.error_msg}")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 标准化列名
            column_mapping = {
                'code': '代码',
                'code_name': '名称',
                'open': '今开',
                'high': '最高',
                'low': '最低',
                'close': '最新价',
                'preclose': '昨收',
                'volume': '成交量',
                'amount': '成交额',
                'turn': '换手率',
                'pctChg': '涨跌幅',
                'peTTM': '市盈率',
                'pbMRQ': '市净率',
                'psTTM': '市销率',
                'pcfNcfTTM': '市现率',
                'isST': '是否ST'
            }
            
            df = self.standardize_kline_columns(df, column_mapping)
            
            # 添加标准列
            if '代码' in df.columns:
                df['代码'] = df['代码'].str.replace('.', '')
            
            logger.info(f"baostock 获取股票 {symbol} 实时行情成功")
            return df
            
        except Exception as e:
            logger.error(f"获取股票实时行情失败: {e}")
            return pd.DataFrame()
    
    def get_stock_kline(self, symbol: str, period: str = 'daily', 
                        start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        获取股票历史K线数据
        
        Args:
            symbol: 股票代码（6位数字）
            period: 周期，可选值：daily, weekly, monthly
            start_date: 开始日期，格式：YYYY-MM-DD
            end_date: 结束日期，格式：YYYY-MM-DD
            
        Returns:
            K线数据
        """
        if not self.ensure_connected():
            logger.error("baostock 连接失败，无法获取K线数据")
            return pd.DataFrame()
        
        try:
            symbol = self.normalize_symbol(symbol)
            bs_code = self.get_baostock_code(symbol)
            
            # 设置默认日期范围
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            # 根据周期选择不同的函数
            if period == 'daily':
                rs = bs.query_history_k_data_plus(
                    code=bs_code,
                    fields="date,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="d",
                    adjustflag="3"  # 前复权
                )
            elif period == 'weekly':
                rs = bs.query_history_k_data_plus(
                    code=bs_code,
                    fields="date,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="w",
                    adjustflag="3"  # 前复权
                )
            elif period == 'monthly':
                rs = bs.query_history_k_data_plus(
                    code=bs_code,
                    fields="date,open,high,low,close,volume,amount,turn,pctChg",
                    start_date=start_date,
                    end_date=end_date,
                    frequency="m",
                    adjustflag="3"  # 前复权
                )
            else:
                logger.error(f"不支持的周期: {period}")
                return pd.DataFrame()
            
            if rs.error_code != '0':
                logger.error(f"获取K线数据失败: {rs.error_msg}")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())
            
            if not data_list:
                return pd.DataFrame()
            
            df = pd.DataFrame(data_list, columns=rs.fields)
            
            # 标准化列名
            column_mapping = {
                'date': '日期',
                'open': '开盘',
                'high': '最高',
                'low': '最低',
                'close': '收盘',
                'volume': '成交量',
                'amount': '成交额',
                'turn': '换手率',
                'pctChg': '涨跌幅'
            }
            
            df = self.standardize_kline_columns(df, column_mapping)
            
            # 数据类型转换
            numeric_cols = ['开盘', '最高', '最低', '收盘', '成交量', '成交额', '换手率', '涨跌幅']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            if '日期' in df.columns:
                df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
            
            logger.info(f"baostock 获取股票 {symbol} {period} K线数据成功，共 {len(df)} 条")
            return df
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_financial(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取股票财务指标
        
        Args:
            symbol: 股票代码
            
        Returns:
            财务指标字典
        """
        if not self.ensure_connected():
            logger.error("baostock 连接失败，无法获取财务数据")
            return {}
        
        try:
            symbol = self.normalize_symbol(symbol)
            bs_code = self.get_baostock_code(symbol)
            
            financial_data = {}
            
            # 获取最新年报
            current_year = datetime.now().year
            year_list = [str(y) for y in range(current_year - 5, current_year + 1)]
            
            # 1. 获取利润表
            try:
                income_list = []
                for year in year_list:
                    for quarter in [1, 2, 3, 4]:
                        rs = bs.query_profit_data(code=bs_code, year=year, quarter=quarter)
                        if rs.error_code == '0':
                            while rs.next():
                                income_list.append(rs.get_row_data())
                
                if income_list:
                    df_income = pd.DataFrame(income_list, columns=rs.fields)
                    financial_data['income'] = df_income
            except Exception as e:
                logger.warning(f"获取利润表失败: {e}")
            
            # 2. 获取资产负债表
            try:
                balance_list = []
                for year in year_list:
                    for quarter in [1, 2, 3, 4]:
                        rs = bs.query_balance_data(code=bs_code, year=year, quarter=quarter)
                        if rs.error_code == '0':
                            while rs.next():
                                balance_list.append(rs.get_row_data())
                
                if balance_list:
                    df_balance = pd.DataFrame(balance_list, columns=rs.fields)
                    financial_data['balance'] = df_balance
            except Exception as e:
                logger.warning(f"获取资产负债表失败: {e}")
            
            # 3. 获取现金流量表
            try:
                cashflow_list = []
                for year in year_list:
                    for quarter in [1, 2, 3, 4]:
                        rs = bs.query_cash_flow_data(code=bs_code, year=year, quarter=quarter)
                        if rs.error_code == '0':
                            while rs.next():
                                cashflow_list.append(rs.get_row_data())
                
                if cashflow_list:
                    df_cashflow = pd.DataFrame(cashflow_list, columns=rs.fields)
                    financial_data['cash_flow'] = df_cashflow
            except Exception as e:
                logger.warning(f"获取现金流量表失败: {e}")
            
            # 4. 获取成长能力指标
            try:
                growth_list = []
                for year in year_list:
                    for quarter in [1, 2, 3, 4]:
                        rs = bs.query_growth_data(code=bs_code, year=year, quarter=quarter)
                        if rs.error_code == '0':
                            while rs.next():
                                growth_list.append(rs.get_row_data())
                
                if growth_list:
                    df_growth = pd.DataFrame(growth_list, columns=rs.fields)
                    financial_data['growth'] = df_growth
            except Exception as e:
                logger.warning(f"获取成长能力指标失败: {e}")
            
            # 5. 获取盈利能力指标
            try:
                operation_list = []
                for year in year_list:
                    for quarter in [1, 2, 3, 4]:
                        rs = bs.query_operation_data(code=bs_code, year=year, quarter=quarter)
                        if rs.error_code == '0':
                            while rs.next():
                                operation_list.append(rs.get_row_data())
                
                if operation_list:
                    df_operation = pd.DataFrame(operation_list, columns=rs.fields)
                    financial_data['operation'] = df_operation
            except Exception as e:
                logger.warning(f"获取盈利能力指标失败: {e}")
            
            logger.info(f"baostock 获取股票 {symbol} 财务数据成功")
            return financial_data
            
        except Exception as e:
            logger.error(f"获取财务数据失败: {e}")
            return {}
    
    def get_fund_info(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金基本信息
        """
        # baostock 主要提供股票数据，基金数据有限
        # 这里返回空 DataFrame，建议使用 akshare 获取基金数据
        logger.warning("baostock 基金数据有限，建议使用 akshare 获取基金信息")
        return pd.DataFrame()
    
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
        # baostock 主要提供股票数据，基金数据有限
        logger.warning("baostock 基金数据有限，建议使用 akshare 获取基金净值")
        return pd.DataFrame()
    
    def get_fund_portfolio(self, fund_code: str, date: str = None) -> pd.DataFrame:
        """
        获取基金持仓
        
        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY-MM-DD，默认最新
            
        Returns:
            基金持仓数据
        """
        # baostock 主要提供股票数据，基金数据有限
        logger.warning("baostock 基金数据有限，建议使用 akshare 获取基金持仓")
        return pd.DataFrame()
    
    def __del__(self):
        """析构函数，确保登出"""
        self.logout()


if __name__ == "__main__":
    # 测试 baostock 数据提供者
    provider = BaostockProvider()
    
    # 测试获取股票实时行情
    print("测试获取股票实时行情...")
    realtime = provider.get_stock_realtime('600519')
    if not realtime.empty:
        print(f"实时行情获取成功，数据形状: {realtime.shape}")
        print(realtime.head())
    else:
        print("实时行情获取失败")
    
    # 测试获取股票K线数据
    print("\n测试获取股票K线数据...")
    kline = provider.get_stock_kline('600519', period='daily', 
                                     start_date='2024-01-01', end_date='2024-12-31')
    if not kline.empty:
        print(f"K线数据获取成功，数据形状: {kline.shape}")
        print(kline.head())
    else:
        print("K线数据获取失败")
    
    # 测试获取财务数据
    print("\n测试获取股票财务数据...")
    financial = provider.get_stock_financial('600519')
    if financial:
        print(f"财务数据获取成功，包含 {len(financial)} 个表")
        for key, df in financial.items():
            print(f"  {key}: {df.shape}")
    else:
        print("财务数据获取失败")
    
    provider.logout()