"""
项目公用方法模块
提供跨模块使用的通用工具函数和类
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
from functools import wraps
import pandas as pd
import numpy as np
from loguru import logger


# ============================================================================
# 配置工具函数
# ============================================================================

def load_config(config_path: str, default_config: Optional[Dict] = None) -> Dict:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        default_config: 默认配置字典
        
    Returns:
        配置字典
    """
    if default_config is None:
        default_config = {}
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return deep_merge_dict(default_config, config)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return default_config
    else:
        logger.warning(f"配置文件 {config_path} 不存在，使用默认配置")
        return default_config


def deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并字典，保留默认配置的同时允许用户覆盖
    
    Args:
        base: 基础字典
        override: 覆盖字典
        
    Returns:
        合并后的字典
    """
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


# ============================================================================
# 重试与装饰器工具
# ============================================================================

def retry_decorator(max_retries: int = 3, delay: float = 2.0, 
                   exceptions: Tuple = (Exception,)):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 重试延迟（秒）
        exceptions: 需要重试的异常类型
        
    Returns:
        装饰器函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logger.warning(f"尝试 {i+1}/{max_retries} 失败: {e}")
                    if i < max_retries - 1:
                        time.sleep(delay)
                    else:
                        logger.error(f"所有尝试都失败: {e}")
                        raise
        return wrapper
    return decorator


# ============================================================================
# 日期时间工具
# ============================================================================

def normalize_date_range(start_date: Optional[str] = None, 
                        end_date: Optional[str] = None,
                        default_days: int = 365) -> Tuple[str, str]:
    """
    标准化日期范围
    
    Args:
        start_date: 开始日期，格式：YYYY-MM-DD
        end_date: 结束日期，格式：YYYY-MM-DD
        default_days: 默认天数（当start_date为None时）
        
    Returns:
        (标准化开始日期, 标准化结束日期)
    """
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=default_days)).strftime('%Y-%m-%d')
    return start_date, end_date


def parse_quarter_string(quarter_str: str) -> Tuple[int, int]:
    """
    解析季度字符串，提取年份和季度信息
    
    支持的格式：
    - "YYYY年Q季度股票投资明细" (例如: "2025年1季度股票投资明细")
    - "YYYY年Q季度" (例如: "2025年Q1")
    - "YYYY-Q季度" (例如: "2025-Q1")
    - "YYYYQ季度" (例如: "2025Q1")
    
    Args:
        quarter_str: 季度字符串
        
    Returns:
        (年份, 季度) 元组
        
    Raises:
        ValueError: 当字符串格式无法解析时
        AttributeError: 当输入不是字符串时
    """
    if not isinstance(quarter_str, str):
        raise AttributeError(f"季度信息必须是字符串类型，实际类型: {type(quarter_str)}")
    
    quarter_str = quarter_str.strip()
    
    # 尝试不同的格式模式
    
    # 模式1: "YYYY年Q季度股票投资明细" 或 "YYYY年Q季度"
    pattern1 = r'(\d{4})\s*年\s*(\d+)\s*季度'
    match1 = re.search(pattern1, quarter_str)
    if match1:
        year = int(match1.group(1))
        quarter = int(match1.group(2))
        if 1 <= quarter <= 4:
            return year, quarter
    
    # 模式2: "YYYY年Q季度" (Q1, Q2, Q3, Q4)
    pattern2 = r'(\d{4})\s*年\s*Q([1-4])'
    match2 = re.search(pattern2, quarter_str)
    if match2:
        year = int(match2.group(1))
        quarter = int(match2.group(2))
        return year, quarter
    
    # 模式3: "YYYY-Q季度" (例如: 2025-Q1)
    pattern3 = r'(\d{4})-Q([1-4])'
    match3 = re.search(pattern3, quarter_str)
    if match3:
        year = int(match3.group(1))
        quarter = int(match3.group(2))
        return year, quarter
    
    # 模式4: "YYYYQ季度" (例如: 2025Q1)
    pattern4 = r'(\d{4})Q([1-4])'
    match4 = re.search(pattern4, quarter_str)
    if match4:
        year = int(match4.group(1))
        quarter = int(match4.group(2))
        return year, quarter
    
    # 模式5: "YYYY年Q季度" (中文数字)
    pattern5 = r'(\d{4})\s*年\s*([一二三四])\s*季度'
    match5 = re.search(pattern5, quarter_str)
    if match5:
        year = int(match5.group(1))
        quarter_chinese = match5.group(2)
        quarter_map = {'一': 1, '二': 2, '三': 3, '四': 4}
        quarter = quarter_map.get(quarter_chinese)
        if quarter:
            return year, quarter
    
    # 如果所有模式都不匹配，抛出异常
    raise ValueError(f"无法解析季度字符串: '{quarter_str}'")


# ============================================================================
# 文件操作工具
# ============================================================================

def detect_file_type(file_path: str) -> str:
    """
    自动检测文件类型
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件类型 ('csv' 或 'excel')
        
    Raises:
        ValueError: 无法识别的文件类型
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.csv']:
        return 'csv'
    elif ext in ['.xlsx', '.xls']:
        return 'excel'
    else:
        raise ValueError(f"无法识别的文件类型: {ext}")


