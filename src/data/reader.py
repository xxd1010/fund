"""
数据读取模块
提供从指定路径读取各类数据文件的功能
"""

import os
import pandas as pd
from typing import Optional, List, Dict, Union
from pathlib import Path
from loguru import logger


class DataReader:
    """
    数据读取器
    
    支持从指定路径读取CSV、Excel等格式的数据文件
    """
    
    def __init__(self, base_path: str = './data'):
        """
        初始化数据读取器
        
        Args:
            base_path: 数据文件的基础路径，默认为 './data'
        """
        self.base_path = base_path
        self._ensure_base_path()
        logger.info(f"数据读取器初始化完成，基础路径: {self.base_path}")
    
    def _ensure_base_path(self):
        """确保基础路径存在"""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path, exist_ok=True)
            logger.info(f"创建数据目录: {self.base_path}")
    
    def read_csv(self, file_path: str, encoding: str = 'utf-8-sig') -> pd.DataFrame:
        """
        读取CSV文件
        
        Args:
            file_path: 文件路径（可以是相对路径或绝对路径）
            encoding: 文件编码，默认 'utf-8-sig'
            
        Returns:
            包含数据的DataFrame
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        full_path = self._get_full_path(file_path)
        logger.info(f"读取CSV文件: {full_path}")
        
        try:
            df = pd.read_csv(full_path, encoding=encoding)
            logger.info(f"成功读取 {len(df)} 行数据")
            return df
        except FileNotFoundError:
            logger.error(f"文件不存在: {full_path}")
            raise
        except Exception as e:
            logger.error(f"读取CSV文件失败: {e}")
            raise ValueError(f"读取CSV文件失败: {e}")
    
    def read_excel(self, file_path: str, sheet_name: Optional[Union[str, int]] = 0) -> pd.DataFrame:
        """
        读取Excel文件
        
        Args:
            file_path: 文件路径
            sheet_name: 工作表名称或索引，默认 0（第一个工作表）
            
        Returns:
            包含数据的DataFrame
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        full_path = self._get_full_path(file_path)
        logger.info(f"读取Excel文件: {full_path}")
        
        try:
            df = pd.read_excel(full_path, sheet_name=sheet_name)
            logger.info(f"成功读取 {len(df)} 行数据")
            return df
        except FileNotFoundError:
            logger.error(f"文件不存在: {full_path}")
            raise
        except Exception as e:
            logger.error(f"读取Excel文件失败: {e}")
            raise ValueError(f"读取Excel文件失败: {e}")
    
    def read_data(self, file_path: str, file_type: Optional[str] = None) -> pd.DataFrame:
        """
        自动识别文件类型并读取数据
        
        Args:
            file_path: 文件路径
            file_type: 文件类型，可选值：'csv', 'excel'，如果为None则自动识别
            
        Returns:
            包含数据的DataFrame
            
        Raises:
            ValueError: 不支持的文件类型
            FileNotFoundError: 文件不存在
        """
        if file_type is None:
            file_type = self._detect_file_type(file_path)
        
        if file_type == 'csv':
            return self.read_csv(file_path)
        elif file_type == 'excel':
            return self.read_excel(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
    
    def read_stock_kline(self, symbol: str, data_dir: str = 'stock_data',file_type: str = 'csv') -> pd.DataFrame:
        """
        读取股票K线数据
        
        Args:
            symbol: 股票代码
            data_dir: 数据目录，默认 'stock_data'
            file_type: 文件类型，默认 'csv'
        Returns:
            股票K线数据DataFrame
        """
        # 尝试多种可能的文件名格式
        possible_paths = [
            os.path.join(data_dir, f"{symbol}_kline.{file_type}"),  # stock_data/600519_kline.csv
            os.path.join(data_dir, f"{symbol}_kline"),           # stock_data/600519_kline
            f"stock_kline_{symbol}",                              # stock_kline_600519
            f"stock_kline_{symbol}.{file_type}",                 # stock_kline_600519.csv
        ]
        
        for file_path in possible_paths:
            try:
                return self.read_data(file_path, file_type)
            except FileNotFoundError:
                continue
        
        logger.warning(f"股票 {symbol} 的K线数据不存在")
        return pd.DataFrame()
    
    def read_fund_info(self, fund_code: str) -> pd.DataFrame:
        """
        读取基金基本信息
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金信息DataFrame
        """
        # 尝试多种可能的文件名格式
        possible_paths = [
            f"fund_info_{fund_code}",
            f"fund_info_{fund_code}.csv"
        ]
        
        for file_path in possible_paths:
            try:
                return self.read_csv(file_path)
            except FileNotFoundError:
                continue
        
        logger.warning(f"基金 {fund_code} 的信息不存在")
        return pd.DataFrame()
    
    def read_fund_nav(self, fund_code: str) -> pd.DataFrame:
        """
        读取基金净值数据
        
        Args:
            fund_code: 基金代码
            
        Returns:
            基金净值DataFrame
        """
        # 尝试多种可能的文件名格式
        possible_paths = [
            f"fund_nav_{fund_code}",
            f"fund_nav_{fund_code}.csv"
        ]
        
        for file_path in possible_paths:
            try:
                return self.read_csv(file_path)
            except FileNotFoundError:
                continue
        
        logger.warning(f"基金 {fund_code} 的净值数据不存在")
        return pd.DataFrame()
    
    def list_files(self, directory: Optional[str] = None, pattern: str = '*') -> List[str]:
        """
        列出目录下的文件
        
        Args:
            directory: 目录路径，默认为基础路径
            pattern: 文件名匹配模式，默认 '*'
            
        Returns:
            文件路径列表
        """
        if directory is None:
            directory = self.base_path
        
        full_dir = self._get_full_path(directory)
        
        if not os.path.exists(full_dir):
            logger.warning(f"目录不存在: {full_dir}")
            return []
        
        path = Path(full_dir)
        files = [str(f.relative_to(path.parent)) for f in path.glob(pattern) if f.is_file()]
        
        logger.info(f"在 {full_dir} 中找到 {len(files)} 个文件")
        return files
    
    def list_stock_files(self, data_dir: str = 'stock_data') -> List[str]:
        """
        列出股票数据文件
        
        Args:
            data_dir: 数据目录，默认 'stock_data'
            
        Returns:
            股票代码列表
        """
        files = self.list_files(data_dir, '*.csv')
        symbols = []
        for f in files:
            if '_kline.csv' in f:
                symbol = f.replace('\\', '/').split('/')[-1].replace('_kline.csv', '')
                symbols.append(symbol)
        
        logger.info(f"找到 {len(symbols)} 个股票数据文件")
        return symbols
    
    def get_data_info(self, file_path: str) -> Dict:
        """
        获取数据文件的基本信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            包含文件信息的字典
        """
        full_path = self._get_full_path(file_path)
        
        if not os.path.exists(full_path):
            return {'exists': False}
        
        file_size = os.path.getsize(full_path)
        file_ext = os.path.splitext(full_path)[1].lower()
        
        info = {
            'exists': True,
            'path': full_path,
            'size': file_size,
            'size_mb': round(file_size / (1024 * 1024), 2),
            'extension': file_ext,
            'modified_time': pd.Timestamp.fromtimestamp(os.path.getmtime(full_path))
        }
        
        if file_ext in ['.csv', '.xlsx', '.xls']:
            try:
                if file_ext == '.csv':
                    df = pd.read_csv(full_path, nrows=0)
                else:
                    df = pd.read_excel(full_path, nrows=0)
                info['columns'] = list(df.columns)
                info['row_count'] = len(df) if hasattr(df, '__len__') else 'unknown'
            except Exception as e:
                info['error'] = str(e)
        
        return info
    
    def _get_full_path(self, file_path: str) -> str:
        """
        获取完整文件路径
        
        Args:
            file_path: 文件路径
            
        Returns:
            完整路径
        """
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.base_path, file_path)
    
    def _detect_file_type(self, file_path: str) -> str:
        """
        自动检测文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件类型 ('csv' 或 'excel')
        """
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.csv']:
            return 'csv'
        elif ext in ['.xlsx', '.xls']:
            return 'excel'
        else:
            raise ValueError(f"无法识别的文件类型: {ext}")


