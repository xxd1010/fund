"""
akshare 数据提供者实现

基于 akshare 库的数据获取，重构现有功能
"""

import akshare as ak
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from src.utils import logger
from .data_provider import DataProviderBase


class AkshareProvider(DataProviderBase):
    """akshare 数据提供者"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化 akshare 数据提供者
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.name = "akshare"
    
    def get_stock_realtime(self, symbol: str) -> pd.DataFrame:
        """
        获取股票实时行情
        
        Args:
            symbol: 股票代码（6位数字）
            
        Returns:
            实时行情数据
        """
        try:
            symbol = self.normalize_symbol(symbol)
            logger.info(f"akshare 获取股票 {symbol} 实时行情")
            
            # 尝试多个数据源
            errors = []
            
            # 尝试1：使用 stock_zh_a_spot_em 接口（东方财富）
            try:
                logger.info(f"尝试使用 stock_zh_a_spot_em 接口获取 {symbol} 实时行情")
                snapshot = ak.stock_zh_a_spot_em()
                
                # 查找股票代码列
                code_column = None
                for col in snapshot.columns:
                    col_str = str(col)
                    if '代码' in col_str or 'symbol' in col_str.lower() or 'code' in col_str.lower():
                        code_column = col
                        break
                
                if code_column:
                    data = snapshot[snapshot[code_column].astype(str) == symbol]
                    
                    if not data.empty:
                        logger.info(f"stock_zh_a_spot_em 接口成功获取 {symbol} 实时行情")
                        return data
                    else:
                        errors.append(f"stock_zh_a_spot_em: 未找到股票 {symbol}")
                else:
                    errors.append("stock_zh_a_spot_em: 未找到股票代码列")
                    
            except Exception as e:
                errors.append(f"stock_zh_a_spot_em: {e}")
                logger.warning(f"stock_zh_a_spot_em 接口失败: {e}")
            
            # 尝试2：使用 stock_zh_a_spot 接口
            try:
                logger.info(f"尝试使用 stock_zh_a_spot 接口获取 {symbol} 实时行情")
                snapshot = ak.stock_zh_a_spot()
                
                # 查找股票代码列
                code_column = None
                for col in snapshot.columns:
                    col_str = str(col)
                    if '代码' in col_str or 'symbol' in col_str.lower() or 'code' in col_str.lower():
                        code_column = col
                        break
                
                if code_column:
                    data = snapshot[snapshot[code_column].astype(str) == symbol]
                    
                    if not data.empty:
                        logger.info(f"stock_zh_a_spot 接口成功获取 {symbol} 实时行情")
                        return data
                    else:
                        errors.append(f"stock_zh_a_spot: 未找到股票 {symbol}")
                else:
                    errors.append("stock_zh_a_spot: 未找到股票代码列")
                    
            except Exception as e:
                errors.append(f"stock_zh_a_spot: {e}")
                logger.warning(f"stock_zh_a_spot 接口失败: {e}")
            
            # 尝试3：使用历史K线数据作为实时行情的备选方案
            try:
                logger.info(f"尝试使用历史K线数据作为实时行情备选方案获取 {symbol}")
                # 使用当前日期
                today = datetime.now().strftime("%Y-%m-%d")
                # 获取最近3天的数据，以防今天没有数据
                three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
                
                # 获取最近几天的K线数据，取最新的一条作为实时数据
                kline_data = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=three_days_ago,
                    end_date=today,
                    adjust="qfq"
                )
                if not kline_data.empty:
                    # 取最新的一条数据
                    latest_data = kline_data.iloc[-1:].copy()
                    # 重命名列以匹配实时数据格式
                    latest_data = latest_data.rename(columns={
                        '日期': '时间',
                        '收盘': '最新价',
                        '开盘': '今开',
                        '最高': '最高',
                        '最低': '最低',
                        '成交量': '成交量',
                        '成交额': '成交额'
                    })
                    # 添加股票代码
                    latest_data['代码'] = symbol
                    logger.info(f"使用历史K线数据作为实时行情备选方案获取 {symbol} 成功")
                    return latest_data
                else:
                    errors.append("历史K线数据: 返回空数据")
                    
            except Exception as e:
                errors.append(f"备选方案: {e}")
                logger.warning(f"备选方案失败: {e}")
            
            # 所有数据源都失败
            error_msg = "; ".join(errors)
            logger.error(f"所有实时行情数据源都失败: {error_msg}")
            
            # 返回空DataFrame而不是抛出异常
            logger.warning(f"无法获取实时行情数据，返回空DataFrame")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取股票实时行情失败: {e}")
            return pd.DataFrame()
    
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
            K线数据
        """
        try:
            symbol = self.normalize_symbol(symbol)
            logger.info(f"akshare 获取股票 {symbol} {period} K线数据")
            
            # 设置默认日期范围
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
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
                symbol_with_prefix = self.get_exchange_prefix(symbol)
                start_date_fmt = start_date.replace('-', '')
                end_date_fmt = end_date.replace('-', '')
                data = ak.stock_zh_a_hist_tx(symbol=symbol_with_prefix, 
                                            start_date=start_date_fmt, 
                                            end_date=end_date_fmt)
                
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
                symbol_with_prefix = self.get_exchange_prefix(symbol)
                data = ak.stock_zh_a_daily(symbol=symbol_with_prefix, 
                                          start_date=start_date, 
                                          end_date=end_date, 
                                          adjust='qfq')
                
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
            
        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            raise
    
    def get_stock_financial(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        获取股票财务指标
        
        Args:
            symbol: 股票代码
            
        Returns:
            财务指标字典
        """
        try:
            symbol = self.normalize_symbol(symbol)
            logger.info(f"akshare 获取股票 {symbol} 财务指标")
            
            financial_data = {}
            
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
            
            logger.info(f"akshare 获取股票 {symbol} 财务数据成功")
            return financial_data
            
        except Exception as e:
            logger.error(f"获取财务数据失败: {e}")
            raise
    
    def get_fund_info(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金基本信息
        """
        try:
            logger.info(f"akshare 获取基金 {fund_code} 基本信息")
            
            # 基金列表变化频率较低，缓存后可减少重复请求
            fund_list = ak.fund_name_em()
            fund_info = fund_list[fund_list['基金代码'] == fund_code]
            
            if fund_info.empty:
                logger.warning(f"未找到基金 {fund_code} 的基本信息")
            
            return fund_info
            
        except Exception as e:
            logger.error(f"获取基金基本信息失败: {e}")
            raise
    
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
        try:
            # 设置默认日期范围
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            
            logger.info(f"akshare 获取基金 {fund_code} 历史净值")
            
            data = ak.fund_etf_hist_em(symbol=fund_code, 
                                      start_date=start_date, 
                                      end_date=end_date)
            
            if data.empty:
                logger.warning(f"基金 {fund_code} 历史净值数据为空")
            
            return data
            
        except Exception as e:
            logger.error(f"获取基金历史净值失败: {e}")
            raise
    
    def get_fund_portfolio(self, fund_code: str, date: Optional[str] = None) -> pd.DataFrame:
        """
        获取基金持仓
        
        Args:
            fund_code: 基金代码
            date: 日期，格式：YYYY-MM-DD，默认最新
            
        Returns:
            基金持仓数据
        """
        try:
            logger.info(f"akshare 获取基金 {fund_code} 持仓")
            
            # 尝试多个可能的函数名
            errors = []
            
            # 尝试1：使用 fund_portfolio_holdings_em
            try:
                data = ak.fund_portfolio_hold_em(symbol=fund_code, date=date)
                if not data.empty:
                    logger.info(f"使用 fund_portfolio_hold_em 成功获取基金 {fund_code} 持仓")
                    return data
                else:
                    errors.append("fund_portfolio_hold_em: 返回空数据")
            except AttributeError as e:
                errors.append(f"fund_portfolio_hold_em: {e}")
            except Exception as e:
                errors.append(f"fund_portfolio_hold_em: {e}")
            
            # 所有尝试都失败
            error_msg = "; ".join(errors)
            logger.error(f"所有基金持仓数据源都失败: {error_msg}")
            
            # 返回空DataFrame而不是抛出异常
            logger.warning(f"无法获取基金持仓数据，返回空DataFrame")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"获取基金持仓失败: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    # 测试 akshare 数据提供者
    provider = AkshareProvider()
    
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
    try:
        kline = provider.get_stock_kline('600519', period='daily', 
                                        start_date='2024-01-01', end_date='2024-12-31')
        if not kline.empty:
            print(f"K线数据获取成功，数据形状: {kline.shape}")
            print(kline.head())
        else:
            print("K线数据获取失败")
    except Exception as e:
        print(f"K线数据获取失败: {e}")
    
    # 测试获取财务数据
    print("\n测试获取股票财务数据...")
    try:
        financial = provider.get_stock_financial('600519')
        if financial:
            print(f"财务数据获取成功，包含 {len(financial)} 个表")
            for key, df in financial.items():
                print(f"  {key}: {df.shape}")
        else:
            print("财务数据获取失败")
    except Exception as e:
        print(f"财务数据获取失败: {e}")
    
    # 测试获取基金信息
    print("\n测试获取基金信息...")
    try:
        fund_info = provider.get_fund_info('000001')
        if not fund_info.empty:
            print(f"基金信息获取成功，数据形状: {fund_info.shape}")
            print(fund_info.head())
        else:
            print("基金信息获取失败")
    except Exception as e:
        print(f"基金信息获取失败: {e}")