def get_full_path(file_path: str, base_path: str = '.') -> str:
    """
    获取完整文件路径
    
    Args:
        file_path: 文件路径
        base_path: 基础路径
        
    Returns:
        完整路径
    """
    if os.path.isabs(file_path):
        return file_path
    return os.path.join(base_path, file_path)


def ensure_directory_exists(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    """
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        logger.info(f"创建目录: {directory}")


# ============================================================================
# 数据处理工具
# ============================================================================

def get_column_with_mapping(data: pd.DataFrame, col_name: str, 
                           col_mapping: Optional[Dict] = None) -> Optional[pd.Series]:
    """
    获取指定列的数据（支持列名映射）
    
    Args:
        data: DataFrame
        col_name: 列名（英文）
        col_mapping: 列名映射字典
        
    Returns:
        对应列的数据，如果未找到则返回None
    """
    if col_mapping is None:
        col_mapping = {
            'date': '日期',
            'open': '开盘',
            'high': '最高',
            'low': '最低',
            'close': '收盘',
            'volume': '成交量'
        }
    
    if col_name in data.columns:
        return data[col_name]
    elif col_name in col_mapping and col_mapping[col_name] in data.columns:
        return data[col_mapping[col_name]]
    
    return None


def validate_ohlcv_data(data: pd.DataFrame) -> None:
    """
    验证OHLCV数据的完整性
    
    Args:
        data: 待验证的数据
        
    Raises:
        ValueError: 数据格式不正确或缺少必要列
    """
    if not isinstance(data, pd.DataFrame):
        raise ValueError("输入数据必须是pandas DataFrame")
    
    if data.empty:
        raise ValueError("输入数据不能为空")
    
    # 检查必要的列（支持中英文列名）
    required_cols_en = ['date', 'open', 'high', 'low', 'close', 'volume']
    required_cols_cn = ['日期', '开盘', '最高', '最低', '收盘', '成交量']
    
    has_en = all(col in data.columns for col in required_cols_en)
    has_cn = all(col in data.columns for col in required_cols_cn)
    
    if not (has_en or has_cn):
        raise ValueError(f"数据必须包含以下列之一：\n"
                         f"英文：{required_cols_en}\n"
                         f"中文：{required_cols_cn}")
    
    # 检查数据类型
    for col in data.columns:
        if col in ['open', 'high', 'low', 'close', 'volume', '开盘', '最高',
                   '最低', '收盘', '成交量']:
            if not pd.api.types.is_numeric_dtype(data[col]):
                raise ValueError(f"列 '{col}' 必须是数值类型")


def normalize_series(data: pd.Series, method: str = 'minmax') -> pd.Series:
    """
    数据序列归一化
    
    Args:
        data: 原始数据序列
        method: 归一化方法，'minmax'或'zscore'
        
    Returns:
        归一化后的数据序列
        
    Raises:
        ValueError: 不支持的归一化方法
    """
    if method == 'minmax':
        return (data - data.min()) / (data.max() - data.min())
    elif method == 'zscore':
        return (data - data.mean()) / data.std()
    else:
        raise ValueError(f"不支持的归一化方法: {method}")


def calculate_weighted_average(values: List[float], weights: List[float]) -> float:
    """
    计算加权平均值
    
    Args:
        values: 值列表
        weights: 权重列表
        
    Returns:
        加权平均值
        
    Raises:
        ValueError: 列表长度不匹配或权重总和为0
    """
    if len(values) != len(weights):
        raise ValueError("值和权重列表长度必须相同")
    
    if sum(weights) == 0:
        raise ValueError("权重总和不能为0")
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    total_weight = sum(weights)
    
    return weighted_sum / total_weight


# ============================================================================
# 数学计算工具
# ============================================================================

def calculate_signal_strength(value: float, threshold: float, 
                            range_val: float) -> float:
    """
    计算信号强度
    
    Args:
        value: 当前值
        threshold: 阈值
        range_val: 参考范围（用于标准化）
        
    Returns:
        0-1之间的强度值
    """
    diff = abs(value - threshold)
    strength = min(diff / max(range_val, 0.01), 1.0)
    return strength


def calculate_ma(data: pd.Series, period: int) -> pd.Series:
    """
    计算移动平均线
    
    Args:
        data: 数据序列
        period: 计算周期
        
    Returns:
        移动平均线序列
    """
    if period <= 0:
        raise ValueError("周期必须大于0")
    
    return data.rolling(window=period).mean()


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    计算指数移动平均线
    
    Args:
        data: 数据序列
        period: 计算周期
        
    Returns:
        指数移动平均线序列
    """
    if period <= 0:
        raise ValueError("周期必须大于0")
    
    return data.ewm(span=period, adjust=False).mean()


# ============================================================================
# 缓存管理工具
# ============================================================================

class MemoryCache:
    """内存缓存管理器"""
    
    def __init__(self, ttl: int = 60, max_size: int = 128):
        """
        初始化内存缓存
        
        Args:
            ttl: 缓存生存时间（秒）
            max_size: 最大缓存项数
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        self._evict_expired()
        
        cached = self._cache.get(key)
        if cached:
            cached_at, cached_value = cached
            if (datetime.now() - cached_at).total_seconds() < self.ttl:
                return cached_value
        
        return None
    
    def set(self, key: str, value: Any) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        self._evict_expired()
        
        # 如果缓存已满，删除最旧的项
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.items(), key=lambda item: item[1][0])[0]
            self._cache.pop(oldest_key, None)
        
        self._cache[key] = (datetime.now(), value)
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    def _evict_expired(self) -> None:
        """清理过期缓存项"""
        now = datetime.now()
        expired_keys = [
            key for key, (cached_at, _) in self._cache.items()
            if (now - cached_at).total_seconds() >= self.ttl
        ]
        for key in expired_keys:
            self._cache.pop(key, None)


# ============================================================================
# 类型转换工具
# ============================================================================

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全转换为浮点数
    
    Args:
        value: 待转换的值
        default: 转换失败时的默认值
        
    Returns:
        浮点数
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    安全转换为整数
    
    Args:
        value: 待转换的值
        default: 转换失败时的默认值
        
    Returns:
        整数
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """
    安全转换为字符串
    
    Args:
        value: 待转换的值
        default: 转换失败时的默认值
        
    Returns:
        字符串
    """
    try:
        return str(value)
    except Exception:
        return default


# ============================================================================
# 导出所有函数
# ============================================================================

__all__ = [
    # 配置工具
    'load_config',
    'deep_merge_dict',
    
    # 重试与装饰器
    'retry_decorator',
    
    # 日期时间工具
    'normalize_date_range',
    'parse_quarter_string',
    
    # 文件操作工具
    'detect_file_type',
    'get_full_path',
    'ensure_directory_exists',
    
    # 数据处理工具
    'get_column_with_mapping',
    'validate_ohlcv_data',
    'normalize_series',
    'calculate_weighted_average',
    
    # 数学计算工具
    'calculate_signal_strength',
    'calculate_ma',
    'calculate_ema',
    
    # 缓存管理
    'MemoryCache',
    
    # 类型转换工具
    'safe_float',
    'safe_int',
    'safe_str',
]