def read_from_path(file_path: str, base_path: str = './data') -> pd.DataFrame:
    """
    便捷函数：从指定路径读取数据
    
    Args:
        file_path: 文件路径
        base_path: 基础路径
        
    Returns:
        DataFrame
    """
    reader = DataReader(base_path)
    return reader.read_data(file_path)


if __name__ == "__main__":
    reader = DataReader('./data')
    
    print("=" * 60)
    print("数据读取器演示")
    print("=" * 60)
    
    print("\n1. 读取CSV文件:")
    try:
        df = reader.read_csv('stock_kline_600519.csv')
        print(f"   成功读取 {len(df)} 行数据")
        print(f"   列名: {list(df.columns)}")
    except Exception as e:
        print(f"   读取失败: {e}")
    
    print("\n2. 读取股票K线数据:")
    df_kline = reader.read_stock_kline('600519')
    if not df_kline.empty:
        print(f"   成功读取 {len(df_kline)} 行数据")
        print(df_kline.head())
    
    print("\n3. 列出所有股票数据文件:")
    symbols = reader.list_stock_files()
    print(f"   找到 {len(symbols)} 个股票: {symbols[:5]}...")
    
    print("\n4. 获取文件信息:")
    info = reader.get_data_info('stock_kline_600519.csv')
    print(f"   文件信息: {info}")
    
    print("\n5. 读取基金信息:")
    df_fund = reader.read_fund_info('000001')
    if not df_fund.empty:
        print(f"   成功读取 {len(df_fund)} 行数据")
        print(df_fund.head())
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)
